from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .config import get_agent_config
from .exceptions import (
    AgentConfigurationError,
    AgentDisabledError,
    LLMProviderError,
    ToolProtocolError,
)
from .orchestrator import AgentOrchestrator
from .permissions import IsSystemAdmin
from .serializers import AgentQuerySerializer
from .services import ProcurementActionService
from .models import KnowledgeDocument
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError


class AgentQueryView(APIView):
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    http_method_names = ["post", "options"]

    def post(self, request):
        serializer = AgentQuerySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            config = get_agent_config()
            config.validate_for_request()
            result = AgentOrchestrator(config).run(
                request.user,
                serializer.validated_data["question"],
                history=serializer.validated_data.get("history", []),
                conversation_id=serializer.validated_data.get("conversation_id"),
            )
        except AgentDisabledError:
            return Response(
                {"code": "agent_disabled", "detail": "智能查询功能尚未启用。"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except AgentConfigurationError:
            return Response(
                {"code": "agent_not_configured", "detail": "智能查询配置不完整。"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except LLMProviderError:
            return Response(
                {"code": "provider_unavailable", "detail": "智能查询暂时不可用。"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except ToolProtocolError:
            return Response(
                {"code": "invalid_model_response", "detail": "智能查询响应异常。"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "answer": result.answer,
                "domain": result.domain,
                "tools": result.tools,
                "request_id": result.request_id,
                "conversation_id": result.conversation_id,
                "actions": result.actions,
                "evidence": result.evidence,
                "retrieval": result.retrieval,
            }
        )


class AgentActionConfirmView(APIView):
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    http_method_names = ["post", "options"]

    def post(self, request, draft_id):
        try:
            action = ProcurementActionService.confirm(request.user, draft_id)
        except ObjectDoesNotExist:
            return Response(
                {"detail": "待确认操作不存在。"},
                status=status.HTTP_404_NOT_FOUND,
            )
        except PermissionDenied:
            return Response(
                {"detail": "无权确认该操作。"},
                status=status.HTTP_403_FORBIDDEN,
            )
        except (ValidationError, DRFValidationError) as exc:
            messages = getattr(exc, "messages", None)
            detail = messages[0] if messages else getattr(exc, "detail", str(exc))
            return Response({"detail": detail}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"action": action})


class KnowledgeDocumentDetailView(APIView):
    permission_classes = [IsAuthenticated, IsSystemAdmin]
    http_method_names = ["get", "options"]

    def get(self, request, document_id):
        try:
            document = KnowledgeDocument.objects.prefetch_related("chunks").get(
                pk=document_id,
                status=KnowledgeDocument.STATUS_PUBLISHED,
            )
        except KnowledgeDocument.DoesNotExist:
            return Response({"detail": "知识文档不存在。"}, status=status.HTTP_404_NOT_FOUND)
        return Response(
            {
                "id": document.id,
                "title": document.title,
                "domain": document.domain,
                "version": document.version,
                "updated_at": document.updated_at,
                "sections": [
                    {
                        "chunk_id": chunk.id,
                        "section": chunk.section_path,
                        "content": chunk.content,
                    }
                    for chunk in document.chunks.filter(is_active=True)
                ],
            }
        )

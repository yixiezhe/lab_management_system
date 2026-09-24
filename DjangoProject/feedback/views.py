from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Feedback
from .permissions import IsNotLandHost, IsSystemAdmin
from .serializers import FeedbackReplySerializer, FeedbackSerializer


class FeedbackViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [IsAuthenticated, IsNotLandHost]

    @action(
        detail=True,
        methods=["post"],
        permission_classes=[IsAuthenticated, IsNotLandHost, IsSystemAdmin],
    )
    def reply(self, request, pk=None):
        feedback = self.get_object()
        serializer = FeedbackReplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        feedback.admin_reply = serializer.validated_data["admin_reply"]
        feedback.replied_by = request.user
        feedback.replied_at = timezone.now()
        feedback.save(update_fields=["admin_reply", "replied_by", "replied_at", "updated_at"])

        data = self.get_serializer(feedback).data
        return Response(data, status=status.HTTP_200_OK)

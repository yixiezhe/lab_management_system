from django.urls import path

from .views import AgentActionConfirmView, AgentQueryView, KnowledgeDocumentDetailView

urlpatterns = [
    path("query/", AgentQueryView.as_view(), name="labops-agent-query"),
    path(
        "actions/<uuid:draft_id>/confirm/",
        AgentActionConfirmView.as_view(),
        name="labops-agent-action-confirm",
    ),
    path(
        "knowledge/documents/<int:document_id>/",
        KnowledgeDocumentDetailView.as_view(),
        name="labops-knowledge-document-detail",
    ),
]

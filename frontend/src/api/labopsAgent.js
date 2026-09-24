import apiClient from '@/api'


export const queryLabOpsAgent = (question, history = [], conversationId = null) => (
  apiClient.post('/labops-agent/query/', {
    question,
    history,
    ...(conversationId ? { conversation_id: conversationId } : {}),
  })
)

export const confirmLabOpsAction = (actionId) => (
  apiClient.post(`/labops-agent/actions/${actionId}/confirm/`)
)

export const getLabOpsKnowledgeDocument = (documentId) => (
  apiClient.get(`/labops-agent/knowledge/documents/${documentId}/`)
)

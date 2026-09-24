<template>
  <div v-if="hasEvidence || showDegraded" class="evidence-wrap">
    <details v-if="hasEvidence">
      <summary>查看知识依据（{{ evidence.length }}）</summary>
      <button
        v-for="item in evidence"
        :key="item.chunk_id"
        class="evidence-item"
        type="button"
        :disabled="loading"
        @click="openDocument(item.document_id)"
      >
        <span class="evidence-title">[{{ item.reference }}] {{ item.title }}</span>
        <span class="evidence-section">{{ item.section || '正文' }}</span>
        <span v-if="item.excerpt" class="evidence-excerpt">{{ item.excerpt }}</span>
      </button>
    </details>
    <span v-else class="retrieval-warning">知识检索暂不可用，本次仅使用业务查询结果。</span>
  </div>
  <el-dialog
    v-model="dialogVisible"
    append-to-body
    width="min(760px, calc(100vw - 28px))"
    :title="document?.title || '知识依据'"
  >
    <div v-loading="loading" class="document-preview">
      <div v-if="document" class="document-meta">
        版本 {{ document.version }} · 更新于 {{ formatDate(document.updated_at) }}
      </div>
      <section v-for="section in document?.sections || []" :key="section.chunk_id">
        <h4>{{ section.section || '正文' }}</h4>
        <p>{{ section.content }}</p>
      </section>
    </div>
  </el-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getLabOpsKnowledgeDocument } from '@/api/labopsAgent'

const props = defineProps({
  evidence: { type: Array, default: () => [] },
  retrieval: { type: Object, default: () => ({}) },
})

const hasEvidence = computed(() => props.evidence.length > 0)
const showDegraded = computed(() => ['unavailable'].includes(props.retrieval?.status))
const dialogVisible = ref(false)
const loading = ref(false)
const document = ref(null)

function formatDate(value) {
  return value ? new Date(value).toLocaleString('zh-CN', { hour12: false }) : '未知'
}

async function openDocument(documentId) {
  loading.value = true
  dialogVisible.value = true
  try {
    const response = await getLabOpsKnowledgeDocument(documentId)
    document.value = response.data
  } catch (error) {
    dialogVisible.value = false
    ElMessage.error(error.response?.data?.detail || '知识原文加载失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.evidence-wrap { margin-top: 7px; font-size: 11px; }
details { padding: 7px 8px; border: 1px solid #d9ecff; border-radius: 8px; background: #f5faff; }
summary { color: #337ecc; cursor: pointer; font-weight: 600; }
.evidence-item { width: 100%; display: block; margin-top: 7px; padding: 7px 0 0; border: 0; border-top: 1px solid #e4f1ff; color: inherit; background: transparent; cursor: pointer; text-align: left; }
.evidence-item:disabled { cursor: wait; opacity: .65; }
.evidence-item:hover .evidence-title { color: #409eff; }
.evidence-title, .evidence-section, .evidence-excerpt { display: block; }
.evidence-title { color: #303133; font-weight: 600; }
.evidence-section { margin-top: 2px; color: #606266; }
.evidence-excerpt { margin-top: 3px; overflow: hidden; color: #909399; line-height: 1.45; text-overflow: ellipsis; white-space: nowrap; }
.retrieval-warning { display: block; padding: 6px 8px; border-radius: 7px; color: #b88230; background: #fdf6ec; }
.document-preview { min-height: 120px; max-height: 65vh; overflow-y: auto; }
.document-meta { margin-bottom: 14px; color: #909399; font-size: 12px; }
.document-preview section + section { margin-top: 18px; }
.document-preview h4 { margin: 0 0 7px; color: #303133; }
.document-preview p { margin: 0; color: #606266; line-height: 1.75; white-space: pre-wrap; }
</style>

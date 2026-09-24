<template>
  <div class="feedback-page">
    <section class="announcement-panel">
      <div class="page-header">
        <div>
          <h1>公告和反馈</h1>
        </div>
        <el-button :icon="Refresh" :loading="loading || loadingAnnouncements" @click="fetchPageData">
          刷新
        </el-button>
      </div>

      <div class="section-header">
        <h2>公告</h2>
        <el-tag type="info">共 {{ announcementList.length }} 条</el-tag>
      </div>

      <el-skeleton v-if="loadingAnnouncements" :rows="4" animated />
      <el-empty v-else-if="announcementList.length === 0" description="暂无公告" />

      <div v-else class="announcement-list">
        <article v-for="item in announcementList" :key="item.id" class="announcement-item">
          <div class="announcement-title-row">
            <h3>{{ item.title }}</h3>
            <el-tag v-if="!item.is_read" type="warning" effect="plain">未读</el-tag>
          </div>
          <div class="time-label">{{ formatDate(item.updated_at || item.created_at) }}</div>
          <div class="announcement-content">{{ item.content }}</div>
        </article>
      </div>
    </section>

    <el-card class="feedback-form-card" shadow="never">
      <template #header>
        <div class="section-header">
          <h2>提交反馈</h2>
        </div>
      </template>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        class="feedback-form"
      >
        <el-form-item label="反馈类型" prop="category">
          <el-radio-group v-model="form.category">
            <el-radio-button label="bug">系统 Bug</el-radio-button>
            <el-radio-button label="suggestion">功能建议</el-radio-button>
            <el-radio-button label="other">其他反馈</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="反馈内容" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="5"
            maxlength="1000"
            show-word-limit
            placeholder="请描述问题现象、出现页面、期望改进点等信息。"
          />
        </el-form-item>

        <div class="form-actions">
          <el-button @click="resetForm">清空</el-button>
          <el-button type="primary" :icon="Promotion" :loading="submitting" @click="submitFeedback">
            提交
          </el-button>
        </div>
      </el-form>
    </el-card>

    <section class="feedback-list-panel">
      <div class="section-header">
        <h2>历史反馈</h2>
        <el-tag type="info">共 {{ feedbackList.length }} 条</el-tag>
      </div>

      <el-skeleton v-if="loading" :rows="5" animated />
      <el-empty v-else-if="feedbackList.length === 0" description="暂无反馈" />

      <div v-else class="feedback-list">
        <article v-for="item in feedbackList" :key="item.id" class="feedback-item">
          <div class="feedback-meta">
            <el-tag :type="getCategoryTagType(item.category)" effect="plain">
              {{ item.category_display || getCategoryLabel(item.category) }}
            </el-tag>
            <span class="time-label">{{ formatDate(item.created_at) }}</span>
          </div>

          <div class="feedback-content">{{ item.content }}</div>

          <div v-if="item.admin_reply" class="reply-block">
            <div class="reply-title">
              <span>回复</span>
              <span v-if="item.replied_at" class="time-label">{{ formatDate(item.replied_at) }}</span>
            </div>
            <div class="reply-content">{{ item.admin_reply }}</div>
          </div>

          <div v-if="authStore.isSystemAdmin" class="reply-actions">
            <template v-if="editingFeedbackId === item.id">
              <el-input
                v-model="replyDraft"
                type="textarea"
                :rows="3"
                maxlength="1000"
                show-word-limit
                placeholder="填写管理员回复"
              />
              <div class="reply-buttons">
                <el-button :icon="Close" @click="cancelReply">取消</el-button>
                <el-button
                  type="primary"
                  :icon="Check"
                  :loading="savingReplyId === item.id"
                  @click="submitReply(item)"
                >
                  保存回复
                </el-button>
              </div>
            </template>
            <el-button v-else :icon="EditPen" @click="startReply(item)">
              {{ item.admin_reply ? '修改回复' : '回复' }}
            </el-button>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue';
import apiClient from '@/api';
import { useAuthStore } from '@/stores/auth';
import { ElMessage } from 'element-plus';
import { Check, Close, EditPen, Promotion, Refresh } from '@element-plus/icons-vue';

const authStore = useAuthStore();

const loading = ref(false);
const loadingAnnouncements = ref(false);
const submitting = ref(false);
const feedbackList = ref([]);
const announcementList = ref([]);
const formRef = ref(null);
const editingFeedbackId = ref(null);
const replyDraft = ref('');
const savingReplyId = ref(null);

const form = reactive({
  category: 'bug',
  content: '',
});

const rules = {
  category: [{ required: true, message: '请选择反馈类型', trigger: 'change' }],
  content: [
    { required: true, message: '请填写反馈内容', trigger: 'blur' },
    { min: 5, message: '反馈内容至少 5 个字', trigger: 'blur' },
  ],
};

const normalizeListResponse = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
};

const markAnnouncementsRead = async (items) => {
  const unreadIds = items.filter(item => !item.is_read).map(item => item.id).filter(Boolean);
  if (unreadIds.length === 0) return;

  await Promise.allSettled(
    unreadIds.map(id => apiClient.post(`/procurement/announcements/${id}/mark-read/`))
  );

  announcementList.value = announcementList.value.map(item => (
    unreadIds.includes(item.id) ? { ...item, is_read: true } : item
  ));
};

const fetchAnnouncements = async () => {
  loadingAnnouncements.value = true;
  try {
    const response = await apiClient.get('/procurement/announcements/');
    const items = normalizeListResponse(response.data);
    announcementList.value = items;
    await markAnnouncementsRead(items);
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '获取公告列表失败');
  } finally {
    loadingAnnouncements.value = false;
  }
};

const fetchFeedback = async () => {
  loading.value = true;
  try {
    const response = await apiClient.get('/feedback/items/');
    feedbackList.value = normalizeListResponse(response.data);
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '获取反馈列表失败');
  } finally {
    loading.value = false;
  }
};

const fetchPageData = async () => {
  await Promise.all([fetchAnnouncements(), fetchFeedback()]);
};

const resetForm = () => {
  form.category = 'bug';
  form.content = '';
  formRef.value?.clearValidate();
};

const submitFeedback = async () => {
  if (!formRef.value) return;
  await formRef.value.validate();

  submitting.value = true;
  try {
    await apiClient.post('/feedback/items/', {
      category: form.category,
      content: form.content.trim(),
    });
    ElMessage.success('反馈已匿名提交');
    resetForm();
    await fetchFeedback();
  } catch (error) {
    const detail = error.response?.data?.content?.[0] || error.response?.data?.detail || '提交反馈失败';
    ElMessage.error(detail);
  } finally {
    submitting.value = false;
  }
};

const startReply = (item) => {
  editingFeedbackId.value = item.id;
  replyDraft.value = item.admin_reply || '';
};

const cancelReply = () => {
  editingFeedbackId.value = null;
  replyDraft.value = '';
};

const submitReply = async (item) => {
  const content = replyDraft.value.trim();
  if (!content) {
    ElMessage.warning('请填写回复内容');
    return;
  }

  savingReplyId.value = item.id;
  try {
    const response = await apiClient.post(`/feedback/items/${item.id}/reply/`, {
      admin_reply: content,
    });
    const index = feedbackList.value.findIndex(feedback => feedback.id === item.id);
    if (index !== -1) feedbackList.value[index] = response.data;
    ElMessage.success('回复已保存');
    cancelReply();
  } catch (error) {
    const detail = error.response?.data?.admin_reply?.[0] || error.response?.data?.detail || '保存回复失败';
    ElMessage.error(detail);
  } finally {
    savingReplyId.value = null;
  }
};

const getCategoryLabel = (category) => {
  const map = {
    bug: '系统 Bug',
    suggestion: '功能建议',
    other: '其他反馈',
  };
  return map[category] || '反馈';
};

const getCategoryTagType = (category) => {
  const map = {
    bug: 'danger',
    suggestion: 'success',
    other: 'info',
  };
  return map[category] || 'info';
};

const formatDate = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
};

onMounted(fetchPageData);
</script>

<style scoped>
.feedback-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.announcement-panel,
.feedback-list-panel {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 20px;
}

.feedback-form-card {
  border-radius: 6px;
}

.page-header,
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.section-header {
  margin-bottom: 16px;
}

h1,
h2,
h3 {
  margin: 0;
  color: #303133;
}

h1 {
  font-size: 24px;
}

h2 {
  font-size: 20px;
}

h3 {
  font-size: 17px;
  line-height: 1.4;
}

.announcement-list,
.feedback-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.announcement-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.announcement-item,
.feedback-item {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 16px;
  background: #fff;
}

.announcement-content,
.feedback-content,
.reply-content {
  margin-top: 12px;
  color: #303133;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.feedback-form {
  max-width: 900px;
}

.form-actions,
.reply-buttons {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.feedback-meta,
.reply-title {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.time-label {
  color: #909399;
  font-size: 13px;
}

.reply-block {
  margin-top: 14px;
  padding: 12px 14px;
  border-left: 3px solid #409eff;
  background: #f5f9ff;
}

.reply-title {
  justify-content: space-between;
  color: #1f5f99;
  font-weight: 600;
}

.reply-actions {
  margin-top: 14px;
}

.reply-buttons {
  margin-top: 10px;
}

@media (max-width: 767px) {
  .page-header,
  .section-header,
  .announcement-title-row {
    align-items: flex-start;
    flex-direction: column;
  }

  .feedback-form :deep(.el-radio-group) {
    display: grid;
    grid-template-columns: 1fr;
    width: 100%;
  }

  .form-actions,
  .reply-buttons {
    flex-direction: column;
  }
}
</style>

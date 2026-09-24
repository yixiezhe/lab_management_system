<template>
  <div class="announcement-management-page">
    <el-card shadow="never" class="management-card">
      <template #header>
        <div class="page-header">
          <h1>公告管理</h1>
          <div class="header-actions">
            <el-button :icon="Refresh" :loading="loading" @click="fetchAnnouncements">刷新</el-button>
            <el-button type="primary" :icon="Plus" @click="openCreateDialog">发布公告</el-button>
          </div>
        </div>
      </template>

      <el-table
        v-loading="loading"
        :data="announcementList"
        border
        stripe
        empty-text="暂无公告"
        style="width: 100%"
      >
        <el-table-column prop="title" label="标题" min-width="160" />

        <el-table-column label="内容" min-width="280">
          <template #default="{ row }">
            <div class="content-preview">{{ row.content }}</div>
          </template>
        </el-table-column>

        <el-table-column label="展示设置" width="180">
          <template #default="{ row }">
            <div class="setting-tags">
              <el-tag :type="row.is_published ? 'success' : 'info'" effect="plain">
                {{ row.is_published ? '首页展示' : '不在首页展示' }}
              </el-tag>
              <el-tag :type="row.show_popup ? 'warning' : 'info'" effect="plain">
                {{ row.show_popup ? '登录弹窗' : '不弹窗' }}
              </el-tag>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="最后更新" width="210">
          <template #default="{ row }">
            <div class="updated-cell">
              <span>{{ formatDate(row.updated_at) }}</span>
              <span v-if="row.updated_by">修改人：{{ row.updated_by.name }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link :icon="EditPen" @click="openEditDialog(row)">
              修改
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="isEditing ? '修改公告' : '发布公告'"
      width="720px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="公告标题" prop="title">
          <el-input v-model="form.title" maxlength="120" show-word-limit placeholder="请输入公告标题" />
        </el-form-item>

        <el-form-item label="公告内容" prop="content">
          <el-input
            v-model="form.content"
            type="textarea"
            :rows="10"
            maxlength="4000"
            show-word-limit
            placeholder="请输入公告内容"
          />
        </el-form-item>

        <div class="switch-row">
          <el-form-item label="在首页展示">
            <el-switch v-model="form.is_published" />
          </el-form-item>
          <el-form-item label="登录时弹窗显示">
            <el-switch v-model="form.show_popup" />
          </el-form-item>
        </div>
      </el-form>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="handleSave">
            {{ isEditing ? '保存修改' : '发布公告' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue';
import apiClient from '@/api';
import { ElMessage } from 'element-plus';
import { EditPen, Plus, Refresh } from '@element-plus/icons-vue';

const announcementList = ref([]);
const loading = ref(false);
const saving = ref(false);
const dialogVisible = ref(false);
const formRef = ref(null);

const form = reactive({
  id: null,
  title: '',
  content: '',
  is_published: false,
  show_popup: false,
});

const isEditing = computed(() => !!form.id);

const rules = {
  title: [
    { required: true, message: '请填写公告标题', trigger: 'blur' },
    { min: 1, message: '请填写公告标题', trigger: 'blur' },
  ],
  content: [
    { required: true, message: '请填写公告内容', trigger: 'blur' },
    { min: 1, message: '请填写公告内容', trigger: 'blur' },
  ],
};

const normalizeListResponse = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
};

const resetForm = () => {
  Object.assign(form, {
    id: null,
    title: '',
    content: '',
    is_published: false,
    show_popup: false,
  });
  formRef.value?.clearValidate();
};

const fetchAnnouncements = async () => {
  loading.value = true;
  try {
    const response = await apiClient.get('/procurement/announcements/');
    announcementList.value = normalizeListResponse(response.data);
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '获取公告列表失败');
  } finally {
    loading.value = false;
  }
};

const openCreateDialog = () => {
  resetForm();
  dialogVisible.value = true;
};

const openEditDialog = (announcement) => {
  Object.assign(form, {
    id: announcement.id,
    title: announcement.title || '',
    content: announcement.content || '',
    is_published: !!announcement.is_published,
    show_popup: !!announcement.show_popup,
  });
  formRef.value?.clearValidate();
  dialogVisible.value = true;
};

const handleSave = async () => {
  if (!formRef.value) return;
  await formRef.value.validate();

  const payload = {
    title: form.title.trim(),
    content: form.content.trim(),
    is_published: form.is_published,
    show_popup: form.show_popup,
  };

  saving.value = true;
  try {
    if (isEditing.value) {
      await apiClient.put(`/procurement/announcements/${form.id}/`, payload);
      ElMessage.success('公告已保存');
    } else {
      await apiClient.post('/procurement/announcements/', payload);
      ElMessage.success('公告已发布');
    }
    dialogVisible.value = false;
    await fetchAnnouncements();
  } catch (error) {
    const detail =
      error.response?.data?.title?.[0] ||
      error.response?.data?.content?.[0] ||
      error.response?.data?.detail ||
      '保存公告失败';
    ElMessage.error(detail);
  } finally {
    saving.value = false;
  }
};

const formatDate = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
};

onMounted(fetchAnnouncements);
</script>

<style scoped>
.announcement-management-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.management-card {
  border-radius: 6px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.page-header h1 {
  margin: 0;
  color: #303133;
  font-size: 22px;
}

.header-actions,
.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
}

.content-preview {
  display: -webkit-box;
  overflow: hidden;
  color: #303133;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
}

.setting-tags {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.updated-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #606266;
  font-size: 13px;
}

.updated-cell span + span {
  color: #909399;
}

.switch-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

@media (max-width: 767px) {
  .page-header,
  .header-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .switch-row {
    grid-template-columns: 1fr;
  }
}
</style>

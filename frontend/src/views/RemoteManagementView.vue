<template>
  <el-container direction="vertical" style="padding: 20px;">
    <el-card class="box-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span>🖥️ 远程主机管理 (系统管理员)</span>
          <el-button type="primary" @click="handleOpenDialog('create')">
            <el-icon><Plus /></el-icon>
            新增主机
          </el-button>
        </div>
      </template>

      <el-table :data="machines" stripe v-loading="isLoading">
        <el-table-column prop="name" label="主机名称" min-width="200" />
        <el-table-column prop="ip_address" label="IP 地址 / 域名" min-width="200" />
        
        <el-table-column prop="username" label="Windows 用户名" min-width="150" />

        <el-table-column prop="description" label="主机描述" min-width="250" show-overflow-tooltip />
        <el-table-column prop="is_active" label="是否启用" width="100" align="center">
          <template #default="scope">
            <el-tag :type="scope.row.is_active ? 'success' : 'info'">
              {{ scope.row.is_active ? '已启用' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column label="操作" fixed="right" width="180" align="center">
          <template #default="scope">
            <el-button
              type="primary"
              plain
              size="small"
              @click="handleOpenDialog('edit', scope.row)"
            >
              编辑
            </el-button>
            <el-button
              type="danger"
              plain
              size="small"
              @click="handleDelete(scope.row.id)"
            >
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="dialogMode === 'create' ? '新增主机' : '编辑主机'"
      width="600px"
      @closed="handleCloseDialog"
    >
      <el-form
        ref="machineFormRef"
        :model="machineForm"
        :rules="machineFormRules"
        label-width="120px"
        v-loading="isSubmitting"
      >
        <el-form-item label="主机名称" prop="name">
          <el-input v-model="machineForm.name" placeholder="例如：高性能计算服务器" />
        </el-form-item>
        <el-form-item label="IP 地址 / 域名" prop="ip_address">
          <el-input v-model="machineForm.ip_address" placeholder="例如：192.0.2.10 或 rdp.example.invalid" />
        </el-form-item>
        
        <el-form-item label="Windows 用户名" prop="username">
          <el-input v-model="machineForm.username" placeholder="例如：labuser01" />
        </el-form-item>
        <el-form-item label="Windows 密码" prop="password">
          <el-input
            v-model="machineForm.password"
            type="password"
            show-password
            :placeholder="dialogMode === 'edit' ? '留空则不修改密码' : '请输入密码'"
          />
          <el-tooltip 
            v-if="dialogMode === 'edit'"
            content="密码在后台已加密存储。此处留空，则不修改已存密码。" 
            placement="top">
            <el-icon style="margin-left: 8px; color: #999;"><QuestionFilled /></el-icon>
          </el-tooltip>
        </el-form-item>

        <el-form-item label="主机描述" prop="description">
          <el-input v-model="machineForm.description" type="textarea" placeholder="（可选）" />
        </el-form-item>
        <el-form-item label="是否启用" prop="is_active">
          <el-switch
            v-model="machineForm.is_active"
            active-text="启用"
            inactive-text="禁用"
          />
          <el-tooltip content="禁用后，普通用户在预约页面的下拉列表中将看不到此主机" placement="top">
            <el-icon style="margin-left: 8px; color: #999;"><QuestionFilled /></el-icon>
          </el-tooltip>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleSubmit" :loading="isSubmitting">
            {{ dialogMode === 'create' ? '创建' : '保存' }}
          </el-button>
        </span>
      </template>
    </el-dialog>

  </el-container>
</template>

<script setup>
import { ref, onMounted, reactive } from 'vue';
import {
  fetchRdpMachines,
  createRdpMachine,
  updateRdpMachine,
  deleteRdpMachine
} from '@/api/remote_access';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Plus, QuestionFilled } from '@element-plus/icons-vue';

// --- 状态变量 ---
const isLoading = ref(false);
const isSubmitting = ref(false);
const machines = ref([]); // 主机列表

// --- 对话框相关 ---
const dialogVisible = ref(false);
const dialogMode = ref('create'); // 'create' or 'edit'
const machineFormRef = ref(null); // 表单引用

// 3. (已修改) 更新 initialForm
const initialForm = {
  id: null,
  name: '',
  ip_address: '',
  description: '',
  is_active: true,
  username: '', // <-- 新增
  password: ''  // <-- 新增
};
const machineForm = reactive({ ...initialForm });

// 4. (已修改) 更新验证规则
const machineFormRules = {
  name: [
    { required: true, message: '请输入主机名称', trigger: 'blur' }
  ],
  ip_address: [
    { required: true, message: '请输入 IP 地址或域名', trigger: 'blur' }
  ],
  username: [ // <-- 新增
    { required: true, message: '请输入 Windows 用户名', trigger: 'blur' }
  ],
  // 密码在 "编辑" 时是可选的（留空=不修改），
  // 在 "创建" 时，后端模型字段 'blank=True'，所以也是可选的
  // (但如果为空，连接时会失败，这符合逻辑)
};

// --- 数据获取 ---
const handleFetchMachines = async () => {
  isLoading.value = true;
  try {
    const response = await fetchRdpMachines();
    machines.value = response.data.results || response.data; 
  } catch (error) {
    console.error("Failed to fetch RDP machines (admin):", error);
    ElMessage.error('获取主机列表失败');
  } finally {
    isLoading.value = false;
  }
};

onMounted(() => {
  handleFetchMachines();
});

// --- 核心 CRUD 操作 ---

/**
 * 打开对话框
 */
const handleOpenDialog = (mode, machine = null) => {
  dialogMode.value = mode;
  if (mode === 'edit' && machine) {
    // 编辑模式：填充表单
    Object.assign(machineForm, machine);
    // 5. (核心) 必须清空密码字段，防止明文密码被保留在表单状态中
    //    后端 API 不会返回密码，所以 'machine' 对象中没有 'password'
    machineForm.password = '';
  } else {
    // 创建模式：重置表单
    Object.assign(machineForm, { ...initialForm, is_active: true });
  }
  dialogVisible.value = true;
};

/**
 * 关闭对话框时重置表单和校验
 */
const handleCloseDialog = () => {
  Object.assign(machineForm, initialForm);
  machineFormRef.value?.resetFields();
};

/**
 * 提交表单 (创建或更新)
 */
const handleSubmit = async () => {
  if (!machineFormRef.value) return;

  await machineFormRef.value.validate(async (valid) => {
    if (valid) {
      isSubmitting.value = true;
      
      // 准备要发送的数据
      const dataToSend = { ...machineForm };

      // (核心) 如果是 "编辑" 模式 且 "密码" 为空，
      // 则从 dataToSend 中删除 password 键，
      // 确保后端 serializer 不会用空字符串覆盖已有的加密密码。
      if (dialogMode.value === 'edit' && dataToSend.password === '') {
        delete dataToSend.password;
      }
      
      try {
        if (dialogMode.value === 'create') {
          // --- 创建 ---
          // 移除 id
          const { id, ...createData } = dataToSend; 
          await createRdpMachine(createData);
          ElMessage.success('主机创建成功');
        } else {
          // --- 更新 ---
          if (!dataToSend.id) return;
          await updateRdpMachine(dataToSend.id, dataToSend);
          ElMessage.success('主机更新成功');
        }
        dialogVisible.value = false; // 关闭对话框
        handleFetchMachines(); // 刷新表格
      } catch (error) {
        console.error('Submit machine failed:', error);
        ElMessage.error(error.response?.data?.detail || '操作失败');
      } finally {
        isSubmitting.value = false;
      }
    } else {
      ElMessage.warning('请检查表单是否填写完整');
    }
  });
};

/**
 * 删除主机
 */
const handleDelete = async (machineId) => {
  try {
    await ElMessageBox.confirm(
      '确定要删除这个主机吗？这也会删除关联的预约记录。', // 更新提示
      '确认删除',
      {
        confirmButtonText: '确定删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );
    
    isLoading.value = true;
    await deleteRdpMachine(machineId);
    ElMessage.success('主机已删除');
    handleFetchMachines(); // 刷新表格

  } catch (error) {
    if (error !== 'cancel') {
      console.error("Delete failed:", error);
      ElMessage.error(error.response?.data?.detail || '删除失败');
    }
  } finally {
    isLoading.value = false;
  }
};
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 18px;
  font-weight: 500;
}
.box-card {
  border-radius: 8px;
  border: 1px solid #e0e0e0;
}
</style>
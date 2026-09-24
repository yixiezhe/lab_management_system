<template>
  <el-form ref="formRef" :model="formData" label-width="100px">
    
    <div v-for="(item, index) in formData.items" :key="index" class="item-block">
      <el-form-item :label="'采购内容 ' + (index + 1)" :prop="'items.' + index + '.content'" :rules="rules.content">
        <el-input v-model="item.content" placeholder="请填写具体物品名称" />
      </el-form-item>
      
      <el-form-item label="规格" :prop="'items.' + index + '.specifications'">
        <el-input v-model="item.specifications" placeholder="规格型号 (选填)" />
      </el-form-item>
      
      <el-form-item label="采购链接" :prop="'items.' + index + '.purchase_link'" :rules="rules.purchase_link">
        <el-input v-model="item.purchase_link" placeholder="例如: https://item.taobao.com (选填)" />
      </el-form-item>

      <el-form-item label="单价" :prop="'items.' + index + '.unit_price'" :rules="rules.unit_price">
        <el-input-number v-model="item.unit_price" :precision="2" :step="1" :min="0" controls-position="right" />
      </el-form-item>

      <el-form-item label="数量" :prop="'items.' + index + '.quantity'" :rules="rules.quantity">
        <el-input-number v-model="item.quantity" :min="1" controls-position="right" />
      </el-form-item>
      
      <el-form-item label="小计">
        <span class="total-price">¥ {{ (item.unit_price * item.quantity).toFixed(2) }}</span>
      </el-form-item>
      
      <el-form-item v-if="formData.items.length > 1">
        <el-button type="danger" @click="removeItem(index)">删除此物品</el-button>
      </el-form-item>
    </div>

    <el-form-item>
      <el-button type="primary" @click="addItem">增加物品</el-button>
      <el-button type="success" @click="submitForm" style="margin-left: 10px;">{{ isEditMode ? '保存修改' : '提交申请' }}</el-button>
    </el-form-item>
  </el-form>
</template>

<script setup>
import { ref, watchEffect, computed } from 'vue';
import { cloneDeep } from 'lodash-es';
import apiClient from '@/api';
import { ElMessage } from 'element-plus';

const props = defineProps({
  initialData: {
    type: Object,
    default: null
  }
});
const emit = defineEmits(['submitSuccess']);
const isEditMode = computed(() => !!props.initialData);
const formRef = ref(null);

const createEmptyItem = () => ({ content: '', specifications: '', purchase_link: '', unit_price: 0, quantity: 1 });
const formData = ref({ items: [createEmptyItem()] });

const rules = ref({
  content: [{ required: true, message: '采购内容不能为空', trigger: 'blur' }],
  unit_price: [{ type: 'number', min: 0, message: '单价不能为负数', trigger: 'blur' }],
  quantity: [{ type: 'number', min: 1, message: '数量必须大于0', trigger: 'blur' }],
  purchase_link: [{ type: 'url', message: '请输入有效的URL', trigger: 'blur' }]
});

watchEffect(() => {
  if (isEditMode.value) {
    formData.value = cloneDeep(props.initialData);
  } else {
    // 在创建模式下，重置表单
    formRef.value?.resetFields();
    formData.value = { items: [createEmptyItem()] };
  }
});

const addItem = () => formData.value.items.push(createEmptyItem());
const removeItem = (index) => formData.value.items.splice(index, 1);

const submitForm = async () => {
  if (!formRef.value) return;
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (isEditMode.value) {
          await apiClient.patch(`/team-procurement/requests/${props.initialData.id}/`, formData.value);
          ElMessage.success('修改成功！');
        } else {
          await apiClient.post('/team-procurement/requests/', formData.value);
          ElMessage.success('小组请购申请提交成功！');
        }
        emit('submitSuccess');
      } catch (error) {
        console.error('提交失败:', error.response?.data);
        ElMessage.error('提交失败，请检查内容。');
      }
    } else {
      ElMessage.error('表单验证失败，请检查输入项！');
    }
  });
};
</script>

<style scoped>
/* 【修改点 2】添加块状布局的样式 */
.item-block {
  padding: 20px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  margin-bottom: 20px;
}
.total-price {
  font-size: 1.1em;
  color: #F56C6C;
  font-weight: bold;
}
/* 确保在块状布局中，表单项之间有合适的间距 */
.item-block .el-form-item {
  margin-bottom: 22px;
}
/* 最后一个表单项（删除按钮）不需要下边距 */
.item-block .el-form-item:last-child {
  margin-bottom: 0;
}
</style>
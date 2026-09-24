<!-- frontend/src/components/ProcurementForm.vue -->
<template>
  <div>
    <!-- 顶部三步选择 -->
    <el-form-item label="经费类型">
      <el-radio-group v-model="step1_expenseType" @change="resetStep(2)">
        <el-radio-button label="c2c">公对公</el-radio-button>
        <el-radio-button label="public">公共经费</el-radio-button>
      </el-radio-group>
    </el-form-item>

    <div v-if="step1_expenseType">
      <el-form-item label="选择平台">
        <el-select
          v-model="step2_platform"
          placeholder="请选择平台/服务"
          @change="resetStep(3)"
          :loading="isPlatformLoading"
        >
          <el-option
            v-for="platform in platformOptions"
            :key="platform.id"
            :label="platform.name"
            :value="platform.name"
          />
        </el-select>
      </el-form-item>
    </div>

    <div v-if="step1_expenseType && step2_platform">
      <el-form-item label="采购类型">
        <el-radio-group v-model="step3_purchaseType">
          <el-radio-button label="consumable">耗材</el-radio-button>
          <el-radio-button label="chemical">药品</el-radio-button>
        </el-radio-group>

        <div v-if="step1_expenseType === 'public' && currentDutyPerson" class="duty-person-info">
          📌 本日采购人为：<strong>{{ currentDutyPerson }}</strong>
        </div>
      </el-form-item>
    </div>

    <!-- 自动保存/清空 状态条 -->
    <el-alert
      v-if="showStatusBar"
      type="info"
      :closable="false"
      class="autosave-bar"
    >
      <template #title>
        已自动保存 {{ lastSavedDisplay }}
        <el-link type="primary" class="clear-link" @click="clearDraft">清空草稿</el-link>
      </template>
    </el-alert>

    <!-- 最终表单 -->
    <div v-if="showFinalForm" v-loading="isItemsLoading">
      <div v-if="!isItemsLoading && availableItems.length === 0" class="no-items-found">
        <el-alert title="未找到匹配的采购项目" type="warning" show-icon :closable="false">
          请检查您的筛选条件，或前往“白名单管理”页面添加对应的采购项目。
        </el-alert>
      </div>

      <div v-else>
        <el-divider>填写采购详情</el-divider>

        <el-form ref="requestFormRef" :model="requestData" label-width="100px">
          <div v-for="(item, index) in requestData.items" :key="index" class="item-block">
            <el-form-item
              label="采购内容"
              :prop="'items.' + index + '.content'"
              :rules="dynamicFormRules.content"
            >
              <el-select v-model="item.content" filterable placeholder="请从白名单中搜索或选择">
                <el-option
                  v-for="wlItem in availableItems"
                  :key="wlItem.id"
                  :label="wlItem.content"
                  :value="wlItem.content"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="CAS号">
              <el-input v-model="item.cas_number" />
            </el-form-item>
            <el-form-item label="货号">
              <el-input v-model="item.product_number" />
            </el-form-item>
            <el-form-item label="厂商" :prop="'items.' + index + '.manufacturer'">
              <el-input v-model="item.manufacturer" />
            </el-form-item>
            <el-form-item label="参数">
              <el-input v-model="item.parameters" />
            </el-form-item>

            <el-form-item
              label="规格"
              :prop="'items.' + index + '.specifications'"
              :rules="dynamicFormRules.specifications"
            >
              <el-input v-model="item.specifications" placeholder="选择“多多”或“药代”时必填" />
            </el-form-item>

            <el-form-item
              v-if="step1_expenseType === 'public'"
              label="采购链接"
              :prop="'items.' + index + '.purchase_link'"
              :rules="dynamicFormRules.purchase_link"
            >
              <el-input v-model="item.purchase_link" placeholder="公共经费申请必填" />
            </el-form-item>

            <el-form-item
              label="单价"
              :prop="'items.' + index + '.unit_price'"
              :rules="dynamicFormRules.unit_price"
            >
              <el-input-number
                v-model="item.unit_price"
                :precision="2"
                :step="0.1"
                :min="0"
                controls-position="right"
              />
            </el-form-item>

            <el-form-item
              label="数量"
              :prop="'items.' + index + '.quantity'"
              :rules="dynamicFormRules.quantity"
            >
              <el-input-number v-model="item.quantity" :min="1" controls-position="right" />
            </el-form-item>

            <el-form-item label="总价">
              <span class="total-price">¥ {{ (item.unit_price * item.quantity).toFixed(2) }}</span>
            </el-form-item>

            <el-form-item v-if="requestData.items.length > 1">
              <el-button type="danger" @click="removeItem(index)">删除此物品</el-button>
            </el-form-item>
          </div>

          <el-form-item>
            <el-button type="success" @click="submitRequest">
              {{ isEditMode ? '保存修改' : '提交申请' }}
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch, onBeforeUnmount } from 'vue';
import apiClient from '@/api';
import { ElMessage } from 'element-plus';
import { cloneDeep, debounce } from 'lodash-es';
import { useAuthStore } from '@/stores/auth';
import {
  DEFAULT_PUBLIC_DUTY_SCHEDULE,
  fetchPublicDutySchedule,
  getTodayPublicDutyPerson,
} from '@/utils/publicDutySchedule';

const authStore = useAuthStore();

const props = defineProps({
  initialData: { type: Object, default: null }
});
const emit = defineEmits(['submitSuccess']);
const isEditMode = computed(() => !!props.initialData);

/* ----------------------- 步骤 & 数据 ----------------------- */
const step1_expenseType = ref(null);
const step2_platform = ref(null);
const step3_purchaseType = ref(null);

const requestFormRef = ref(null);
const availableItems = ref([]);
const isItemsLoading = ref(false);
const showFinalForm = ref(false);
const isPlatformLoading = ref(false);
const platformOptions = ref([]);

/* ----------------------- 当日值班员 ----------------------- */
const currentDutyPerson = ref('');
const dutySchedule = ref(DEFAULT_PUBLIC_DUTY_SCHEDULE.map(item => ({ ...item })));
const applyTodayDutyPerson = () => {
  currentDutyPerson.value = getTodayPublicDutyPerson(dutySchedule.value);
};
applyTodayDutyPerson();

const loadDutySchedule = async () => {
  try {
    dutySchedule.value = await fetchPublicDutySchedule();
  } catch {
    dutySchedule.value = DEFAULT_PUBLIC_DUTY_SCHEDULE.map(item => ({ ...item }));
  } finally {
    applyTodayDutyPerson();
  }
};

/* ----------------------- 表单模型 ----------------------- */
const createEmptyItem = () => ({
  content: '',
  cas_number: '',
  product_number: '',
  manufacturer: '',
  parameters: '',
  specifications: '',
  unit_price: 0,
  quantity: 1,
  purchase_type: '',
  purchase_link: ''
});
const requestData = ref({ items: [createEmptyItem()] });

/* ----------------------- 平台 & 白名单 ----------------------- */
const fetchPlatforms = async (category) => {
  if (!category) {
    platformOptions.value = [];
    return;
  }
  isPlatformLoading.value = true;
  try {
    const { data } = await apiClient.get('/procurement/platforms/', { params: { category } });
    platformOptions.value = data;
  } catch {
    platformOptions.value = [];
    ElMessage.error('获取平台列表失败');
  } finally {
    isPlatformLoading.value = false;
  }
};

const fetchAvailableItems = async () => {
  if (!step1_expenseType.value || !step2_platform.value || !step3_purchaseType.value) {
    showFinalForm.value = false;
    return;
  }
  isItemsLoading.value = true;
  showFinalForm.value = true;
  try {
    const params = {
      main_category: step1_expenseType.value,
      platform: step2_platform.value,
      purchase_type: step3_purchaseType.value
    };
    const { data } = await apiClient.get('/procurement/whitelist-items/', { params });
    availableItems.value = data;
  } catch {
    availableItems.value = [];
    ElMessage.error('获取可选采购物品列表失败！');
  } finally {
    isItemsLoading.value = false;
  }
};

/* ----------------------- 重置步骤 ----------------------- */
const suspendWatch = ref(false);

const resetStep = (step) => {
  if (suspendWatch.value) return; // 草稿恢复中不重置
  if (step <= 2) {
    step2_platform.value = null;
    platformOptions.value = [];
  }
  if (step <= 3) {
    step3_purchaseType.value = null;
  }
  availableItems.value = [];
  showFinalForm.value = false;
  requestData.value.items = [createEmptyItem()];
};

/* ----------------------- 自动保存（localStorage） ----------------------- */
const userKey = computed(() => authStore.user?.id || 'guest');
const DRAFT_KEY = computed(() => `procurement_draft:v4:${userKey.value}`);

const lastSavedAt = ref(0);
const showStatusBar = ref(false);
const lastSavedDisplay = computed(() => {
  if (!lastSavedAt.value) return '';
  const d = new Date(lastSavedAt.value);
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  const ss = String(d.getSeconds()).padStart(2, '0');
  return `${hh}:${mm}:${ss}`;
});

const doSaveDraft = () => {
  try {
    const payload = {
      step1: step1_expenseType.value,
      step2: step2_platform.value,
      step3: step3_purchaseType.value,
      form: requestData.value,
      ts: Date.now(),
      v: 4
    };
    localStorage.setItem(DRAFT_KEY.value, JSON.stringify(payload));
    lastSavedAt.value = payload.ts;
    showStatusBar.value = true;
  } catch {}
};
const saveDraft = debounce(doSaveDraft, 500);

const clearDraft = () => {
  localStorage.removeItem(DRAFT_KEY.value);
  lastSavedAt.value = 0;
  showStatusBar.value = false;
  // 同步把表单置空
  step1_expenseType.value = null;
  step2_platform.value = null;
  step3_purchaseType.value = null;
  requestData.value = { items: [createEmptyItem()] };
  availableItems.value = [];
  platformOptions.value = [];
  showFinalForm.value = false;
};

/* ----------------------- 恢复草稿 ----------------------- */
const restoreDraft = async () => {
  try {
    const raw = localStorage.getItem(DRAFT_KEY.value);
    if (!raw) return;

    const data = JSON.parse(raw);
    if (!data || data.v !== 4) return;

    suspendWatch.value = true; // 1) 暂停 watch，避免 resetStep 误清
    // 2) 先设置第一步
    step1_expenseType.value = data.step1 || null;

    // 3) 拉平台列表，再设置平台
    if (step1_expenseType.value) {
      await fetchPlatforms(step1_expenseType.value);
    }
    step2_platform.value = data.step2 || null;

    // 4) 设置采购类型 → 拉白名单
    step3_purchaseType.value = data.step3 || null;
    if (
      step1_expenseType.value &&
      step2_platform.value &&
      step3_purchaseType.value
    ) {
      await fetchAvailableItems();
    }

    // 5) 填充表单
    if (data.form && Array.isArray(data.form.items) && data.form.items.length > 0) {
      requestData.value = cloneDeep(data.form);
      requestData.value.items = requestData.value.items.map((it) => ({
        ...createEmptyItem(),
        ...it
      }));
    } else {
      requestData.value = { items: [createEmptyItem()] };
    }

    // 6) 展示最终表单
    showFinalForm.value = !!(
      step1_expenseType.value &&
      step2_platform.value &&
      step3_purchaseType.value
    );

    lastSavedAt.value = data.ts || Date.now();
    showStatusBar.value = true;
  } catch {
    // ignore
  } finally {
    // 7) 恢复 watch
    suspendWatch.value = false;
  }
};

/* ----------------------- watch：在非恢复阶段才保存 ----------------------- */
watch(
  step1_expenseType,
  async (val) => {
    if (suspendWatch.value) return;
    // 经费类型变化时：重置后续步骤并重新拉平台列表
    resetStep(2);
    if (val) {
      await fetchPlatforms(val);
    }
    saveDraft();
  }
);

watch(step2_platform, () => {
  if (!suspendWatch.value) saveDraft();
});

watch(step3_purchaseType, async () => {
  if (suspendWatch.value) return;
  await fetchAvailableItems();
  saveDraft();
});

watch(
  requestData,
  () => {
    if (!suspendWatch.value) saveDraft();
  },
  { deep: true }
);

/* ----------------------- 生命周期 ----------------------- */
onMounted(async () => {
  await loadDutySchedule();

  // 编辑模式：不启用草稿（避免串数据）
  if (isEditMode.value) {
    const data = cloneDeep(props.initialData);
    step1_expenseType.value = data.expense_type;
    await fetchPlatforms(step1_expenseType.value);
    step2_platform.value = data.platform;
    if (data.items?.length) step3_purchaseType.value = data.items[0].purchase_type;
    await fetchAvailableItems();
    requestData.value = data;
    showFinalForm.value = true;
    showStatusBar.value = false;
    return;
  }

  // 新建：优先恢复草稿
  await restoreDraft();

  // 若无草稿，常规初始化（此时等用户选择经费类型后，由 watch 去拉平台列表）
  if (!step1_expenseType.value) {
    showFinalForm.value = false;
  }
});

// 页面关闭/刷新也保存一次
const beforeUnload = () => doSaveDraft();
window.addEventListener('beforeunload', beforeUnload);
onBeforeUnmount(() => window.removeEventListener('beforeunload', beforeUnload));

/* ----------------------- 其余逻辑 ----------------------- */
const removeItem = (index) => requestData.value.items.splice(index, 1);

const dynamicFormRules = computed(() => {
  const rules = {
    content: [{ required: true, message: '必须选择采购内容', trigger: 'change' }],
    unit_price: [
      {
        validator: (rule, value, cb) =>
          value <= 0 ? cb(new Error('单价必须大于0')) : cb(),
        trigger: 'blur'
      }
    ],
    quantity: [{ required: true, message: '数量不能为空', trigger: 'blur' }]
  };

  if (['多多', '药代'].includes(step2_platform.value)) {
    rules.specifications = [
      {
        required: true,
        message: '当选择“多多”或“药代”平台时，规格为必填项',
        trigger: 'blur'
      }
    ];
  } else {
    rules.specifications = [];
  }

  if (step1_expenseType.value === 'public') {
    rules.purchase_link = [
      { required: true, message: '公共经费申请必须填写采购链接', trigger: 'blur' }
    ];
  } else {
    rules.purchase_link = [];
  }
  return rules;
});

const submitRequest = async () => {
  if (!requestFormRef.value) return;

  await requestFormRef.value.validate(async (valid) => {
    if (!valid) {
      ElMessage.error('表单验证失败，请检查输入项！');
      return;
    }

    const raw_total_price = requestData.value.items.reduce(
      (t, it) =>
        t +
        (Number(it.unit_price) || 0) * (Number(it.quantity) || 0),
      0
    );
    const total_price = Number(raw_total_price.toFixed(2));

    const payload = {
      ...requestData.value,
      expense_type: step1_expenseType.value,
      platform: step2_platform.value,
      total_price
    };
    payload.items.forEach((it) => {
      it.purchase_type = step3_purchaseType.value;
      delete it.main_category;
    });

    let endpoint = '';
    if (step1_expenseType.value === 'public')
      endpoint = '/procurement/public-purchase-requests/';
    else if (step1_expenseType.value === 'c2c')
      endpoint = '/procurement/c2c-purchase-requests/';
    else {
      ElMessage.error('未知的经费类型，无法提交！');
      return;
    }

    try {
      if (isEditMode.value) {
        await apiClient.patch(`${endpoint}${props.initialData.id}/`, payload);
        ElMessage.success('修改成功！');
      } else {
        await apiClient.post(endpoint, payload);
        ElMessage.success('采购申请提交成功！');
      }
      // 提交成功清空草稿
      clearDraft();
      emit('submitSuccess');
    } catch (error) {
      const data = error.response?.data;
      let msg = '提交失败，请检查内容。';
      if (data) {
        const firstKey = Object.keys(data)[0];
        if (firstKey) {
          if (Array.isArray(data[firstKey]) && data[firstKey][0])
            msg = `${firstKey}: ${data[firstKey][0]}`;
          else if (typeof data[firstKey] === 'string')
            msg = `${firstKey}: ${data[firstKey]}`;
        }
      }
      ElMessage.error(msg);
    }
  });
};
</script>

<style scoped>
.item-block {
  padding: 20px;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  margin-bottom: 20px;
}
.el-select {
  width: 100%;
}
.total-price {
  font-size: 1.2em;
  color: #F56C6C;
  font-weight: bold;
}
.no-items-found {
  margin-top: 20px;
}

.duty-person-info {
  display: inline-block;
  margin-left: 20px;
  vertical-align: middle;
  padding: 5px 10px;
  background-color: #f0f9eb;
  color: #67c23a;
  border-radius: 4px;
  font-size: 13px;
}
.duty-person-info strong {
  font-weight: 600;
}

.autosave-bar {
  margin: 12px 0 6px;
  padding: 8px 12px;
}
.clear-link {
  margin-left: 12px;
  font-size: 13px;
}
</style>

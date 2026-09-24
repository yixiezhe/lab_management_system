<template>
  <div class="group-affairs-page">
    <div class="page-header">
      <div>
        <h1>小组事务</h1>
        <div v-if="selectedBoard" class="group-meta">
          {{ selectedBoard.tutor?.name }}小组
          <el-tag :type="canManage ? 'success' : 'info'" effect="plain">
            {{ canManage ? '小组管理员' : '小组成员' }}
          </el-tag>
        </div>
      </div>

      <div class="header-actions">
        <el-select
          v-if="boards.length > 1"
          v-model="selectedBoardId"
          filterable
          placeholder="选择小组"
          class="board-select"
        >
          <el-option
            v-for="board in boards"
            :key="board.id"
            :label="`${board.tutor?.name || '未命名'}小组`"
            :value="board.id"
          />
        </el-select>
        <el-button :icon="Refresh" :loading="loading" @click="fetchBoards">刷新</el-button>
      </div>
    </div>

    <el-skeleton v-if="loading && boards.length === 0" :rows="8" animated />

    <el-empty v-else-if="boards.length === 0" description="暂无可查看的小组事务" />

    <template v-else-if="selectedBoard">
      <div class="affairs-grid">
      <section class="panel board-panel">
        <div class="section-header">
          <div>
            <h2>事务板</h2>
            <div class="section-subtitle">最后更新：{{ formatDate(selectedBoard.updated_at) || '暂无' }}</div>
          </div>
          <el-button
            v-if="canManage"
            type="primary"
            :icon="Check"
            :loading="savingText"
            @click="saveTextContent"
          >
            保存
          </el-button>
        </div>

        <el-input
          v-model="textDraft"
          type="textarea"
          :rows="9"
          maxlength="6000"
          show-word-limit
          :readonly="!canManage"
          placeholder="填写小组事务内容"
        />
      </section>

      <section class="panel purchase-form-panel">
        <div class="section-header">
          <div>
            <h2>采购轮班与请购</h2>
            <div class="section-subtitle">按采购轮班名单依次自动分配采购人</div>
          </div>
        </div>

        <el-form v-if="canManage" label-position="top" class="notice-form">
          <el-form-item label="采购轮班名单（选择顺序即轮班顺序）">
            <el-select v-model="purchaseRotationDraft" multiple filterable placeholder="请选择并按顺序添加成员" class="member-select">
              <el-option v-for="member in selectedBoard.members" :key="member.id" :label="member.name" :value="member.id" />
            </el-select>
          </el-form-item>
          <div class="form-actions">
            <el-button type="primary" :loading="savingRotation" @click="savePurchaseRotation">保存轮班名单</el-button>
          </div>
        </el-form>

        <el-divider v-if="canManage" />
        <el-form label-position="top" class="notice-form">
          <el-form-item label="要购买的东西">
            <el-input v-model="purchaseForm.items" type="textarea" :rows="3" maxlength="2000" show-word-limit placeholder="填写物品名称、规格、数量等" />
          </el-form-item>
          <el-form-item label="备注（选填）">
            <el-input v-model="purchaseForm.note" maxlength="500" />
          </el-form-item>
          <div class="form-actions">
            <el-button type="primary" :loading="creatingPurchase" @click="createPurchase">发起请购</el-button>
          </div>
        </el-form>

      </section>

      <section class="panel purchase-list-panel">
        <div class="section-header compact-header">
          <div>
            <h2>采购列表</h2>
            <div class="section-subtitle">跟踪支付、到货及报销进度</div>
          </div>
          <el-tag effect="plain" round>{{ purchases.length }} 项</el-tag>
        </div>
        <el-empty v-if="purchases.length === 0" description="暂无组内采购记录" :image-size="72" />
        <div v-else class="purchase-cards">
          <article v-for="row in purchases" :key="row.id" class="purchase-card">
            <div class="purchase-card-main">
              <div class="purchase-card-heading">
                <span class="purchase-id">#{{ row.id }}</span>
                <h3>{{ row.items }}</h3>
                <el-tag :type="statusTagType(row.status)" effect="light" round>{{ row.status_display }}</el-tag>
              </div>
              <div v-if="row.note" class="purchase-note">备注：{{ row.note }}</div>
              <div class="purchase-meta-grid">
                <div><span>请购人</span><strong>{{ row.requester?.name || '-' }}</strong></div>
                <div><span>采购人</span><strong>{{ row.buyer?.name || '-' }}</strong></div>
                <div><span>支付金额</span><strong class="amount">{{ row.payment_amount ? `¥ ${row.payment_amount}` : '待填写' }}</strong></div>
                <div><span>发起时间</span><strong>{{ formatDate(row.created_at) }}</strong></div>
              </div>
              <div class="purchase-progress" :style="{ '--progress': `${purchaseProgress(row.status)}%` }">
                <div v-for="(step, index) in purchaseSteps" :key="step.key" :class="['progress-step', { active: purchaseStepIndex(row.status) >= index }]">
                  <i></i><span>{{ step.label }}</span>
                </div>
              </div>
              <div class="purchase-details">
                <span v-if="row.paid_at">支付：{{ formatDate(row.paid_at) }}</span>
                <span v-if="row.arrived_at">到货：{{ formatDate(row.arrived_at) }}</span>
                <span v-if="row.reimbursed_at">报销：{{ formatDate(row.reimbursed_at) }}</span>
              </div>
              <div v-if="row.payment_proof || row.invoice || row.item_image" class="purchase-files">
                <el-link v-if="row.payment_proof" :href="resolveMediaUrl(row.payment_proof)" target="_blank" download>支付凭证</el-link>
                <el-link v-if="row.invoice" :href="resolveMediaUrl(row.invoice)" target="_blank" download>发票</el-link>
                <el-link v-if="row.item_image" :href="resolveMediaUrl(row.item_image)" target="_blank" download>实物图片</el-link>
              </div>
            </div>
            <div class="purchase-card-action">
              <div v-if="isCurrentBuyer(row) && row.status === 'assigned'" class="purchase-action">
                <el-input v-model="purchaseDrafts[row.id].amount" type="number" min="0.01" placeholder="支付金额" />
                <label class="file-picker">支付凭证<input type="file" accept="image/*,.pdf" @change="setPurchaseFile(row.id, 'payment_proof', $event)" /></label>
                <el-button type="primary" @click="submitPayment(row)">登记支付</el-button>
              </div>
              <div v-else-if="isCurrentBuyer(row) && row.status === 'paid'" class="purchase-action">
                <label class="file-picker">上传发票<input type="file" accept="image/*,.pdf" @change="setPurchaseFile(row.id, 'invoice', $event)" /></label>
                <label class="file-picker">上传实物图<input type="file" accept="image/*" @change="setPurchaseFile(row.id, 'item_image', $event)" /></label>
                <el-button type="primary" @click="submitArrival(row)">登记到货</el-button>
              </div>
              <el-button v-else-if="isCurrentBuyer(row) && row.status === 'arrived'" type="success" plain @click="markReimbursed(row)">确认已报销</el-button>
              <span v-else class="action-hint">{{ row.status === 'reimbursed' ? '全部流程已完成' : '等待采购人处理' }}</span>
              <el-button v-if="canManage" type="danger" link :icon="Delete" class="delete-purchase" @click="deletePurchase(row)">删除记录</el-button>
            </div>
          </article>
        </div>
      </section>

      <section class="panel notice-panel">
        <div class="section-header">
          <div>
            <h2>组内弹窗提醒</h2>
            <div class="section-subtitle">发布后仅当前小组成员弹窗可见</div>
          </div>
        </div>

        <el-form v-if="canManage" label-position="top" class="notice-form">
          <el-form-item label="标题">
            <el-input v-model="noticeForm.title" maxlength="120" show-word-limit placeholder="小组提醒" />
          </el-form-item>
          <el-form-item label="内容">
            <el-input
              v-model="noticeForm.content"
              type="textarea"
              :rows="4"
              maxlength="2000"
              show-word-limit
              placeholder="填写提醒内容"
            />
          </el-form-item>
          <div class="form-actions">
            <el-button
              type="primary"
              :icon="Promotion"
              :loading="publishingNotice"
              @click="publishNotice"
            >
              发布弹窗
            </el-button>
          </div>
        </el-form>

        <el-empty v-else description="仅小组管理员可发布提醒" :image-size="68" />
      </section>

      <section class="panel duty-panel">
        <div class="section-header duty-header">
          <div>
            <h2>值日表</h2>
            <div class="section-subtitle">未选择人员的日期保持留空</div>
          </div>
          <div class="duty-actions">
            <el-switch
              v-model="dutyReminderDraft"
              :disabled="!canManage"
              active-text="每日提醒"
            />
            <el-button
              v-if="canManage"
              type="primary"
              :icon="Check"
              :loading="savingDuty"
              @click="saveDutySchedule"
            >
              保存
            </el-button>
          </div>
        </div>

        <el-table :data="dutyDraft" border stripe class="duty-table">
          <el-table-column prop="weekday_label" label="日期" width="120" />
          <el-table-column label="值日人员" min-width="220">
            <template #default="{ row }">
              <el-select
                v-if="canManage"
                v-model="row.user_id"
                clearable
                filterable
                placeholder="留空"
                class="member-select"
              >
                <el-option
                  v-for="member in selectedBoard.members"
                  :key="member.id"
                  :label="member.name"
                  :value="member.id"
                />
              </el-select>
              <span v-else>{{ row.name || '未安排' }}</span>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section class="panel members-panel">
        <div class="section-header">
          <div>
            <h2>小组管理员</h2>
            <div class="section-subtitle">导师为默认管理员</div>
          </div>
        </div>

        <el-table :data="selectedBoard.members" border stripe>
          <el-table-column prop="username" label="学号/工号" width="160" />
          <el-table-column prop="name" label="姓名" min-width="140" />
          <el-table-column label="身份" min-width="180">
            <template #default="{ row }">
              <div class="role-tags">
                <el-tag v-if="row.id === selectedBoard.tutor?.id" type="warning" effect="plain">导师</el-tag>
                <el-tag v-if="isAdmin(row)" type="success" effect="plain">小组管理员</el-tag>
                <el-tag v-if="!isAdmin(row) && row.id !== selectedBoard.tutor?.id" type="info" effect="plain">
                  成员
                </el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column v-if="canManage" label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.id === selectedBoard.tutor?.id"
                type="info"
                link
                disabled
              >
                默认管理员
              </el-button>
              <el-button
                v-else-if="isAdmin(row)"
                type="danger"
                link
                :icon="Delete"
                :loading="rowActionLoadingId === row.id"
                @click="removeAdmin(row)"
              >
                移除
              </el-button>
              <el-button
                v-else
                type="primary"
                link
                :icon="Plus"
                :loading="rowActionLoadingId === row.id"
                @click="appointAdmin(row)"
              >
                任命
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </section>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import apiClient from '@/api';
import { ElMessage, ElMessageBox } from 'element-plus';
import { Check, Delete, Plus, Promotion, Refresh } from '@element-plus/icons-vue';
import { useAuthStore } from '@/stores/auth';

const authStore = useAuthStore();

const weekdayLabels = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];
const purchaseSteps = [
  { key: 'assigned', label: '已分配' },
  { key: 'paid', label: '已支付' },
  { key: 'arrived', label: '已到货' },
  { key: 'reimbursed', label: '已报销' },
];

const boards = ref([]);
const selectedBoardId = ref(null);
const loading = ref(false);
const savingText = ref(false);
const savingDuty = ref(false);
const publishingNotice = ref(false);
const rowActionLoadingId = ref(null);
const textDraft = ref('');
const dutyReminderDraft = ref(false);
const dutyDraft = ref([]);
const purchases = ref([]);
const purchaseRotationDraft = ref([]);
const savingRotation = ref(false);
const creatingPurchase = ref(false);
const purchaseDrafts = reactive({});
const purchaseForm = reactive({ items: '', note: '' });

const noticeForm = reactive({
  title: '小组提醒',
  content: '',
});

const normalizeListResponse = (data) => {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.results)) return data.results;
  return [];
};

const getErrorDetail = (error, fallback) => {
  const status = error.response?.status;
  const data = error.response?.data;
  const detail =
    data?.detail ||
    data?.error ||
    (typeof data === 'string' ? data : '') ||
    error.message ||
    fallback;
  if (status === 404) {
    return `${fallback}（404：接口不存在，请重启 Django 后端后再刷新页面）`;
  }
  return status ? `${fallback}（${status}：${detail}）` : detail || fallback;
};

const selectedBoard = computed(() => (
  boards.value.find(board => board.id === selectedBoardId.value) || null
));

const canManage = computed(() => !!selectedBoard.value?.can_manage);

const adminIds = computed(() => {
  const ids = new Set();
  (selectedBoard.value?.admins || []).forEach((entry) => {
    if (entry.user?.id) ids.add(entry.user.id);
  });
  return ids;
});

const isAdmin = (member) => adminIds.value.has(member.id);

const defaultDuty = () => weekdayLabels.map((label, index) => ({
  weekday: index,
  weekday_label: label,
  user_id: null,
  name: '',
}));

const applyBoardDrafts = () => {
  const board = selectedBoard.value;
  if (!board) {
    textDraft.value = '';
    dutyReminderDraft.value = false;
    dutyDraft.value = defaultDuty();
    purchaseRotationDraft.value = [];
    return;
  }

  textDraft.value = board.text_content || '';
  dutyReminderDraft.value = !!board.duty_reminder_enabled;
  purchaseRotationDraft.value = Array.isArray(board.purchase_rotation) ? [...board.purchase_rotation] : [];
  const sourceSchedule = Array.isArray(board.duty_schedule) ? board.duty_schedule : defaultDuty();
  const weekdayMap = new Map(sourceSchedule.map(item => [Number(item.weekday), item]));
  dutyDraft.value = weekdayLabels.map((label, weekday) => {
    const item = weekdayMap.get(weekday) || {};
    return {
      weekday,
      weekday_label: item.weekday_label || label,
      user_id: item.user_id || null,
      name: item.name || '',
    };
  });
};

const ensurePurchaseDraft = (id) => {
  if (!purchaseDrafts[id]) purchaseDrafts[id] = { amount: '', payment_proof: null, invoice: null, item_image: null };
  return purchaseDrafts[id];
};

const fetchPurchases = async () => {
  if (!selectedBoardId.value) return;
  try {
    const response = await apiClient.get(`/group-affairs/boards/${selectedBoardId.value}/purchases/`);
    purchases.value = normalizeListResponse(response.data);
    purchases.value.forEach(row => ensurePurchaseDraft(row.id));
  } catch (error) {
    ElMessage.error(getErrorDetail(error, '获取组内采购失败'));
  }
};

const savePurchaseRotation = async () => {
  savingRotation.value = true;
  try {
    const response = await apiClient.patch(`/group-affairs/boards/${selectedBoardId.value}/`, { purchase_rotation: purchaseRotationDraft.value });
    replaceSelectedBoard(response.data);
    ElMessage.success('采购轮班名单已保存');
  } catch (error) {
    ElMessage.error(error.response?.data?.purchase_rotation?.[0] || getErrorDetail(error, '保存采购轮班名单失败'));
  } finally { savingRotation.value = false; }
};

const createPurchase = async () => {
  if (!purchaseForm.items.trim()) return ElMessage.warning('请填写要购买的东西');
  creatingPurchase.value = true;
  try {
    const response = await apiClient.post(`/group-affairs/boards/${selectedBoardId.value}/purchases/`, purchaseForm);
    purchaseForm.items = ''; purchaseForm.note = '';
    ElMessage.success(`请购已提交，已分配给 ${response.data.buyer?.name || '采购人'}`);
    await fetchPurchases();
  } catch (error) { ElMessage.error(getErrorDetail(error, '发起请购失败')); }
  finally { creatingPurchase.value = false; }
};

const isCurrentBuyer = row => Number(row.buyer?.id) === Number(authStore.user?.id);
const purchaseStepIndex = status => Math.max(0, purchaseSteps.findIndex(step => step.key === status));
const purchaseProgress = status => (purchaseStepIndex(status) / (purchaseSteps.length - 1)) * 100;
const statusTagType = status => ({ assigned: 'warning', paid: 'primary', arrived: 'success', reimbursed: 'info' }[status] || 'info');
const resolveMediaUrl = (value) => {
  if (!value) return '';
  try {
    const parsed = new URL(value, window.location.origin);
    return `${parsed.pathname}${parsed.search}`;
  } catch {
    return value;
  }
};
const setPurchaseFile = (id, field, event) => { ensurePurchaseDraft(id)[field] = event.target.files?.[0] || null; };

const submitPayment = async (row) => {
  const draft = ensurePurchaseDraft(row.id);
  if (!draft.amount || !draft.payment_proof) return ElMessage.warning('请填写支付金额并上传支付凭证');
  const data = new FormData(); data.append('payment_amount', draft.amount); data.append('payment_proof', draft.payment_proof);
  try { await apiClient.post(`/group-affairs/boards/${selectedBoardId.value}/purchases/${row.id}/pay/`, data); ElMessage.success('支付信息已登记'); await fetchPurchases(); }
  catch (error) { ElMessage.error(getErrorDetail(error, '登记支付失败')); }
};

const submitArrival = async (row) => {
  const draft = ensurePurchaseDraft(row.id);
  if (!draft.invoice || !draft.item_image) return ElMessage.warning('请同时上传发票和实物图片');
  const data = new FormData(); data.append('invoice', draft.invoice); data.append('item_image', draft.item_image);
  try { await apiClient.post(`/group-affairs/boards/${selectedBoardId.value}/purchases/${row.id}/arrive/`, data); ElMessage.success('到货材料已上传'); await fetchPurchases(); }
  catch (error) { ElMessage.error(getErrorDetail(error, '登记到货失败')); }
};

const markReimbursed = async (row) => {
  try { await apiClient.post(`/group-affairs/boards/${selectedBoardId.value}/purchases/${row.id}/reimburse/`); ElMessage.success('已标记为完成报销'); await fetchPurchases(); }
  catch (error) { ElMessage.error(getErrorDetail(error, '标记报销失败')); }
};

const deletePurchase = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定删除采购单 #${row.id} 吗？相关支付凭证、发票和实物图片也会一并删除。`,
      '删除采购记录',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消', confirmButtonClass: 'el-button--danger' },
    );
    await apiClient.delete(`/group-affairs/boards/${selectedBoardId.value}/purchases/${row.id}/`);
    ElMessage.success('采购记录已删除');
    await fetchPurchases();
  } catch (error) {
    if (error === 'cancel' || error === 'close') return;
    ElMessage.error(getErrorDetail(error, '删除采购记录失败'));
  }
};

const replaceSelectedBoard = (board) => {
  const index = boards.value.findIndex(item => item.id === board.id);
  if (index >= 0) {
    boards.value.splice(index, 1, board);
  } else {
    boards.value.push(board);
  }
};

const fetchBoards = async () => {
  loading.value = true;
  try {
    const response = await apiClient.get('/group-affairs/boards/');
    const list = normalizeListResponse(response.data);
    boards.value = list;

    if (list.length > 0) {
      const stillExists = list.some(board => board.id === selectedBoardId.value);
      selectedBoardId.value = stillExists ? selectedBoardId.value : list[0].id;
      applyBoardDrafts();
      await fetchPurchases();
    } else {
      selectedBoardId.value = null;
      applyBoardDrafts();
      purchases.value = [];
    }
  } catch (error) {
    ElMessage.error(getErrorDetail(error, '获取小组事务失败'));
  } finally {
    loading.value = false;
  }
};

const saveTextContent = async () => {
  if (!selectedBoard.value) return;
  savingText.value = true;
  try {
    const response = await apiClient.patch(`/group-affairs/boards/${selectedBoard.value.id}/`, {
      text_content: textDraft.value,
    });
    replaceSelectedBoard(response.data);
    ElMessage.success('事务板已保存');
  } catch (error) {
    ElMessage.error(getErrorDetail(error, '保存事务板失败'));
  } finally {
    savingText.value = false;
  }
};

const saveDutySchedule = async () => {
  if (!selectedBoard.value) return;
  savingDuty.value = true;
  try {
    const response = await apiClient.patch(`/group-affairs/boards/${selectedBoard.value.id}/`, {
      duty_schedule: dutyDraft.value.map(item => ({
        weekday: item.weekday,
        user_id: item.user_id || null,
      })),
      duty_reminder_enabled: dutyReminderDraft.value,
    });
    replaceSelectedBoard(response.data);
    applyBoardDrafts();
    ElMessage.success('值日表已保存');
  } catch (error) {
    const detail =
      error.response?.data?.duty_schedule?.[0] ||
      getErrorDetail(error, '保存值日表失败');
    ElMessage.error(detail);
  } finally {
    savingDuty.value = false;
  }
};

const publishNotice = async () => {
  if (!selectedBoard.value) return;
  const title = noticeForm.title.trim();
  const content = noticeForm.content.trim();
  if (!title || !content) {
    ElMessage.warning('请填写弹窗标题和内容');
    return;
  }

  publishingNotice.value = true;
  try {
    await apiClient.post(`/group-affairs/boards/${selectedBoard.value.id}/notices/`, {
      title,
      content,
    });
    noticeForm.title = '小组提醒';
    noticeForm.content = '';
    ElMessage.success('组内弹窗已发布');
  } catch (error) {
    const detail =
      error.response?.data?.title?.[0] ||
      error.response?.data?.content?.[0] ||
      getErrorDetail(error, '发布组内弹窗失败');
    ElMessage.error(detail);
  } finally {
    publishingNotice.value = false;
  }
};

const appointAdmin = async (member) => {
  if (!selectedBoard.value) return;
  rowActionLoadingId.value = member.id;
  try {
    const response = await apiClient.post(`/group-affairs/boards/${selectedBoard.value.id}/admins/`, {
      user_id: member.id,
    });
    replaceSelectedBoard(response.data);
    ElMessage.success(`已任命 ${member.name} 为小组管理员`);
  } catch (error) {
    ElMessage.error(getErrorDetail(error, '任命小组管理员失败'));
  } finally {
    rowActionLoadingId.value = null;
  }
};

const removeAdmin = async (member) => {
  if (!selectedBoard.value) return;
  rowActionLoadingId.value = member.id;
  try {
    const response = await apiClient.delete(`/group-affairs/boards/${selectedBoard.value.id}/admins/${member.id}/`);
    replaceSelectedBoard(response.data);
    ElMessage.success(`已移除 ${member.name} 的小组管理员身份`);
  } catch (error) {
    ElMessage.error(getErrorDetail(error, '移除小组管理员失败'));
  } finally {
    rowActionLoadingId.value = null;
  }
};

const formatDate = (value) => {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('zh-CN', { hour12: false });
};

watch(selectedBoardId, () => {
  applyBoardDrafts();
  fetchPurchases();
});

onMounted(fetchBoards);
</script>

<style scoped>
.group-affairs-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.affairs-grid {
  display: grid;
  grid-template-columns: repeat(12, minmax(0, 1fr));
  grid-template-areas:
    'board board board board board board board board board board board board'
    'purchase-form purchase-form purchase-form purchase-form purchase-form purchase-form notice notice notice notice notice notice'
    'purchase-list purchase-list purchase-list purchase-list purchase-list purchase-list purchase-list purchase-list purchase-list purchase-list purchase-list purchase-list'
    'duty duty duty duty duty duty members members members members members members';
  gap: 14px;
  align-items: stretch;
}

.board-panel { grid-area: board; }
.purchase-form-panel { grid-area: purchase-form; }
.notice-panel { grid-area: notice; }
.purchase-list-panel { grid-area: purchase-list; }
.duty-panel { grid-area: duty; }
.members-panel { grid-area: members; }

.page-header,
.section-header,
.duty-actions,
.header-actions,
.notice-title-row,
.form-actions {
  display: flex;
  align-items: center;
}

.page-header,
.section-header,
.notice-title-row {
  justify-content: space-between;
  gap: 16px;
}

.page-header h1,
.section-header h2,
.notice-title-row h3 {
  margin: 0;
  color: #303133;
}

.page-header h1 {
  font-size: 24px;
}

.section-header h2 {
  font-size: 18px;
}

.group-meta,
.section-subtitle,
.notice-title-row span,
.notice-author {
  color: #909399;
  font-size: 13px;
}

.group-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 6px;
}

.header-actions,
.duty-actions {
  justify-content: flex-end;
  gap: 10px;
}

.board-select {
  width: 220px;
}

.panel {
  min-width: 0;
  padding: 20px;
  background: #fff;
  border: 1px solid #e7eaf0;
  border-radius: 12px;
  box-shadow: 0 5px 18px rgba(31, 45, 61, 0.055);
  transition: box-shadow 0.2s ease, transform 0.2s ease;
}

.panel:hover {
  box-shadow: 0 9px 24px rgba(31, 45, 61, 0.085);
}

.board-panel {
  position: relative;
  overflow: hidden;
  padding: 24px;
  border-color: #b9d6ff;
  background: linear-gradient(120deg, #f2f8ff 0%, #fff 55%, #f3f9ff 100%);
  box-shadow: 0 9px 28px rgba(64, 130, 220, 0.12);
}

.board-panel::before {
  position: absolute;
  top: 0;
  left: 0;
  width: 5px;
  height: 100%;
  content: '';
  background: #409eff;
}

.board-panel .section-header h2 { color: #1f5fae; font-size: 21px; }
.board-panel :deep(.el-textarea__inner) {
  min-height: 150px !important;
  border: 0;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: inset 0 0 0 1px rgba(64, 158, 255, 0.18);
  font-size: 15px;
  line-height: 1.75;
}

.notice-form {
  margin-top: 16px;
}

.form-actions {
  justify-content: flex-end;
}

.notice-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.notice-item {
  padding: 14px;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  background: #fafafa;
}

.notice-title-row h3 {
  font-size: 16px;
}

.notice-content {
  margin-top: 10px;
  color: #303133;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.notice-author {
  margin-top: 8px;
}

.duty-header {
  margin-bottom: 14px;
}

.duty-table {
  width: 100%;
}

.member-select {
  width: 100%;
}

.role-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.purchase-action { display: flex; flex-direction: column; gap: 8px; align-items: stretch; min-width: 170px; }
.purchase-action input[type='file'] { max-width: 280px; }
.el-link + .el-link { margin-left: 10px; }
.compact-header { margin-bottom: 14px; }
.delete-purchase { align-self: flex-end; margin-top: 2px; }
.notice-panel { background: linear-gradient(145deg, #ffffff 72%, #f3f8ff); }
.purchase-form-panel { background: linear-gradient(145deg, #ffffff 75%, #f4fbf7); }

.purchase-cards { display: flex; flex-direction: column; gap: 10px; }
.purchase-card {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(180px, 230px);
  gap: 18px;
  padding: 16px 18px;
  border: 1px solid #e8ebf0;
  border-radius: 10px;
  background: #fbfcfe;
}
.purchase-card-heading { display: flex; align-items: center; gap: 10px; }
.purchase-card-heading h3 { flex: 1; margin: 0; color: #252b36; font-size: 16px; line-height: 1.55; white-space: pre-wrap; }
.purchase-id { color: #7b8798; font-weight: 700; font-variant-numeric: tabular-nums; }
.purchase-note { margin-top: 5px; color: #697386; font-size: 13px; }
.purchase-meta-grid { display: grid; grid-template-columns: repeat(4, minmax(110px, 1fr)); gap: 8px 18px; margin-top: 13px; }
.purchase-meta-grid div { display: flex; flex-direction: column; gap: 2px; }
.purchase-meta-grid span { color: #9098a5; font-size: 12px; }
.purchase-meta-grid strong { color: #3d4654; font-size: 13px; font-weight: 500; }
.purchase-meta-grid .amount { color: #e06c28; font-size: 15px; font-weight: 700; }
.purchase-progress { position: relative; display: grid; grid-template-columns: repeat(4, 1fr); margin-top: 16px; }
.purchase-progress::before,
.purchase-progress::after { position: absolute; top: 6px; left: 6px; right: 6px; height: 2px; content: ''; background: #dfe4eb; }
.purchase-progress::after { right: auto; width: calc((100% - 12px) * var(--progress) / 100); background: #67c23a; }
.progress-step { position: relative; z-index: 1; display: flex; flex-direction: column; gap: 5px; color: #a1a8b2; font-size: 11px; }
.progress-step:not(:first-child) { align-items: center; }
.progress-step:last-child { align-items: flex-end; }
.progress-step i { width: 14px; height: 14px; border: 3px solid #dfe4eb; border-radius: 50%; background: #fff; }
.progress-step.active { color: #4c9145; font-weight: 600; }
.progress-step.active i { border-color: #67c23a; background: #67c23a; box-shadow: inset 0 0 0 2px #fff; }
.purchase-details { display: flex; flex-wrap: wrap; gap: 5px 18px; margin-top: 8px; color: #8a93a1; font-size: 12px; }
.purchase-files { display: flex; flex-wrap: wrap; gap: 14px; margin-top: 9px; }
.purchase-files .el-link { margin-left: 0; }
.purchase-card-action { display: flex; flex-direction: column; justify-content: center; align-items: stretch; gap: 6px; padding-left: 17px; border-left: 1px solid #e7eaf0; }
.action-hint { color: #9098a5; text-align: center; font-size: 13px; }
.file-picker { display: flex; flex-direction: column; gap: 4px; color: #606975; font-size: 12px; }

@media (max-width: 767px) {
  .page-header,
  .section-header,
  .duty-actions,
  .header-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .board-select {
    width: 100%;
  }
}

@media (max-width: 1399px) {
  .affairs-grid {
    grid-template-areas:
      'board board board board board board board board board board board board'
      'purchase-form purchase-form purchase-form purchase-form purchase-form purchase-form notice notice notice notice notice notice'
      'purchase-list purchase-list purchase-list purchase-list purchase-list purchase-list purchase-list purchase-list purchase-list purchase-list purchase-list purchase-list'
      'duty duty duty duty duty duty members members members members members members';
  }
  .purchase-meta-grid { grid-template-columns: repeat(2, minmax(110px, 1fr)); }
}

@media (max-width: 767px) {
  .affairs-grid {
    grid-template-columns: minmax(0, 1fr);
    grid-template-areas: 'board' 'purchase-form' 'notice' 'purchase-list' 'duty' 'members';
  }
  .panel { padding: 16px; border-radius: 10px; }
  .purchase-card { grid-template-columns: minmax(0, 1fr); }
  .purchase-card-action { padding: 12px 0 0; border-top: 1px solid #e7eaf0; border-left: 0; }
  .purchase-meta-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .purchase-card-heading { align-items: flex-start; flex-wrap: wrap; }
}
</style>

import { ElMessage, ElMessageBox } from 'element-plus'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'


function hasMeaningfulDraft(rawDraft) {
  if (!rawDraft) return false
  try {
    const draft = JSON.parse(rawDraft)
    const items = Array.isArray(draft?.form?.items) ? draft.form.items : []
    return Boolean(
      draft?.step1 ||
      draft?.step2 ||
      draft?.step3 ||
      items.some(item => String(item?.content || '').trim()),
    )
  } catch {
    return false
  }
}

function buildProcurementDraft(preview) {
  const purchaseTypes = [...new Set(preview.items.map(item => item.purchase_type))]
  if (purchaseTypes.length !== 1 || !purchaseTypes[0]) return null
  return {
    step1: preview.expense_type,
    step2: preview.platform,
    step3: purchaseTypes[0],
    form: {
      items: preview.items.map(item => ({
        content: item.content || '',
        cas_number: item.cas_number || '',
        product_number: item.product_number || '',
        manufacturer: item.manufacturer || '',
        parameters: item.parameters || '',
        specifications: item.specifications || '',
        unit_price: Number(item.unit_price || 0),
        quantity: Number(item.quantity || 1),
        purchase_type: item.purchase_type || '',
        purchase_link: item.purchase_link || '',
      })),
    },
    ts: Date.now(),
    v: 4,
  }
}

export function buildLabOpsHistoryContent(message) {
  const summaries = (message.actions || []).map((action) => {
    const preview = action.preview || {}
    if (action.type === 'equipment_reservation_prefill') {
      const channel = preview.position_no ? `，通道${preview.position_no}` : ''
      return `已准备预约：${preview.equipment_name}${channel}，${preview.target_date} ${preview.start_time}-${preview.end_time}`
    }
    if (action.type === 'procurement_form_prefill') {
      const names = (preview.items || []).map(item => item.content).join('、')
      return `已准备采购：${names}，${preview.expense_type_label}，平台${preview.platform}`
    }
    return ''
  }).filter(Boolean)
  return summaries.length ? `${message.content}\n[${summaries.join('；')}]` : message.content
}

export function useLabOpsActionNavigation(onNavigated = null) {
  const router = useRouter()
  const authStore = useAuthStore()

  async function finishNavigation(message) {
    if (typeof onNavigated === 'function') onNavigated()
    ElMessage.success(message)
  }

  async function openEquipmentReservation(action) {
    const preview = action?.preview || {}
    if (!preview.equipment_id || !preview.target_date || !preview.start_time || !preview.end_time) {
      ElMessage.error('预约预填信息不完整，请重新描述需求。')
      return
    }
    const query = {
      assistant_prefill: '1',
      equipment_id: preview.equipment_id,
      date: preview.target_date,
      start_time: preview.start_time,
      end_time: preview.end_time,
    }
    if (preview.position_no) query.position_no = preview.position_no
    await router.push({ name: 'instruments-book', query })
    await finishNavigation('预约信息已预填，请核对后手动提交')
  }

  async function openProcurementRequest(action) {
    const preview = action?.preview || {}
    if (!preview.expense_type || !preview.platform || !Array.isArray(preview.items)) {
      ElMessage.error('采购预填信息不完整，请重新描述需求。')
      return
    }
    const draft = buildProcurementDraft(preview)
    if (!draft) {
      ElMessage.error('采购类型不一致，请拆分成多份申请。')
      return
    }
    const draftKey = `procurement_draft:v4:${authStore.user?.id || 'guest'}`
    if (hasMeaningfulDraft(localStorage.getItem(draftKey))) {
      try {
        await ElMessageBox.confirm(
          '采购页面已有未提交草稿。继续将用助手生成的内容替换该草稿。',
          '替换现有采购草稿？',
          { type: 'warning', confirmButtonText: '替换并打开', cancelButtonText: '取消' },
        )
      } catch {
        return
      }
    }
    localStorage.setItem(draftKey, JSON.stringify(draft))
    await router.push({
      name: 'procurement-request',
      query: { assistant_prefill: String(draft.ts) },
    })
    await finishNavigation('采购信息已预填，请核对后手动提交')
  }

  return { openEquipmentReservation, openProcurementRequest }
}

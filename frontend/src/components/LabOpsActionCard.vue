<template>
  <section class="action-card">
    <header>
      <span class="action-icon"><el-icon><DocumentChecked /></el-icon></span>
      <div>
        <strong>{{ action.title || '采购申请草稿' }}</strong>
        <small>请核对后再提交</small>
      </div>
      <el-tag type="warning" size="small" effect="light">待提交</el-tag>
    </header>

    <div v-if="preview" class="summary-grid">
      <span>经费类型</span><strong>{{ preview.expense_type_label }}</strong>
      <span>采购平台</span><strong>{{ preview.platform }}</strong>
      <span>预计总价</span><strong class="price">¥ {{ preview.total_price }}</strong>
    </div>

    <div v-if="preview?.items?.length" class="items">
      <article v-for="(item, index) in preview.items" :key="`${action.id}-${index}`">
        <div class="item-title">
          <strong>{{ item.content }}</strong>
          <span>× {{ item.quantity }}</span>
        </div>
        <div class="item-price">¥ {{ item.unit_price }} / 件</div>
        <dl>
          <template v-if="item.specifications">
            <dt>规格</dt><dd>{{ item.specifications }}</dd>
          </template>
          <template v-if="item.manufacturer">
            <dt>厂商</dt><dd>{{ item.manufacturer }}</dd>
          </template>
          <template v-if="item.purchase_link">
            <dt>链接</dt><dd class="link-text">{{ item.purchase_link }}</dd>
          </template>
        </dl>
      </article>
    </div>

    <div v-if="action.sources?.length" class="sources">
      规则依据：{{ action.sources.map(item => item.title).join('、') }}（当前白名单）
    </div>

    <footer>
      <span>只预填原页面，不会自动提交申请</span>
      <el-button
        type="primary"
        size="small"
        @click="$emit('open')"
      >
        {{ action.confirm_label || '打开采购页面并预填' }}
      </el-button>
    </footer>
  </section>
</template>

<script setup>
import { computed } from 'vue'
import { DocumentChecked } from '@element-plus/icons-vue'

const props = defineProps({
  action: { type: Object, required: true },
})

defineEmits(['open'])

const preview = computed(() => props.action.preview || null)
</script>

<style scoped>
.action-card { margin-top: 10px; overflow: hidden; border: 1px solid #f3d19e; border-radius: 12px; background: #fff; box-shadow: 0 4px 14px rgba(180, 125, 35, .08); }
header { display: flex; align-items: center; gap: 9px; padding: 11px 12px; border-bottom: 1px solid #faecd8; background: #fdf6ec; }
header > div { flex: 1; min-width: 0; }
header strong, header small { display: block; }
header strong { color: #303133; font-size: 13px; }
header small { margin-top: 2px; color: #909399; font-size: 10px; }
.action-icon { display: grid; place-items: center; width: 30px; height: 30px; border-radius: 9px; color: #b88230; background: #faecd8; }
.summary-grid { display: grid; grid-template-columns: 66px minmax(0, 1fr); gap: 7px 10px; padding: 11px 12px; border-bottom: 1px solid #ebeef5; font-size: 12px; }
.summary-grid span { color: #909399; }
.summary-grid strong { overflow-wrap: anywhere; color: #303133; }
.summary-grid .price { color: #f56c6c; }
.items { padding: 0 12px; }
.items article { padding: 10px 0; }
.items article + article { border-top: 1px dashed #dcdfe6; }
.item-title { display: flex; align-items: center; justify-content: space-between; gap: 8px; color: #303133; font-size: 12px; }
.item-price { margin-top: 3px; color: #f56c6c; font-size: 11px; }
dl { display: grid; grid-template-columns: 34px minmax(0, 1fr); gap: 3px 6px; margin: 6px 0 0; font-size: 10px; }
dt { color: #a8abb2; }
dd { min-width: 0; margin: 0; color: #606266; overflow-wrap: anywhere; }
.link-text { max-height: 30px; overflow: hidden; }
.sources { padding: 8px 12px; border-top: 1px solid #ebeef5; color: #909399; background: #fafafa; font-size: 10px; line-height: 1.5; }
footer { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 10px 12px; border-top: 1px solid #ebeef5; }
footer span { color: #909399; font-size: 10px; line-height: 1.4; }
footer a { color: #409eff; font-size: 12px; text-decoration: none; }
</style>

<template>
  <div class="screen-manage">
    <div class="topbar">
      <div class="title">
        <div class="h1">走廊显示屏管理</div>
        <div class="sub">仅系统管理员 / 走廊显示屏管理人员可见</div>
      </div>

      <div class="actions">
        <el-button @click="openPreview" plain>
          <el-icon><View /></el-icon>
          打开预览页
        </el-button>
        <el-button @click="loadAll" :loading="loading" plain>
          <el-icon><Refresh /></el-icon>
          刷新数据
        </el-button>
        <el-button type="primary" @click="saveConfig" :loading="saving">
          <el-icon><Check /></el-icon>
          保存显示配置
        </el-button>
      </div>
    </div>

    <div class="grid">
      <section class="left">
        <div class="card">
          <div class="card-title">上传展示图片</div>

          <el-upload
            drag
            multiple
            :show-file-list="false"
            accept="image/*"
            :http-request="uploadImage"
            :disabled="loading || uploading"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              拖拽图片到这里，或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="tip">支持多张上传，预览页将自动适配尺寸与数量</div>
            </template>
          </el-upload>

          <div class="split"></div>

          <div class="card-title-row">
            <div class="card-title">已上传图片（{{ images.length }}）</div>
            <el-tag size="small" type="info" effect="plain">按顺序轮播</el-tag>
          </div>

          <div v-if="images.length === 0" class="empty">
            <el-empty description="暂无图片" />
          </div>

          <div v-else class="img-list">
            <div v-for="(img, idx) in images" :key="img.id" class="img-item">
              <div class="thumb">
                <img :src="resolveUrl(img.url)" :alt="img.name || 'image'" />
              </div>

              <div class="meta">
                <div class="line1">
                  <span class="idx">#{{ idx + 1 }}</span>
                  <span class="name">{{ img.name || '未命名图片' }}</span>
                </div>
                <div class="line2">
                  <el-tag size="small" effect="plain">{{ img.width || '-' }}×{{ img.height || '-' }}</el-tag>
                  <el-tag size="small" type="success" effect="plain" v-if="img.created_at">{{ img.created_at }}</el-tag>
                </div>
              </div>

              <div class="ops">
                <el-button
                  size="small"
                  plain
                  :disabled="idx === 0 || sorting"
                  @click="moveUp(idx)"
                >
                  <el-icon><ArrowUp /></el-icon>
                </el-button>
                <el-button
                  size="small"
                  plain
                  :disabled="idx === images.length - 1 || sorting"
                  @click="moveDown(idx)"
                >
                  <el-icon><ArrowDown /></el-icon>
                </el-button>
                <el-popconfirm
                  title="确定删除这张图片吗？"
                  confirm-button-text="删除"
                  cancel-button-text="取消"
                  @confirm="deleteImage(img.id)"
                >
                  <template #reference>
                    <el-button size="small" type="danger" plain :loading="deletingId === img.id">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </template>
                </el-popconfirm>
              </div>
            </div>
          </div>

          <div class="split"></div>

          <div class="note">
            <div class="note-title">小提示</div>
            <ul>
              <li>“上移/下移”会修改轮播顺序</li>
              <li>预览页每 10 秒会自动拉取最新数据（我们已在预览页里写好）</li>
            </ul>
          </div>
        </div>
      </section>

      <section class="right">
        <div class="card config-card">
          <div class="card-title">显示配置</div>

          <el-form label-width="110px" class="form">
            <el-form-item label="轮播间隔">
              <el-input-number
                v-model="form.carousel_interval_ms"
                :min="1000"
                :step="500"
                controls-position="right"
              />
              <span class="unit">ms</span>
            </el-form-item>

            <el-form-item label="当前状态">
              <el-input v-model="form.state" placeholder="例如：运行正常 / 设备维护中 / 会议进行中" />
            </el-form-item>

            <el-form-item label="今日提示">
              <el-input v-model="form.tip" placeholder="例如：离开前确认电源/气源关闭" />
            </el-form-item>

            <el-form-item label="安全检查">
              <el-input v-model="form.safety" placeholder="例如：废液分类；通风橱复位" />
            </el-form-item>

            <el-form-item label="补充说明">
              <el-input
                v-model="notesText"
                type="textarea"
                :rows="5"
                placeholder="一行一条，例如：&#10;重要物品用完及时登记/补充&#10;发现安全隐患请立即上报"
              />
            </el-form-item>

            <el-divider content-position="left">值日安排（预览页中部）</el-divider>

            <el-form-item label="值日安排">
              <el-input
                v-model="form.duty_text"
                type="textarea"
                :rows="10"
                placeholder="请输入值日安排，可换行填写日期、取快递人员、卫生组等内容"
              />
              <div class="tip">保存后，展示屏按原文显示此处内容，不再自动轮值。</div>
            </el-form-item>
          </el-form>

          <div class="config-actions">
            <el-button @click="resetConfig" plain>重置为服务器数据</el-button>
            <el-button type="primary" @click="saveConfig" :loading="saving">保存</el-button>
          </div>

        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import apiClient from '@/api'
import { ElMessage } from 'element-plus'
import {
  UploadFilled, Refresh, Check, Delete, ArrowUp, ArrowDown, View
} from '@element-plus/icons-vue'

// ====== 预览地址（与你的路由一致）======
const previewUrl = '/display-preview'

// ====== 核心工具：处理图片路径 ======
// 自动判断：如果 url 是相对路径（如 /media/...），则拼接当前页面主机名 + 8000端口
// 这样无论是 localhost 还是 192.168.x.x 都能正常访问图片
const resolveUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('http')) return url
  // 假设后端始终在当前 IP 的 8000 端口
  return `http://${window.location.hostname}:8000${url}`
}

// ====== 列表数据 ======
const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const sorting = ref(false)
const deletingId = ref(null)

const images = ref([]) // {id,url,name,width,height,created_at}

// ====== 实验室情况表单 ======
const form = ref({
  carousel_interval_ms: 5000,
  state: '运行正常',
  tip: '请保持实验台整洁，离开前确认电源/气源关闭。',
  safety: '通风橱使用后请复位；废液按规定分类。',
  notes: ['重要物品用完及时登记/补充', '发现安全隐患请立即上报', '公共区域保持通道畅通'],
  duty_text: '',
})

const notesText = computed({
  get() {
    return (form.value.notes || []).join('\n')
  },
  set(v) {
    form.value.notes = (v || '')
      .split('\n')
      .map(s => s.trim())
      .filter(Boolean)
  }
})

// ====== API Endpoints ======
const API_ADMIN_IMAGES = '/corridor_display/admin/images/'
const API_ADMIN_ORDER = '/corridor_display/admin/images/reorder/'
const API_ADMIN_CONFIG = '/corridor_display/admin/config/'

// 读取 + 初始化
async function loadAll() {
  loading.value = true
  try {
    await Promise.all([loadImages(), loadConfig()])
  } finally {
    loading.value = false
  }
}

async function loadImages() {
  try {
    const resp = await apiClient.get(API_ADMIN_IMAGES)
    images.value = Array.isArray(resp.data) ? resp.data : (resp.data?.results || [])
  } catch (e) {
    images.value = []
    console.error('加载走廊显示图片失败', e)
  }
}

async function loadConfig() {
  try {
    const resp = await apiClient.get(API_ADMIN_CONFIG)
    if (resp?.data) {
      form.value = {
        ...form.value,
        ...resp.data
      }
      if (!Array.isArray(form.value.notes)) form.value.notes = []
      if (typeof form.value.duty_text !== 'string') form.value.duty_text = ''
    }
  } catch (e) {
    console.error('加载走廊显示配置失败', e)
  }
}

// 上传
async function uploadImage(req) {
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('image', req.file)
    fd.append('name', req.file?.name || '')

    await apiClient.post(API_ADMIN_IMAGES, fd, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    ElMessage.success('上传成功')
    await loadImages()
  } catch (e) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

// 删除
async function deleteImage(id) {
  deletingId.value = id
  try {
    await apiClient.delete(`${API_ADMIN_IMAGES}${id}/`)
    ElMessage.success('已删除')
    await loadImages()
  } catch (e) {
    ElMessage.error('删除失败')
  } finally {
    deletingId.value = null
  }
}

// 排序
async function submitOrder() {
  sorting.value = true
  try {
    const orderedIds = images.value.map(x => x.id)
    await apiClient.post(API_ADMIN_ORDER, { ordered_ids: orderedIds })
  } catch (e) {
    ElMessage.error('排序保存失败')
  } finally {
    sorting.value = false
  }
}

async function moveUp(idx) {
  if (idx <= 0) return
  const arr = images.value.slice()
  ;[arr[idx - 1], arr[idx]] = [arr[idx], arr[idx - 1]]
  images.value = arr
  await submitOrder()
}

async function moveDown(idx) {
  if (idx >= images.value.length - 1) return
  const arr = images.value.slice()
  ;[arr[idx + 1], arr[idx]] = [arr[idx], arr[idx + 1]]
  images.value = arr
  await submitOrder()
}

// 保存 config
async function saveConfig() {
  saving.value = true
  try {
    const { carousel_interval_ms, state, tip, safety, notes, duty_text } = form.value
    const payload = { carousel_interval_ms, state, tip, safety, notes, duty_text }
    if (!Array.isArray(payload.notes)) payload.notes = []
    await apiClient.put(API_ADMIN_CONFIG, payload)
    ElMessage.success('保存成功')
  } catch (e) {
    console.error('保存走廊显示配置失败', e)
    const data = e?.response?.data
    let errMsg = '保存失败'
    if (typeof data === 'string' && data.trim()) {
      errMsg = data
    } else if (data?.detail) {
      errMsg = data.detail
    } else if (data && typeof data === 'object') {
      const firstKey = Object.keys(data)[0]
      if (firstKey) {
        const firstVal = Array.isArray(data[firstKey]) ? data[firstKey][0] : data[firstKey]
        errMsg = `${firstKey}: ${firstVal}`
      }
    }
    ElMessage.error(errMsg)
  } finally {
    saving.value = false
  }
}

function resetConfig() {
  loadConfig()
}

function openPreview() {
  window.open(previewUrl, '_blank')
}

onMounted(() => {
  hydrateDutyRowsFromForm()
  loadAll()
})
</script>

<style scoped>
.screen-manage {
  padding: 16px;
  min-height: calc(100vh - 32px);
}

.topbar {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.title .h1 {
  font-size: 20px;
  font-weight: 800;
  line-height: 1.2;
}
.title .sub {
  margin-top: 4px;
  font-size: 12px;
  color: #666;
}

.grid {
  display: grid;
  grid-template-columns: 0.92fr 1.08fr;
  gap: 14px;
}

.card {
  background: #fff;
  border: 1px solid #eee;
  border-radius: 14px;
  padding: 14px;
  box-shadow: 0 10px 24px rgba(0,0,0,0.04);
}

.card-title {
  font-size: 14px;
  font-weight: 800;
  color: #303133;
  margin-bottom: 10px;
}

.card-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.tip {
  margin-top: 8px;
  font-size: 12px;
  color: #666;
}

.split {
  height: 1px;
  background: #f0f0f0;
  margin: 14px 0;
}

.empty {
  padding: 6px 0 12px;
}

.img-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.img-item {
  display: grid;
  grid-template-columns: 84px 1fr auto;
  gap: 10px;
  padding: 10px;
  border: 1px solid #f1f1f1;
  border-radius: 12px;
  background: #fafafa;
}

.thumb {
  width: 84px;
  height: 64px;
  border-radius: 10px;
  overflow: hidden;
  background: #111;
  display: flex;
  align-items: center;
  justify-content: center;
}
.thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.meta {
  min-width: 0;
}
.line1 {
  display: flex;
  gap: 8px;
  align-items: baseline;
}
.idx {
  font-size: 12px;
  color: #909399;
}
.name {
  font-size: 13px;
  font-weight: 700;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.line2 {
  margin-top: 6px;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.ops {
  display: flex;
  gap: 6px;
  align-items: center;
}

.note {
  font-size: 12px;
  color: #666;
}
.note-title {
  font-weight: 800;
  color: #303133;
  margin-bottom: 6px;
}
.note ul {
  margin: 0;
  padding-left: 18px;
  line-height: 1.7;
}

.config-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 8px;
}

.form .unit {
  margin-left: 10px;
  color: #666;
  font-size: 12px;
}

@media (max-width: 1100px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>

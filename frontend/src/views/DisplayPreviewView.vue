<template>
  <div class="preview-root">
    <div class="preview-grid">
      <section class="left-panel">
        <div class="panel-header">
          <span class="title-cn">走廊展示</span>
          <span class="title-en">GALLERY</span>
        </div>

        <div class="carousel-wrap">
          <div v-if="images.length > 0" style="position:absolute; top:0; left:0; z-index:100; opacity:0.01;">
            <img :src="resolveUrl(images[0].url)" style="width:1px; height:1px;" />
          </div>

          <el-carousel
            v-if="images.length > 0"
            class="custom-carousel"
            height="100%"
            indicator-position="none"
            :interval="carouselInterval"
            arrow="hover"
          >
            <el-carousel-item v-for="img in images" :key="img.id || img.url">
              <div class="img-frame">
                <img class="carousel-img" :src="resolveUrl(img.url)" :alt="img.name || 'display image'" />
              </div>
            </el-carousel-item>
          </el-carousel>

          <div v-else class="empty-wrap">
            <el-empty description="暂无图片" :image-size="100" />
          </div>
        </div>

        <div class="weather-bar" v-if="weather.temp !== null">
          <div class="weather-content">
            <div class="w-main">
              <span class="w-temp">{{ weather.temp }}°</span>
              <div class="w-info">
                <span class="w-cond">{{ weather.condition }}</span>
                <span class="w-range">{{ weather.min }}° ~ {{ weather.max }}°</span>
              </div>
            </div>
            <div class="w-divider"></div>
            <div class="w-loc">
              <div class="loc-txt">
                <el-icon><LocationInformation /></el-icon> 上海·杨浦
              </div>
              <div class="hum-txt" v-if="weather.humidity">
                湿度 {{ weather.humidity }}%
              </div>
            </div>
          </div>
        </div>
        
        <div class="weather-loading" v-else>
          <span>更新天气数据...</span>
        </div>
      </section>

      <section class="right-panel">
        <div class="duty-card">
          <header class="card-header">
            <div class="header-main">
              <h1>实验室值日安排</h1>
              <span class="sub-title">Laboratory Duty Roster</span>
            </div>
            <div class="live-clock">
              <div class="clock-time">{{ liveTime }}</div>
              <div class="clock-date">{{ liveDate }}</div>
            </div>
          </header>

          <div class="duty-body">
            <div class="roster-col">
              <div class="manual-duty-text">{{ dutyText || '暂无值日安排' }}</div>
            </div>

            <div class="content-col">
              <div class="content-box">
                <h3><el-icon><List /></el-icon> 值日内容标准</h3>
                <ul>
                  <li><strong>倒垃圾</strong>：包含走廊4个、大实验室3个、108室1个、炉子间1个、称量间1个、办公室1个。</li>
                  <li><strong>垃圾处理</strong>：实验室垃圾装箱后联系示例成员23回收；生活垃圾自行带走。</li>
                  <li><strong>清洁</strong>：清理通风橱、试验台；清理未贴标签试剂瓶。</li>
                  <li><strong>耗材补充</strong>：去离子水、酒精、枪头、纸巾、手套等。</li>
                  <li><strong>大扫除</strong>：每周对办公室、走廊、实验室地面进行扫拖。</li>
                  <li><strong>设备维护</strong>：每周更换超声机水 1-2 次。</li>
                  <li class="warning">离岗前务必检查水、电、气安全！</li>
                </ul>
              </div>
            </div>
          </div>
          
          <footer class="card-footer">
            注：快递值日生负责取实验室公共用品，个人药品请自行负责。
          </footer>
        </div>

        <div class="status-card">
          <div class="status-header">
            <span class="st-title">实验室运行看板</span>
            <div class="st-tag" :class="statusClass">
              <div class="dot"></div> {{ labState }}
            </div>
          </div>

          <div class="status-body">
            <div class="s-box tip-box">
              <div class="s-icon"><el-icon><Bell /></el-icon></div>
              <div class="s-text">
                <div class="s-label">今日提示</div>
                <div class="s-val">{{ statusTip }}</div>
              </div>
            </div>
            
            <div class="s-box safe-box">
              <div class="s-icon"><el-icon><Warning /></el-icon></div>
              <div class="s-text">
                <div class="s-label">安全检查</div>
                <div class="s-val">{{ safetyTip }}</div>
              </div>
            </div>
          </div>

          <div class="status-footer-bar">
             <div class="note-row">
               <span class="n-label">补充说明：</span>
               <div class="n-content">
                 <span v-if="statusNotes.length === 0">无</span>
                 <span v-else v-for="(note, idx) in statusNotes" :key="idx" class="n-item">
                   {{ idx + 1 }}. {{ note }}
                 </span>
               </div>
             </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref, computed } from 'vue'
import apiClient from '@/api'
import { 
  LocationInformation, List, Bell, Warning 
} from '@element-plus/icons-vue'

// ----------------------
// 工具
// ----------------------
const resolveUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return `http://${window.location.hostname}:8000${url}`
}

// ----------------------
// 左侧逻辑
// ----------------------
const images = ref([])
const carouselInterval = ref(5000)
let pollTimer = null

const dutyText = ref('')

async function fetchPublicDisplay() {
  try {
    const resp = await apiClient.get('/corridor_display/public/')
    const data = resp.data || {}
    images.value = Array.isArray(data.images) ? data.images : []
    
    if (typeof data.carousel_interval_ms === 'number' && data.carousel_interval_ms > 500) {
      carouselInterval.value = data.carousel_interval_ms
    }

    dutyText.value = typeof data.duty?.text === 'string' ? data.duty.text : ''

    if (data.status) {
      if (data.status.tip) statusTip.value = data.status.tip
      if (data.status.safety) safetyTip.value = data.status.safety
      if (data.status.state) labState.value = data.status.state
      if (Array.isArray(data.status.notes)) statusNotes.value = data.status.notes
    }
  } catch (e) {}
}

// 天气 (上海杨浦: 31.3, 121.53)
const weather = ref({ temp: null, condition: '', min: null, max: null, humidity: null })
let weatherTimer = null
const weatherCodeMap = {
  0: '晴', 1: '多云', 2: '阴', 3: '阴', 45: '雾', 48: '雾凇',
  51: '小雨', 53: '中雨', 55: '大雨', 61: '小雨', 63: '中雨', 65: '大雨',
  71: '小雪', 73: '中雪', 95: '雷雨', 96: '雷雨冰雹'
}

async function fetchWeather() {
  try {
    // 坐标精准定位到上海杨浦
    const res = await fetch('https://api.open-meteo.com/v1/forecast?latitude=31.299&longitude=121.53&current=temperature_2m,weather_code,relative_humidity_2m&daily=temperature_2m_max,temperature_2m_min&timezone=Asia%2FShanghai')
    const data = await res.json()
    if (data.current && data.daily) {
      weather.value = {
        temp: Math.round(data.current.temperature_2m),
        condition: weatherCodeMap[data.current.weather_code] || '多云',
        humidity: data.current.relative_humidity_2m,
        max: Math.round(data.daily.temperature_2m_max[0]),
        min: Math.round(data.daily.temperature_2m_min[0])
      }
    }
  } catch (e) {
    console.error('天气获取失败', e)
  }
}

// ----------------------
// 右侧逻辑
// ----------------------
const liveDate = ref('')
const liveTime = ref('')
let clockTimer = null

function updateTime() {
  const now = new Date()
  const weekDays = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"]
  liveDate.value = `${now.getFullYear()}年${now.getMonth()+1}月${now.getDate()}日 ${weekDays[now.getDay()]}`
  liveTime.value = now.toTimeString().slice(0, 8)
}

// 状态
const statusTip = ref('暂无提示')
const safetyTip = ref('暂无')
const labState = ref('运行正常')
const statusNotes = ref([])
const statusClass = computed(() => {
  if (labState.value.includes('维护')) return 'tag-warn'
  if (labState.value.includes('会议')) return 'tag-info'
  return 'tag-success'
})

onMounted(() => {
  updateTime()
  clockTimer = setInterval(updateTime, 1000)
  
  fetchPublicDisplay()
  pollTimer = setInterval(fetchPublicDisplay, 10_000)

  fetchWeather()
  weatherTimer = setInterval(fetchWeather, 3600 * 1000)
})

onBeforeUnmount(() => {
  if (clockTimer) clearInterval(clockTimer)
  if (pollTimer) clearInterval(pollTimer)
  if (weatherTimer) clearInterval(weatherTimer)
})
</script>

<style scoped>
/* ========== 全局 ========== */
.preview-root {
  height: 100vh;
  width: 100%;
  background: #0f172a; /* 深色背景更护眼 */
  color: #f1f5f9;
  box-sizing: border-box;
  overflow: hidden;
}

.preview-grid {
  height: 100%;
  width: 100%;
  /* 关键修改：左 32%，右 68% */
  display: grid;
  grid-template-columns: 32% 68%;
  gap: 24px;
  /* 关键修改：底部留白 40px */
  padding: 24px 24px 40px 24px;
  box-sizing: border-box;
}

/* ========== 左侧：展示区 ========== */
.left-panel {
  display: flex;
  flex-direction: column;
  background: #1e293b;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(0,0,0,0.3);
  position: relative;
}

.panel-header {
  padding: 14px 20px;
  background: rgba(0,0,0,0.2);
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.title-cn { font-size: 18px; font-weight: 700; letter-spacing: 1px; }
.title-en { font-size: 12px; font-weight: 600; opacity: 0.4; letter-spacing: 2px; }

.carousel-wrap {
  flex: 1;
  min-height: 0;
  position: relative;
  background: #000;
  display: flex;
  flex-direction: column;
}

.custom-carousel { width: 100%; height: 100% !important; }
:deep(.el-carousel__container) { height: 100% !important; }

.img-frame {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
}
.carousel-img { width: 100%; height: 100%; object-fit: contain; }

.empty-wrap {
  flex: 1; display: flex; align-items: center; justify-content: center;
}

/* --- 天气模块 (底部居中悬浮) --- */
.weather-bar {
  padding: 16px;
  background: #1e293b;
  border-top: 1px solid rgba(255,255,255,0.05);
  display: flex;
  justify-content: center;
}
.weather-content {
  display: flex;
  align-items: center;
  gap: 16px;
}
.w-main { display: flex; align-items: center; gap: 8px; }
.w-temp { font-size: 36px; font-weight: 700; color: #fff; line-height: 1; }
.w-info { display: flex; flex-direction: column; justify-content: center; }
.w-cond { font-size: 14px; font-weight: 600; color: #fbbf24; }
.w-range { font-size: 12px; color: rgba(255,255,255,0.6); }

.w-divider { width: 1px; height: 28px; background: rgba(255,255,255,0.1); }

.w-loc { display: flex; flex-direction: column; justify-content: center; gap: 2px; }
.loc-txt { font-size: 13px; color: rgba(255,255,255,0.9); display: flex; align-items: center; gap: 4px; }
.hum-txt { font-size: 12px; color: rgba(255,255,255,0.5); }

.weather-loading { padding: 15px; text-align: center; font-size: 12px; opacity: 0.5; }

/* ========== 右侧：信息区 ========== */
.right-panel {
  display: grid;
  /* 关键修改：上 65%，下 35%，给下方更多空间 */
  grid-template-rows: 65% 35%;
  gap: 20px;
  min-height: 0;
}

/* 卡片通用样式 */
.duty-card, .status-card {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 1. 值日表 */
.duty-card { }

.card-header {
  padding: 16px 24px;
  background: linear-gradient(to right, #f8fafc, #fff);
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.header-main h1 { margin: 0; font-size: 28px; color: #0f172a; }
.sub-title { font-size: 16px; color: #94a3b8; letter-spacing: 1px; text-transform: uppercase; }

.live-clock { text-align: right; }
.clock-time { font-size: 32px; font-weight: 700; color: #2563eb; line-height: 1; font-family: monospace; }
.clock-date { font-size: 17px; color: #64748b; margin-top: 4px; }

.duty-body {
  flex: 1;
  display: flex;
  overflow: hidden;
}
.roster-col {
  width: 40%;
  padding: 20px;
  background: #f8fafc;
  border-right: 1px solid #f1f5f9;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
}
.content-col {
  width: 60%;
  padding: 24px;
  overflow-y: auto;
}

.manual-duty-text {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
  font-size: 22px;
  line-height: 1.8;
  color: #1e293b;
}

.content-box h3 { margin: 0 0 12px 0; font-size: 20px; color: #334155; display: flex; align-items: center; gap: 6px; }
.content-box ul { margin: 0; padding-left: 20px; color: #475569; font-size: 18px; line-height: 1.8; }
.warning { color: #dc2626; font-weight: 600; margin-top: 6px; }

.card-footer {
  padding: 10px 24px;
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  text-align: center;
  font-size: 16px;
  color: #94a3b8;
}

/* 2. 实验室运行看板 (暗色主题) */
.status-card {
  background: #1e293b; /* 暗色底更显专业 */
  color: #fff;
  border: 1px solid #334155;
}
.status-header {
  padding: 14px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.st-title { font-size: 16px; font-weight: 700; }
.st-tag {
  display: flex; align-items: center; gap: 6px;
  padding: 4px 12px; border-radius: 20px; font-size: 13px; font-weight: 600;
}
.tag-success { background: rgba(34,197,94,0.2); color: #4ade80; border: 1px solid rgba(34,197,94,0.4); }
.tag-warn { background: rgba(234,179,8,0.2); color: #facc15; border: 1px solid rgba(234,179,8,0.4); }
.tag-info { background: rgba(148,163,184,0.2); color: #cbd5e1; border: 1px solid rgba(148,163,184,0.4); }
.dot { width: 6px; height: 6px; border-radius: 50%; background: currentColor; }

.status-body {
  flex: 1;
  padding: 20px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  overflow-y: auto;
}
.s-box {
  background: rgba(255,255,255,0.05);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  gap: 16px;
  align-items: flex-start;
}
.s-icon {
  width: 40px; height: 40px; border-radius: 8px;
  background: rgba(255,255,255,0.1);
  display: flex; align-items: center; justify-content: center;
  font-size: 20px;
}
.s-text { flex: 1; }
.s-label { font-size: 12px; color: rgba(255,255,255,0.5); margin-bottom: 4px; }
.s-val { font-size: 15px; font-weight: 500; line-height: 1.5; color: #fff; }

.status-footer-bar {
  padding: 12px 20px;
  background: rgba(0,0,0,0.2);
  border-top: 1px solid rgba(255,255,255,0.05);
}
.note-row { display: flex; font-size: 13px; align-items: flex-start; }
.n-label { color: rgba(255,255,255,0.4); white-space: nowrap; margin-right: 8px; }
.n-content { color: rgba(255,255,255,0.8); display: flex; flex-wrap: wrap; gap: 12px; }

@media (max-width: 1280px) {
  .preview-grid { grid-template-columns: 1fr; grid-template-rows: auto auto; overflow-y: auto; }
  .right-panel { grid-template-rows: auto auto; }
}
</style>

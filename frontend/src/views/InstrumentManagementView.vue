<template>
  <el-card class="page">
    <template #header>
      <div class="header">
        <h2>仪器管理</h2>
        <div class="header-actions">
          <el-button @click="openEdit(null, 'standard')">新建普通仪器</el-button>
          <el-button type="primary" @click="openEdit(null, 'planetary_ball_mill')">
            新建行星球磨机
          </el-button>
          <el-button type="success" @click="openEdit(null, 'electrochemical_workstation')">
            新建输力强电化学工作站
          </el-button>
          <el-button type="primary" plain @click="openEdit(null, 'xrd')">新建 XRD</el-button>
        </div>
      </div>
    </template>

    <el-table :data="equipments" v-loading="loading" size="small">
      <el-table-column prop="name" label="名称" width="220" />
      <el-table-column label="类型" width="140">
        <template #default="{ row }">
          <el-tag :type="equipmentModeTagType(row)">
            {{ equipmentModeLabel(row) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="location" label="位置" width="160" />
      <el-table-column label="预约策略">
        <template #default="{ row }">
          <template v-if="row.booking_mode === 'planetary_ball_mill'">
            4 工位；24 小时开放；整点开始预约；
            每球磨 {{ row.ball_mill_cycle_run_minutes }} 分钟自动停机 {{ row.ball_mill_cycle_pause_minutes }} 分钟；
            转速范围 {{ formatRotationSpeedRange(row) }}；
            真实时长上限 {{ formatHours(row.ball_mill_max_actual_minutes) }}；
            每月累计上限 {{ formatOptionalHours(row.ball_mill_monthly_max_actual_minutes) }}；
            排队机制 {{ row.ball_mill_queue_enabled ? '已启用' : '未启用' }}；
            每周三 00:00 放榜；
            放榜前可直约本周，放榜后可直约本周与下一周；
            排队申请始终为当前直约窗口之后的下一整周；
            球磨时间上限 {{ row.ball_mill_max_milling_minutes }} 分钟；
            可操作窗口自动覆盖到下一批排队周
          </template>
          <template v-else-if="row.booking_mode === 'electrochemical_workstation'">
            固定 8 通道（通道1-8）；粒度 {{ row.time_slot_minutes }} 分钟；最多选择未来 {{ row.advance_days }} 天；
            管理员可临时下线通道
          </template>
          <template v-else-if="row.booking_mode === 'xrd'">
            XRD 模板；粒度 {{ row.time_slot_minutes }} 分钟；
            开放 {{ formatClock(row.open_time) }}-{{ formatClock(row.close_time) }}；
            可提前 {{ row.advance_days }} 天；按占用时段统计时长；
            远程主机 {{ row.xrd_remote_machine_name || '未配置' }}
          </template>
          <template v-else>
            粒度 {{ row.time_slot_minutes }} 分钟；
            开放 {{ formatClock(row.open_time) }}-{{ formatClock(row.close_time) }}；
            可提前 {{ row.advance_days }} 天
          </template>
          <span v-if="['standard', 'xrd'].includes(row.booking_mode) && row.early_bird_advance_days">
            （早鸟可提前 {{ row.early_bird_advance_days }} 天）
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="启用" width="90">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'">
            {{ row.is_active ? '是' : '否' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="380">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button link @click="viewCalendar(row)">当日预约</el-button>
          <el-button
            link
            type="primary"
            :loading="exportingEquipmentId === row.id"
            :disabled="exportingEquipmentId !== null && exportingEquipmentId !== row.id"
            @click="exportUsageRecords(row)"
          >
            导出使用记录
          </el-button>
          <el-button v-if="row.booking_mode === 'xrd'" link type="success" @click="viewXrdStats(row)">导师统计</el-button>
          <el-button
            v-if="row.booking_mode === 'planetary_ball_mill' && row.ball_mill_queue_enabled"
            link
            type="warning"
            @click="runQueueDispatch(row)"
          >
            立即放榜
          </el-button>
          <el-popconfirm title="确认删除？" @confirm="remove(row)">
            <template #reference>
              <el-button link type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="editVisible" :title="editForm.id ? '编辑仪器' : '新建仪器'" width="620px">
      <el-form :model="editForm" label-width="140px">
        <el-form-item label="名称">
          <el-input v-model="editForm.name" />
        </el-form-item>

        <el-form-item label="仪器类型">
          <el-radio-group v-model="editForm.booking_mode">
            <el-radio label="standard">普通仪器</el-radio>
            <el-radio label="planetary_ball_mill">行星球磨机</el-radio>
            <el-radio label="electrochemical_workstation">输力强电化学工作站</el-radio>
            <el-radio label="xrd">XRD</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="位置">
          <el-input v-model="editForm.location" />
        </el-form-item>

        <el-form-item v-if="isTimeGranularityEditMode" label="时间粒度(分钟)">
          <el-input-number v-model="editForm.time_slot_minutes" :min="5" :step="5" />
        </el-form-item>

        <el-form-item v-if="isStandardLikeEditMode" label="开放时间">
          <el-time-select
            v-model="editForm.open_time"
            start="00:00"
            step="00:15"
            end="23:45"
            placeholder="开始"
          />
          <span style="margin: 0 8px">—</span>
          <el-time-select
            v-model="editForm.close_time"
            start="00:15"
            step="00:15"
            end="23:59"
            placeholder="结束"
          />
        </el-form-item>

        <template v-if="editForm.booking_mode === 'planetary_ball_mill'">
          <el-form-item label="预约时间规则">
            <div class="formula-block">
              采用 24 小时整点预约，不再单独配置开放时间和开始时间粒度。
            </div>
          </el-form-item>

          <el-form-item label="固定工位">
            <span>1、2、3、4 号位（固定 4 工位）</span>
          </el-form-item>

          <el-form-item label="时间换算规则">
            <div class="formula-block">
              球磨时间可由用户自由输入；系统按“每累计球磨 12 分钟，自动追加 6 分钟停机时间”换算真实预约时长。
            </div>
          </el-form-item>

          <el-form-item label="转速范围(r/min)">
            <el-input-number
              v-model="editForm.ball_mill_min_rotation_speed_rpm"
              :min="1"
              :step="10"
            />
            <span style="margin: 0 8px">—</span>
            <el-input-number
              v-model="editForm.ball_mill_max_rotation_speed_rpm"
              :min="editForm.ball_mill_min_rotation_speed_rpm || 1"
              :step="10"
            />
            <el-button
              link
              type="primary"
              style="margin-left: 10px"
              @click="editForm.ball_mill_max_rotation_speed_rpm = null"
            >
              设为不限制
            </el-button>
            <div class="hint">
              当前：{{ formatRotationSpeedRange(editForm) }}
            </div>
          </el-form-item>

          <el-form-item label="时长上限">
            <div class="formula-block">
              单次真实预约上限为 {{ formatHours(editForm.ball_mill_max_actual_minutes) }}；
              对应球磨时间上限 {{ calcBallMillMaxMillingMinutes(editForm.ball_mill_max_actual_minutes) }} 分钟。
            </div>
          </el-form-item>

          <el-form-item label="可预约用户">
            <el-select
              v-model="editForm.booking_allowed_users"
              multiple
              filterable
              clearable
              placeholder="为空表示所有登录用户均可预约"
              :loading="earlyBirdLoading"
              style="width: 100%"
            >
              <el-option
                v-for="u in earlyBirdCandidates"
                :key="u.id"
                :label="u.name"
                :value="u.id"
              />
            </el-select>
            <div class="hint">
              不选则所有登录用户都可预约；选中后，仅这些用户可以直约或提交排队申请。
            </div>
          </el-form-item>

          <el-form-item label="单次上限(分钟)">
            <el-input-number
              v-model="editForm.ball_mill_max_actual_minutes"
              :min="18"
              :step="30"
            />
          </el-form-item>

          <el-form-item label="每月上限(分钟)">
            <el-input-number
              v-model="editForm.ball_mill_monthly_max_actual_minutes"
              :min="1"
              :step="60"
            />
            <el-button
              link
              type="primary"
              style="margin-left: 10px"
              @click="editForm.ball_mill_monthly_max_actual_minutes = null"
            >
              设为不限制
            </el-button>
            <div class="hint">
              当前：{{ formatOptionalHours(editForm.ball_mill_monthly_max_actual_minutes) }}
            </div>
          </el-form-item>

          <el-form-item label="启用排队机制">
            <el-switch v-model="editForm.ball_mill_queue_enabled" />
          </el-form-item>

          <el-form-item label="每周放榜规则">
            <div class="formula-block">
              系统固定为每周三 00:00 放榜。
              放榜前只开放本周直接预约；放榜后开放本周和下一周直接预约；
              排队申请窗口始终为当前直约窗口后的下一整周。
            </div>
          </el-form-item>

          <template v-if="editForm.ball_mill_queue_enabled">
            <el-form-item label="排队批次规则">
              <div class="formula-block">
                系统固定每次放榜覆盖下一整周，下一次放榜自动推进到再下一整周。
              </div>
            </el-form-item>

            <el-form-item label="可分配开始时段">
              <el-time-select
                v-model="editForm.ball_mill_queue_day_start_time"
                start="00:00"
                step="01:00"
                end="23:00"
                placeholder="开始"
              />
              <span style="margin: 0 8px">—</span>
              <el-time-select
                v-model="editForm.ball_mill_queue_day_end_time"
                start="01:00"
                step="01:00"
                end="23:59"
                placeholder="结束"
              />
              <div class="hint">
                仅允许在该时段内分配“开始时间”，默认 07:00 - 22:00。
              </div>
            </el-form-item>

            <el-form-item label="重度用户阈值(分钟)">
              <el-input-number
                v-model="editForm.ball_mill_queue_heavy_user_threshold_minutes"
                :min="60"
                :step="60"
              />
              <div class="hint">
                过去 30 天累计使用超过该阈值（默认 4320 分钟，即 72 小时）会排到后层队列。
              </div>
            </el-form-item>
          </template>
        </template>

        <template v-else-if="editForm.booking_mode === 'electrochemical_workstation'">
          <el-form-item label="预约时间规则">
            <div class="formula-block">
              固定 8 个通道（通道1-8）；用户通过通道下拉选择后按时间粒度方块预约。
            </div>
          </el-form-item>
          <el-form-item label="通道管理">
            <div class="formula-block">
              管理员可在预约页面临时下线/上线通道；下线通道会灰显且不可互动。
            </div>
          </el-form-item>
          <el-form-item label="可提前预约天数">
            <span>{{ ELECTROCHEMICAL_MAX_ADVANCE_DAYS }} 天（固定）</span>
          </el-form-item>
        </template>

        <el-form-item v-if="isStandardLikeEditMode" label="可提前预约天数">
          <el-input-number v-model="editForm.advance_days" :min="0" :max="90" />
        </el-form-item>

        <el-form-item v-else-if="editForm.booking_mode === 'planetary_ball_mill'" label="可提前预约天数">
          <span>{{ autoBallMillAdvanceDays }} 天（系统自动覆盖当前直约窗口与下一批排队周）</span>
        </el-form-item>

        <el-form-item v-if="editForm.booking_mode === 'xrd'" label="远程主机">
          <el-select
            v-model="editForm.xrd_remote_machine"
            clearable
            filterable
            placeholder="选择远程主机"
            :loading="remoteMachinesLoading"
            style="width: 100%"
          >
            <el-option
              v-for="machine in remoteMachineOptions"
              :key="machine.id"
              :label="formatRemoteMachineOption(machine)"
              :value="machine.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item v-if="isStandardLikeEditMode" label="早鸟可提前天数">
          <el-input-number
            v-model="editForm.early_bird_advance_days"
            :min="0"
            :max="180"
          />
          <div class="hint">
            若不设置或等于上面的“可提前预约天数”，则早鸟与普通用户一致。
          </div>
        </el-form-item>

        <el-form-item v-if="isStandardLikeEditMode" label="早鸟预约用户">
          <el-select
            v-model="editForm.early_bird_users"
            multiple
            filterable
            placeholder="选择可提前预约的早鸟用户"
            :loading="earlyBirdLoading"
            style="width: 100%"
          >
            <el-option
              v-for="u in earlyBirdCandidates"
              :key="u.id"
              :label="u.name"
              :value="u.id"
            />
          </el-select>
          <div class="hint">
            这些用户可以按照上面的“早鸟可提前天数”进行预约。
          </div>
        </el-form-item>

        <el-form-item label="启用">
          <el-switch v-model="editForm.is_active" />
        </el-form-item>

        <el-form-item label="说明">
          <el-input type="textarea" v-model="editForm.description" rows="3" />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="calendarVisible" :title="calendarTitle" size="60%">
      <el-date-picker v-model="calendarDate" type="date" @change="loadCalendar" />

      <el-table :data="calendarRows" size="small" style="margin-top: 12px">
        <el-table-column prop="user_name" label="预约人" width="140" />
        <el-table-column label="日期" width="180">
          <template #default="{ row }">
            {{ formatBookingDate(row) }}
          </template>
        </el-table-column>
        <el-table-column label="时间" width="220">
          <template #default="{ row }">
            {{ formatBookingTime(row) }}
          </template>
        </el-table-column>
        <el-table-column v-if="calendarEquipmentMode === 'planetary_ball_mill'" label="球磨详情" min-width="260">
          <template #default="{ row }">
            {{ formatBallMillDetails(row) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" />
      </el-table>
    </el-drawer>

    <el-drawer v-model="xrdStatsVisible" :title="xrdStatsTitle" size="60%">
      <el-date-picker
        v-model="xrdStatsMonth"
        type="month"
        value-format="YYYY-MM"
        placeholder="选择月份"
        @change="loadXrdStats"
      />
      <el-table :data="xrdStatsRows" v-loading="xrdStatsLoading" size="small" style="margin-top: 12px">
        <el-table-column type="expand">
          <template #default="{ row }">
            <el-table :data="row.students" size="small">
              <el-table-column prop="student_name" label="学生" />
              <el-table-column prop="booking_count" label="预约次数" width="100" />
              <el-table-column label="累计时长" width="140">
                <template #default="{ row: student }">{{ formatMinutes(student.total_minutes) }}</template>
              </el-table-column>
            </el-table>
          </template>
        </el-table-column>
        <el-table-column prop="tutor_name" label="导师" />
        <el-table-column prop="student_count" label="学生数" width="90" />
        <el-table-column prop="booking_count" label="预约次数" width="100" />
        <el-table-column label="累计时长" width="140">
          <template #default="{ row }">{{ formatMinutes(row.total_minutes) }}</template>
        </el-table-column>
      </el-table>
    </el-drawer>
  </el-card>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  listEquipments,
  createEquipment,
  updateEquipment,
  deleteEquipment,
  getEquipmentCalendar,
  exportEquipmentUsageRecords,
  dispatchBallMillQueue,
  getXrdTutorStats,
} from '@/api/equipment'
import { fetchRdpMachines } from '@/api/remote_access'
import apiClient from '@/api'
import { formatElectrochemicalTimeRange } from './instrument-booking/helpers'

const BALL_MILL_WEEKLY_PUBLISH_TIME = '00:00'
const BALL_MILL_WEEKLY_QUEUE_ALLOCATE_WINDOW_DAYS = 7
const BALL_MILL_WEEKLY_QUEUE_PUBLISH_LEAD_DAYS = 5
const BALL_MILL_WEEKLY_DIRECT_BOOKING_MAX_DAYS = 14
const BALL_MILL_WEEKLY_ACTION_MAX_ADVANCE_DAYS = 18
const ELECTROCHEMICAL_MAX_ADVANCE_DAYS = 7

const defaultForm = (bookingMode = 'standard') => {
  const isBallMill = bookingMode === 'planetary_ball_mill'
  const isElectrochemical = bookingMode === 'electrochemical_workstation'
  return {
    id: null,
    name: isBallMill ? '行星球磨机' : (isElectrochemical ? '输力强电化学工作站' : (bookingMode === 'xrd' ? 'XRD' : '')),
    booking_mode: bookingMode,
    location: '',
    time_slot_minutes: 60,
    open_time: (isBallMill || isElectrochemical) ? '00:00' : '08:00',
    close_time: (isBallMill || isElectrochemical) ? '23:59' : '22:00',
    advance_days: isBallMill
      ? BALL_MILL_WEEKLY_ACTION_MAX_ADVANCE_DAYS
      : (isElectrochemical ? ELECTROCHEMICAL_MAX_ADVANCE_DAYS : 7),
    ball_mill_duration_unit_minutes: 12,
    ball_mill_min_rotation_speed_rpm: 1,
    ball_mill_max_rotation_speed_rpm: null,
    ball_mill_max_actual_minutes: 48 * 60,
    ball_mill_monthly_max_actual_minutes: null,
    ball_mill_queue_enabled: false,
    ball_mill_queue_publish_time: BALL_MILL_WEEKLY_PUBLISH_TIME,
    ball_mill_queue_request_window_days: BALL_MILL_WEEKLY_ACTION_MAX_ADVANCE_DAYS,
    ball_mill_queue_allocate_window_days: BALL_MILL_WEEKLY_QUEUE_ALLOCATE_WINDOW_DAYS,
    ball_mill_queue_dispatch_cursor_date: null,
    ball_mill_queue_publish_lead_days: BALL_MILL_WEEKLY_QUEUE_PUBLISH_LEAD_DAYS,
    ball_mill_queue_day_start_time: '07:00',
    ball_mill_queue_day_end_time: '22:00',
    ball_mill_queue_heavy_user_threshold_minutes: 72 * 60,
    ball_mill_direct_booking_window_days: BALL_MILL_WEEKLY_DIRECT_BOOKING_MAX_DAYS,
    ball_mill_direct_booking_cutoff_time: BALL_MILL_WEEKLY_PUBLISH_TIME,
    electrochemical_offline_channels: [],
    xrd_remote_machine: null,
    early_bird_advance_days: null,
    early_bird_users: [],
    booking_allowed_users: [],
    is_active: true,
    description: '',
  }
}

const equipments = ref([])
const loading = ref(false)
const exportingEquipmentId = ref(null)

const editVisible = ref(false)
const editForm = ref(defaultForm())

const earlyBirdCandidates = ref([])
const earlyBirdLoading = ref(false)
const remoteMachineOptions = ref([])
const remoteMachinesLoading = ref(false)

const calendarVisible = ref(false)
const calendarRows = ref([])
const calendarDate = ref(new Date())
const calendarTitle = ref('')
const calendarEquipmentId = ref(null)
const calendarEquipmentMode = ref('standard')

const xrdStatsVisible = ref(false)
const xrdStatsTitle = ref('')
const xrdStatsEquipmentId = ref(null)
const xrdStatsMonth = ref(toLocalDateString(new Date()).slice(0, 7))
const xrdStatsRows = ref([])
const xrdStatsLoading = ref(false)

const isStandardLikeEditMode = computed(() => ['standard', 'xrd'].includes(editForm.value.booking_mode))
const isTimeGranularityEditMode = computed(() =>
  ['standard', 'xrd', 'electrochemical_workstation'].includes(editForm.value.booking_mode),
)

const autoBallMillAdvanceDays = computed(() => {
  if (editForm.value.booking_mode !== 'planetary_ball_mill') {
    return editForm.value.advance_days || 0
  }
  return BALL_MILL_WEEKLY_ACTION_MAX_ADVANCE_DAYS
})

onMounted(() => {
  load()
  loadRemoteMachines()
})

function toLocalDateString(dateLike) {
  const d = new Date(dateLike)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function formatClock(value) {
  return (value || '').slice(0, 5)
}

function formatHours(minutes) {
  if (!minutes) return '0 小时'
  const hours = (minutes / 60).toFixed(minutes % 60 === 0 ? 0 : 1)
  return `${hours} 小时`
}

function formatOptionalHours(minutes) {
  if (!minutes) return '不限制'
  return formatHours(minutes)
}

function equipmentModeLabel(row) {
  if (row?.booking_mode === 'planetary_ball_mill') return '行星球磨机'
  if (row?.booking_mode === 'electrochemical_workstation') return '输力强电化学工作站'
  if (row?.booking_mode === 'xrd') return 'XRD'
  return '普通仪器'
}

function equipmentModeTagType(row) {
  if (row?.booking_mode === 'planetary_ball_mill') return 'warning'
  if (row?.booking_mode === 'electrochemical_workstation') return 'success'
  if (row?.booking_mode === 'xrd') return 'primary'
  return 'info'
}

function formatMinutes(minutes) {
  const total = Number(minutes || 0)
  const hours = Math.floor(total / 60)
  const mins = total % 60
  if (!hours) return `${mins} 分钟`
  if (!mins) return `${hours} 小时`
  return `${hours} 小时 ${mins} 分钟`
}

function formatRotationSpeedRange(row) {
  const minRpm = Number(row?.ball_mill_min_rotation_speed_rpm || 1)
  const maxRpm = row?.ball_mill_max_rotation_speed_rpm
  if (maxRpm == null || maxRpm === '') return `${minRpm} r/min 起`
  return `${minRpm} - ${Number(maxRpm)} r/min`
}

function formatRemoteMachineOption(machine) {
  if (!machine) return ''
  return machine.is_active === false ? `${machine.name}（未开放）` : machine.name
}

function calcBallMillMaxMillingMinutes(maxActualMinutes) {
  const maxMinutes = Number(maxActualMinutes || 0)
  if (maxMinutes <= 0) return 0
  let low = 0
  let high = maxMinutes
  while (low < high) {
    const mid = Math.floor((low + high + 1) / 2)
    const pauses = Math.floor(mid / 12)
    const actual = mid + pauses * 6
    if (actual <= maxMinutes) {
      low = mid
    } else {
      high = mid - 1
    }
  }
  return low
}

function formatBookingDate(row) {
  if (!row?.date) return '-'
  if (row.end_date && row.end_date !== row.date) {
    return `${row.date} 至 ${row.end_date}`
  }
  return row.date
}

function formatBookingTime(row) {
  if (row?.booking_mode === 'electrochemical_workstation') {
    return formatElectrochemicalTimeRange(row?.start_time, row?.end_time)
  }
  return `${formatClock(row?.start_time)} - ${formatClock(row?.end_time)}`
}

function formatBallMillDetails(row) {
  if (!row || row.booking_mode !== 'planetary_ball_mill') return '-'
  const parts = []
  if (row.position_no) parts.push(`${row.position_no} 号位`)
  if (row.operation_type_display) parts.push(row.operation_type_display)
  if (row.rotation_speed_rpm) parts.push(`${row.rotation_speed_rpm} r/min`)
  if (row.milling_minutes) parts.push(`球磨 ${row.milling_minutes} 分钟`)
  if (row.actual_duration_minutes) parts.push(`真实 ${row.actual_duration_minutes} 分钟`)
  return parts.join(' / ') || '-'
}

async function load() {
  loading.value = true
  try {
    const { data } = await listEquipments()
    equipments.value = data
  } finally {
    loading.value = false
  }
}

async function loadEarlyBirdCandidates() {
  if (earlyBirdCandidates.value.length) return
  earlyBirdLoading.value = true
  try {
    const { data } = await apiClient.get('/equipment/equipments/early-bird-candidates/')
    earlyBirdCandidates.value = data || []
  } catch (e) {
    ElMessage.error('加载早鸟用户列表失败')
  } finally {
    earlyBirdLoading.value = false
  }
}

async function loadRemoteMachines() {
  if (remoteMachineOptions.value.length || remoteMachinesLoading.value) return
  remoteMachinesLoading.value = true
  try {
    const { data } = await fetchRdpMachines()
    remoteMachineOptions.value = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : [])
  } catch (e) {
    ElMessage.error('加载远程主机列表失败')
  } finally {
    remoteMachinesLoading.value = false
  }
}

function openEdit(row, bookingMode = 'standard') {
  if (row) {
    editForm.value = {
      id: row.id,
      name: row.name,
      booking_mode: row.booking_mode || 'standard',
      location: row.location,
      time_slot_minutes: row.time_slot_minutes,
      open_time: formatClock(row.open_time),
      close_time: formatClock(row.close_time),
      advance_days: row.advance_days,
      ball_mill_duration_unit_minutes: row.ball_mill_duration_unit_minutes ?? 12,
      ball_mill_min_rotation_speed_rpm: row.ball_mill_min_rotation_speed_rpm ?? 1,
      ball_mill_max_rotation_speed_rpm: row.ball_mill_max_rotation_speed_rpm ?? null,
      ball_mill_max_actual_minutes: row.ball_mill_max_actual_minutes ?? 48 * 60,
      ball_mill_monthly_max_actual_minutes: row.ball_mill_monthly_max_actual_minutes ?? null,
      ball_mill_queue_enabled: Boolean(row.ball_mill_queue_enabled),
      ball_mill_queue_publish_time: BALL_MILL_WEEKLY_PUBLISH_TIME,
      ball_mill_queue_request_window_days: BALL_MILL_WEEKLY_ACTION_MAX_ADVANCE_DAYS,
      ball_mill_queue_allocate_window_days: BALL_MILL_WEEKLY_QUEUE_ALLOCATE_WINDOW_DAYS,
      ball_mill_queue_dispatch_cursor_date: row.ball_mill_queue_dispatch_cursor_date || null,
      ball_mill_queue_publish_lead_days: BALL_MILL_WEEKLY_QUEUE_PUBLISH_LEAD_DAYS,
      ball_mill_queue_day_start_time: formatClock(row.ball_mill_queue_day_start_time || '07:00'),
      ball_mill_queue_day_end_time: formatClock(row.ball_mill_queue_day_end_time || '22:00'),
      ball_mill_queue_heavy_user_threshold_minutes:
        row.ball_mill_queue_heavy_user_threshold_minutes ?? 72 * 60,
      ball_mill_direct_booking_window_days: BALL_MILL_WEEKLY_DIRECT_BOOKING_MAX_DAYS,
      ball_mill_direct_booking_cutoff_time: BALL_MILL_WEEKLY_PUBLISH_TIME,
      electrochemical_offline_channels: Array.isArray(row.electrochemical_offline_channels)
        ? [...row.electrochemical_offline_channels]
        : [],
      xrd_remote_machine: row.xrd_remote_machine ?? null,
      early_bird_advance_days:
        row.early_bird_advance_days != null
          ? row.early_bird_advance_days
          : (row.booking_mode === 'planetary_ball_mill'
            ? BALL_MILL_WEEKLY_ACTION_MAX_ADVANCE_DAYS
            : row.advance_days),
      early_bird_users: Array.isArray(row.early_bird_users) ? [...row.early_bird_users] : [],
      booking_allowed_users: Array.isArray(row.booking_allowed_users)
        ? [...row.booking_allowed_users]
        : [],
      is_active: row.is_active,
      description: row.description || '',
    }
  } else {
    editForm.value = defaultForm(bookingMode)
  }
  editVisible.value = true
  loadEarlyBirdCandidates()
  loadRemoteMachines()
}

async function save() {
  try {
    if (!editForm.value.name) {
      ElMessage.error('名称必填')
      return
    }
    if (isStandardLikeEditMode.value && (!editForm.value.open_time || !editForm.value.close_time)) {
      ElMessage.error('请填写开放时间')
      return
    }
    if (
      isTimeGranularityEditMode.value &&
      (!Number.isInteger(Number(editForm.value.time_slot_minutes)) || Number(editForm.value.time_slot_minutes) <= 0)
    ) {
      ElMessage.error('请设置有效的时间粒度')
      return
    }
    if (editForm.value.booking_mode === 'planetary_ball_mill') {
      if (
        !editForm.value.ball_mill_min_rotation_speed_rpm ||
        editForm.value.ball_mill_min_rotation_speed_rpm <= 0
      ) {
        ElMessage.error('最小转速必须大于 0')
        return
      }
      if (
        editForm.value.ball_mill_max_rotation_speed_rpm != null &&
        editForm.value.ball_mill_max_rotation_speed_rpm < editForm.value.ball_mill_min_rotation_speed_rpm
      ) {
        ElMessage.error('最大转速不能小于最小转速')
        return
      }
      if (!editForm.value.ball_mill_max_actual_minutes || editForm.value.ball_mill_max_actual_minutes <= 0) {
        ElMessage.error('请设置有效的单次最大预约上限')
        return
      }
      if (
        editForm.value.ball_mill_monthly_max_actual_minutes != null &&
        editForm.value.ball_mill_monthly_max_actual_minutes < editForm.value.ball_mill_max_actual_minutes
      ) {
        ElMessage.error('每月最大预约上限不能小于单次最大预约上限')
        return
      }
      if (editForm.value.ball_mill_queue_enabled) {
        if (
          !editForm.value.ball_mill_queue_day_start_time ||
          !editForm.value.ball_mill_queue_day_end_time
        ) {
          ElMessage.error('请设置排队可分配开始时段')
          return
        }
        if (editForm.value.ball_mill_queue_day_start_time >= editForm.value.ball_mill_queue_day_end_time) {
          ElMessage.error('可分配开始时段起点必须早于终点')
          return
        }
        if (
          !editForm.value.ball_mill_queue_heavy_user_threshold_minutes ||
          editForm.value.ball_mill_queue_heavy_user_threshold_minutes <= 0
        ) {
          ElMessage.error('重度用户阈值必须大于 0')
          return
        }
      }
    }

    const payload = { ...editForm.value }
    if (payload.booking_mode === 'planetary_ball_mill') {
      payload.advance_days = BALL_MILL_WEEKLY_ACTION_MAX_ADVANCE_DAYS
      payload.ball_mill_queue_publish_time = BALL_MILL_WEEKLY_PUBLISH_TIME
      payload.ball_mill_queue_request_window_days = BALL_MILL_WEEKLY_ACTION_MAX_ADVANCE_DAYS
      payload.ball_mill_queue_allocate_window_days = BALL_MILL_WEEKLY_QUEUE_ALLOCATE_WINDOW_DAYS
      payload.ball_mill_queue_publish_lead_days = BALL_MILL_WEEKLY_QUEUE_PUBLISH_LEAD_DAYS
      payload.ball_mill_direct_booking_window_days = BALL_MILL_WEEKLY_DIRECT_BOOKING_MAX_DAYS
      payload.ball_mill_direct_booking_cutoff_time = BALL_MILL_WEEKLY_PUBLISH_TIME
      payload.ball_mill_queue_dispatch_cursor_date = null
    } else if (payload.booking_mode === 'electrochemical_workstation') {
      payload.open_time = '00:00'
      payload.close_time = '23:59'
      payload.advance_days = ELECTROCHEMICAL_MAX_ADVANCE_DAYS
      payload.early_bird_advance_days = ELECTROCHEMICAL_MAX_ADVANCE_DAYS
      payload.early_bird_users = []
      payload.booking_allowed_users = []
    } else {
      payload.booking_allowed_users = []
    }

    if (payload.id) {
      await updateEquipment(payload.id, payload)
      ElMessage.success('更新成功')
    } else {
      await createEquipment(payload)
      ElMessage.success('创建成功')
    }
    editVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

async function remove(row) {
  try {
    await deleteEquipment(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

function getFilenameFromDisposition(disposition, fallback) {
  if (!disposition) return fallback
  const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1])
    } catch {
      return utf8Match[1]
    }
  }
  const asciiMatch = disposition.match(/filename="?([^";]+)"?/i)
  return asciiMatch?.[1] || fallback
}

function safeDownloadFilename(value) {
  return String(value || '仪器使用记录.csv').replace(/[\\/:*?"<>|\r\n]/g, '_')
}

async function getBlobErrorMessage(error) {
  const data = error?.response?.data
  if (!(data instanceof Blob)) {
    return data?.detail || '导出使用记录失败'
  }
  try {
    const payload = JSON.parse(await data.text())
    return payload?.detail || payload?.error || '导出使用记录失败'
  } catch {
    return '导出使用记录失败'
  }
}

async function exportUsageRecords(row) {
  exportingEquipmentId.value = row.id
  try {
    const response = await exportEquipmentUsageRecords(row.id)
    const fallback = `${row.name || '仪器'}_使用记录.csv`
    const filename = safeDownloadFilename(
      getFilenameFromDisposition(response.headers?.['content-disposition'], fallback),
    )
    const url = window.URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    ElMessage.success('使用记录 CSV 已生成')
  } catch (error) {
    ElMessage.error(await getBlobErrorMessage(error))
  } finally {
    exportingEquipmentId.value = null
  }
}

async function runQueueDispatch(row) {
  try {
    const { data } = await dispatchBallMillQueue(row.id, { force: true })
    if (!data?.executed) {
      ElMessage.warning(
        data?.detail ||
        `当前批次 ${data?.dispatch_window_start_date || '-'} ~ ${data?.dispatch_window_end_date || '-'} 尚未到放榜日期`
      )
      return
    }
    ElMessage.success(
      `放榜完成（批次 ${data?.dispatch_window_start_date || '-'} ~ ${data?.dispatch_window_end_date || '-'}）：` +
      `分配 ${data?.allocated_count ?? 0} 条，顺延 ${data?.rolled_over_count ?? 0} 条，` +
      `未分配 ${data?.skipped_count ?? 0} 条；下一批 ${data?.next_dispatch_window_start_date || '-'} 开始`
    )
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '放榜失败')
  }
}

function viewXrdStats(row) {
  xrdStatsTitle.value = `${row.name} - 导师统计`
  xrdStatsEquipmentId.value = row.id
  xrdStatsVisible.value = true
  loadXrdStats()
}

async function loadXrdStats() {
  if (!xrdStatsEquipmentId.value) return
  xrdStatsLoading.value = true
  try {
    const { data } = await getXrdTutorStats(xrdStatsEquipmentId.value, {
      month: xrdStatsMonth.value,
    })
    xrdStatsRows.value = Array.isArray(data?.rows) ? data.rows : []
  } catch (e) {
    xrdStatsRows.value = []
    ElMessage.error(e?.response?.data?.detail || '加载 XRD 导师统计失败')
  } finally {
    xrdStatsLoading.value = false
  }
}

function viewCalendar(row) {
  calendarTitle.value = `${row.name} - 当日预约`
  calendarEquipmentId.value = row.id
  calendarEquipmentMode.value = row.booking_mode || 'standard'
  calendarVisible.value = true
  calendarDate.value = new Date()
  loadCalendar()
}

async function loadCalendar() {
  if (!calendarEquipmentId.value) return
  try {
    const ds = toLocalDateString(calendarDate.value)
    const { data } = await getEquipmentCalendar(calendarEquipmentId.value, ds)
    calendarRows.value = data || []
  } catch (e) {
    calendarRows.value = []
    ElMessage.error('加载预约日历失败')
  }
}
</script>

<style scoped>
.page {
  max-width: 1100px;
  margin: 20px auto;
}

.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.hint {
  margin-left: 12px;
  font-size: 12px;
  color: #909399;
}

.formula-block {
  color: #606266;
  line-height: 1.6;
}
</style>

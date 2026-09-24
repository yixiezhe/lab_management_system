<template>
  <el-drawer v-model="xrdTutorStatsVisible" title="XRD 导师统计" size="65%">
    <div class="xrd-stats-toolbar">
      <el-date-picker
        v-model="xrdTutorStatsMonth"
        type="month"
        value-format="YYYY-MM"
        placeholder="选择月份"
        @change="loadXrdTutorStats"
      />
    </div>

    <el-table
      :data="xrdTutorStatsRows"
      v-loading="loading.xrdTutorStats"
      size="small"
      style="margin-top: 12px"
    >
      <el-table-column prop="tutor_name" label="导师" min-width="140" />
      <el-table-column prop="student_count" label="学生数" width="90" />
      <el-table-column prop="booking_count" label="预约次数" width="100" />
      <el-table-column label="总时长" width="140">
        <template #default="{ row }">
          {{ formatMinutes(row.total_minutes) }}
        </template>
      </el-table-column>
      <el-table-column label="学生明细" min-width="240">
        <template #default="{ row }">
          <template v-if="row.can_view_details">
            <el-table :data="row.students" size="small" border>
              <el-table-column prop="student_name" label="学生" min-width="100" />
              <el-table-column prop="booking_count" label="次数" width="70" />
              <el-table-column label="累计时长" width="110">
                <template #default="{ row: student }">
                  {{ formatMinutes(student.total_minutes) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="80">
                <template #default="{ row: student }">
                  <el-button link type="primary" @click="openXrdStudentStats(student)">
                    明细
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
          </template>
          <span v-else class="xrd-stats-muted">仅显示该导师总时长</span>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      :model-value="Boolean(selectedXrdStudentStats)"
      :title="selectedXrdStudentStats ? `${selectedXrdStudentStats.student_name} - XRD 明细` : 'XRD 明细'"
      width="720px"
      append-to-body
      @close="closeXrdStudentStats"
    >
      <el-table :data="selectedXrdStudentStats?.bookings || []" size="small">
        <el-table-column prop="date" label="日期" width="110" />
        <el-table-column label="时间" width="130">
          <template #default="{ row }">
            {{ row.start_time }} - {{ row.end_time }}
          </template>
        </el-table-column>
        <el-table-column label="占用时长" width="110">
          <template #default="{ row }">
            {{ formatMinutes(row.actual_duration_minutes) }}
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="120" />
      </el-table>
    </el-dialog>
  </el-drawer>
</template>

<script setup>
import { useInstrumentBookingController } from '../context'

const {
  xrdTutorStatsVisible,
  xrdTutorStatsRows,
  xrdTutorStatsMonth,
  selectedXrdStudentStats,
  loading,
  loadXrdTutorStats,
  openXrdStudentStats,
  closeXrdStudentStats,
} = useInstrumentBookingController()

function formatMinutes(minutes) {
  const total = Number(minutes || 0)
  const hours = Math.floor(total / 60)
  const mins = total % 60
  if (!hours) return `${mins} 分钟`
  if (!mins) return `${hours} 小时`
  return `${hours} 小时 ${mins} 分钟`
}
</script>

<style scoped>
.xrd-stats-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
}

.xrd-stats-muted {
  color: #909399;
}
</style>

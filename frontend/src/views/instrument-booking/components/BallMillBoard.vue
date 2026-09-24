<template>
  <div class="ball-mill-booking-board">
    <div class="booking-board-header">
      <div>
        <h3>{{ selectedDate }} 预约详情</h3>
        <p>展示当前所选日期内所有用户正在生效的球磨机预约记录</p>
      </div>
    </div>

    <el-empty
      v-if="!loading.dayBookings && !ballMillDayBookings.length"
      description="该日期暂无预约记录"
    />

    <el-table
      v-else
      :data="ballMillDayBookingsDisplay"
      v-loading="loading.dayBookings"
      size="small"
    >
      <el-table-column prop="user_name" label="预约人" min-width="110" />
      <el-table-column v-if="isSystemAdmin" label="操作" min-width="132">
        <template #default="{ row }">
          <div class="booking-admin-actions">
            <el-popconfirm :title="getCancelBookingConfirmText(row)" @confirm="cancelBooking(row)">
              <template #reference>
                <el-button link type="danger" :disabled="!canCancelBooking(row)">取消</el-button>
              </template>
            </el-popconfirm>
            <el-popconfirm
              title="确定彻底删除该预约吗？删除后不可恢复。"
              @confirm="forceDeleteBooking(row)"
            >
              <template #reference>
                <el-button link type="danger" :disabled="!canModifyBooking(row)">删除</el-button>
              </template>
            </el-popconfirm>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="用途" min-width="110">
        <template #default="{ row }">
          {{ row.operation_type_display || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="工位" min-width="140">
        <template #default="{ row }">
          {{ formatBallMillPositions(row) }}
        </template>
      </el-table-column>
      <el-table-column label="开始时间" min-width="160">
        <template #default="{ row }">
          {{ formatDateTime(row.start_at) }}
        </template>
      </el-table-column>
      <el-table-column label="结束时间" min-width="160">
        <template #default="{ row }">
          {{ formatDateTime(row.end_at) }}
        </template>
      </el-table-column>
      <el-table-column label="转速" min-width="100">
        <template #default="{ row }">
          {{ row.rotation_speed_rpm ? `${row.rotation_speed_rpm} r/min` : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="球磨时间" min-width="100">
        <template #default="{ row }">
          {{ row.milling_minutes ? `${row.milling_minutes} 分钟` : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="真实时间" min-width="120">
        <template #default="{ row }">
          {{ row.actual_duration_minutes ? formatDuration(row.actual_duration_minutes) : '-' }}
        </template>
      </el-table-column>
    </el-table>

    <div v-if="isBallMillQueueMode" class="queue-board-header">
      <h3>排队情况</h3>
      <el-button size="small" type="primary" plain :loading="loading.queue" @click="fetchBallMillQueueRequests()">
        刷新
      </el-button>
    </div>

    <el-empty
      v-if="isBallMillQueueMode && !loading.queue && !queueBoardRows.length"
      :description="queueBoardEmptyDescription"
    />

    <el-table
      v-else-if="isBallMillQueueMode"
      :data="queueBoardRows"
      v-loading="loading.queue"
      size="small"
      style="margin-top: 10px"
    >
      <el-table-column label="提交时间" min-width="160">
        <template #default="{ row }">
          {{ formatDateTime(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="申请人" min-width="120">
        <template #default="{ row }">
          {{ row.user_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column label="排队批次" min-width="220">
        <template #default="{ row }">
          {{ formatQueueBatchRange(row.requested_date) }}
        </template>
      </el-table-column>
      <el-table-column label="需求工位" min-width="82">
        <template #default="{ row }">
          {{ row.position_count }}
        </template>
      </el-table-column>
      <el-table-column label="转速" min-width="100">
        <template #default="{ row }">
          {{ row.rotation_speed_rpm ? `${row.rotation_speed_rpm} r/min` : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="球磨时间" min-width="96">
        <template #default="{ row }">
          {{ row.milling_minutes ? `${row.milling_minutes} 分钟` : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="真实时长" min-width="110">
        <template #default="{ row }">
          {{ row.actual_duration_minutes ? formatDuration(row.actual_duration_minutes) : '-' }}
        </template>
      </el-table-column>
      <el-table-column label="状态" min-width="100">
        <template #default="{ row }">
          <el-tag :type="queueStatusType(row.status)">
            {{ queueStatusLabel(row.status) }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="排队顺位" min-width="90">
        <template #default="{ row }">
          <span v-if="getQueueDisplayRank(row)">第 {{ getQueueDisplayRank(row) }}</span>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="分配结果" min-width="180" show-overflow-tooltip>
        <template #default="{ row }">
          {{ queueAllocationText(row) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="96" fixed="right">
        <template #default="{ row }">
          <el-popconfirm
            v-if="canDeleteQueueRequest(row)"
            title="确定删除该排队记录吗？删除后不可恢复。"
            @confirm="deleteQueueRequest(row)"
          >
            <template #reference>
              <el-button link type="danger">删除</el-button>
            </template>
          </el-popconfirm>
          <el-popconfirm
            v-else-if="row.status === 'pending' && canCancelQueueRequest(row)"
            title="确定取消该排队申请吗？"
            @confirm="cancelQueueRequest(row)"
          >
            <template #reference>
              <el-button link type="danger">取消</el-button>
            </template>
          </el-popconfirm>
          <span v-else>-</span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { useInstrumentBookingController } from '../context'
import { formatDateTime } from '../helpers'

const {
  selectedDate,
  loading,
  ballMillDayBookings,
  ballMillDayBookingsDisplay,
  isSystemAdmin,
  getCancelBookingConfirmText,
  canModifyBooking,
  canCancelBooking,
  cancelBooking,
  forceDeleteBooking,
  formatBallMillPositions,
  formatDuration,
  isBallMillQueueMode,
  fetchBallMillQueueRequests,
  queueBoardRows,
  queueBoardEmptyDescription,
  formatQueueBatchRange,
  queueStatusType,
  queueStatusLabel,
  getQueueDisplayRank,
  queueAllocationText,
  canDeleteQueueRequest,
  deleteQueueRequest,
  canCancelQueueRequest,
  cancelQueueRequest,
} = useInstrumentBookingController()
</script>

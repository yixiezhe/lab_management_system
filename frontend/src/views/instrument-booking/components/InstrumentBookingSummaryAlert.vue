<template>
  <el-alert v-if="equipmentInfo && !isElectrochemicalMode" type="info" :closable="false" class="bar">
    <template #title>
      <template v-if="isBallMillMode">
        行星球磨机：固定 4 工位；24 小时开放；整点开始预约；
        每球磨 {{ equipmentInfo.ballMillCycleRunMinutes }} 分钟自动停机 {{ equipmentInfo.ballMillCyclePauseMinutes }} 分钟；
        单次真实预约上限 {{ formatDuration(equipmentInfo.ballMillMaxActualMinutes) }}，
        对应球磨时间上限 {{ equipmentInfo.ballMillMaxMillingMinutes }} 分钟；
        允许转速范围 {{ ballMillRotationSpeedRangeText }}；
        <template v-if="equipmentInfo.ballMillQueueEnabled">
          排队规则：每周三 00:00 放榜；放榜前可直接预约本周，放榜后可直接预约本周与下一周；
          排队申请窗口始终为“当前可直约窗口之后的下一整周”。
        </template>
        <template v-else>排队机制未启用</template>
        <template v-if="testClockEnabled">
          ；测试系统日期 {{ testClockDisplayText }}
        </template>
      </template>
      <template v-else>
        开放时间：{{ equipmentInfo.openStart }} - {{ equipmentInfo.openEnd }}；
        时间粒度：{{ equipmentInfo.timeUnit }} 分钟；
        可提前预约：{{ equipmentInfo.maxAdvance }} 天
      </template>
    </template>
  </el-alert>
</template>

<script setup>
import { useInstrumentBookingController } from '../context'

const {
  equipmentInfo,
  isBallMillMode,
  isElectrochemicalMode,
  formatDuration,
  ballMillRotationSpeedRangeText,
  testClockEnabled,
  testClockDisplayText,
} = useInstrumentBookingController()
</script>

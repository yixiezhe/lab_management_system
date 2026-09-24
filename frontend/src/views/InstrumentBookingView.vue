<template>
  <div class="instrument-booking-page page">
    <div
      class="page-shell"
      :class="{
        'page-shell--ball-mill': isBallMillMode,
        'page-shell--electrochemical': isElectrochemicalMode || isXrdMode,
      }"
    >
      <el-card
        class="wrap"
        :class="{
          'wrap--ball-mill': isBallMillMode,
          'wrap--electrochemical': isElectrochemicalMode || isXrdMode,
        }"
      >
        <template #header>
          <InstrumentBookingToolbar />
        </template>

        <InstrumentBookingSummaryAlert />

        <template v-if="isBallMillMode">
          <BallMillPanel />
          <BallMillBoard />
        </template>
        <template v-else>
          <StandardBookingPanel />
        </template>

        <el-divider />
        <MyBookingsTable />
      </el-card>

      <BallMillCalendarRail v-if="isBallMillMode" />
      <ElectrochemicalCalendarRail v-else-if="isElectrochemicalMode || isXrdMode" />
    </div>

    <BookingHistoryDialog />
    <XrdTutorStatsDialog />
  </div>
</template>

<script setup>
import './instrument-booking/styles/layout.css'
import './instrument-booking/styles/ballmill.css'
import './instrument-booking/styles/responsive.css'
import BallMillBoard from './instrument-booking/components/BallMillBoard.vue'
import BallMillCalendarRail from './instrument-booking/components/BallMillCalendarRail.vue'
import BallMillPanel from './instrument-booking/components/BallMillPanel.vue'
import BookingHistoryDialog from './instrument-booking/components/BookingHistoryDialog.vue'
import ElectrochemicalCalendarRail from './instrument-booking/components/ElectrochemicalCalendarRail.vue'
import InstrumentBookingSummaryAlert from './instrument-booking/components/InstrumentBookingSummaryAlert.vue'
import InstrumentBookingToolbar from './instrument-booking/components/InstrumentBookingToolbar.vue'
import MyBookingsTable from './instrument-booking/components/MyBookingsTable.vue'
import StandardBookingPanel from './instrument-booking/components/StandardBookingPanel.vue'
import XrdTutorStatsDialog from './instrument-booking/components/XrdTutorStatsDialog.vue'
import { provideInstrumentBookingController } from './instrument-booking/context'
import { useInstrumentBookingPage } from './instrument-booking/composables/useInstrumentBookingPage'

const controller = useInstrumentBookingPage()
provideInstrumentBookingController(controller)

const { isBallMillMode, isElectrochemicalMode, isXrdMode } = controller
</script>

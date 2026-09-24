import { inject, provide } from 'vue'

const INSTRUMENT_BOOKING_CONTROLLER_KEY = Symbol('instrument-booking-controller')

export function provideInstrumentBookingController(controller) {
  provide(INSTRUMENT_BOOKING_CONTROLLER_KEY, controller)
}

export function useInstrumentBookingController() {
  const controller = inject(INSTRUMENT_BOOKING_CONTROLLER_KEY, null)
  if (!controller) {
    throw new Error('Instrument booking controller is not available')
  }
  return controller
}

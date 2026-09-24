import apiClient from '@/api';

export const PUBLIC_DUTY_SCHEDULE_API = '/procurement/public-duty-schedule/';

export const DEFAULT_PUBLIC_DUTY_SCHEDULE = [
  { weekday: 0, label: '周日', name: '示例成员26' },
  { weekday: 1, label: '周一', name: '示例成员22' },
  { weekday: 2, label: '周二', name: '示例成员24' },
  { weekday: 3, label: '周三', name: '示例成员26' },
  { weekday: 4, label: '周四', name: '示例成员07' },
  { weekday: 5, label: '周五', name: '示例成员11' },
  { weekday: 6, label: '周六', name: '示例成员05' },
];

export const normalizePublicDutySchedule = (value) => {
  const source = Array.isArray(value) ? value : [];
  return DEFAULT_PUBLIC_DUTY_SCHEDULE.map((defaultItem) => {
    const matched = source.find(item => Number(item?.weekday) === defaultItem.weekday);
    const normalizedName = typeof matched?.name === 'string' ? matched.name.trim() : '';
    return {
      ...defaultItem,
      name: normalizedName,
    };
  });
};

export const publicDutySchedulePayload = (schedule) =>
  normalizePublicDutySchedule(schedule).map(({ weekday, name }) => ({
    weekday,
    name: typeof name === 'string' ? name.trim() : '',
  }));

export const getTodayPublicDutyPerson = (schedule, date = new Date()) => {
  const normalized = normalizePublicDutySchedule(schedule);
  const today = date.getDay();
  const matched = normalized.find(item => item.weekday === today);
  return matched?.name?.trim() || '未指定';
};

export const fetchPublicDutySchedule = async () => {
  const res = await apiClient.get(PUBLIC_DUTY_SCHEDULE_API);
  return normalizePublicDutySchedule(res.data?.weekly_duty);
};

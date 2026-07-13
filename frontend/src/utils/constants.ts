// frontend/src/utils/constants.ts
export const ALERT_LEVEL_OPTIONS = [
  { label: '提示', value: 'info', tagType: 'info' },
  { label: '警告', value: 'warning', tagType: 'warning' },
  { label: '危险', value: 'danger', tagType: 'danger' },
]

export const ALERT_STATUS_OPTIONS = [
  { label: '待处理', value: 'pending', tagType: 'warning' },
  { label: '已处理', value: 'handled', tagType: 'success' },
  { label: '已忽略', value: 'ignored', tagType: 'info' },
]

export const ALERT_TYPE_OPTIONS = [
  { label: '疲劳驾驶', value: '疲劳驾驶' },
  { label: '障碍物检测', value: '障碍物检测' },
  { label: '超速警告', value: '超速警告' },
  { label: '其他', value: '其他' },
]
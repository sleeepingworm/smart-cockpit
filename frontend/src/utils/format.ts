// 根据value找label（用于表格里把status字段的pending显示成"待处理"）
export function optionLabel(options: any[], value: any): string {
  const found = options.find(o => o.value === value)
  return found ? found.label : String(value)
}

// 根据value找tagType（用于el-tag的type属性，决定颜色）
export function optionTagType(options: any[], value: any): string {
  const found = options.find(o => o.value === value)
  return found?.tagType || 'info'
}

// 时间格式化（后端返回的是ISO字符串，要格式化成 YYYY-MM-DD HH:mm:ss）
export function formatDateTime(dt: string | null | undefined): string {
  if (!dt) return '-'
  const d = new Date(dt)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}
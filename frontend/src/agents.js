// Pipeline stations, in execution order. `key` matches the agent name written by the backend trace.
export const STATIONS = [
  { key: 'Orchestrator', label: 'Orchestrator', role: 'Lập kế hoạch, phân công' },
  { key: 'Data Engineer', label: 'Data Engineer', role: 'Nạp & kiểm tra dữ liệu' },
  { key: 'Human', label: 'Phê duyệt', role: 'Cho phép kết nối DB ngoài', valve: true },
  { key: 'Data Analyst', label: 'Data Analyst', role: 'Phân tích thị trường' },
  { key: 'Data Scientist', label: 'Data Scientist', role: 'Mô hình & dự báo' },
  { key: 'Report Writer', label: 'Report Writer', role: 'Viết báo cáo' },
]

export const AGENT_TONE = {
  Orchestrator: 'hull',
  'Data Engineer': 'cryo',
  Human: 'valve',
  'Data Analyst': 'cryo',
  'Data Scientist': 'cryo',
  'Report Writer': 'hull',
  System: 'brick',
}

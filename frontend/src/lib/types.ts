// TS mirrors of the backend Pydantic models + SSE payloads.

export interface SessionSummary {
  id: string
  title: string
  created_at: string
  updated_at: string
  has_brief: number
}

export interface Message {
  id: number
  role: 'user' | 'assistant' | 'system'
  agent: string | null
  content: string
  created_at: string
}

export interface BuildSummary {
  id: string
  status: 'running' | 'done' | 'failed'
  created_at: string
}

export interface SessionDetail {
  session: {
    id: string
    title: string
    brief: Record<string, unknown> | null
    created_at: string
    updated_at: string
  }
  messages: Message[]
  builds: BuildSummary[]
}

export interface FileMeta {
  filename: string
  revision: number
  size: number
}

export interface MachineCheck {
  name: string
  passed: boolean
  detail: string
}

export interface AuditIssue {
  severity: 'critical' | 'warning' | 'info'
  category: string
  page: string | null
  message: string
  suggestion: string
}

export interface CategoryScore {
  name: string
  score: number
  max: number
}

export interface AuditReport {
  score: number
  categories: CategoryScore[]
  issues: AuditIssue[]
  machine_checks: MachineCheck[]
  summary: string
}

export interface AppSettings {
  models: Record<string, string>
  theme_accent: string
  api_key: string
  base_url: string
  enabled: Record<string, boolean>
  vision_audit: boolean
  use_photos: boolean
}

export type AgentStatus = 'queued' | 'running' | 'done' | 'error' | 'skipped'

export interface AgentCardState {
  id: string
  status: AgentStatus
  detail?: string
  startedAt?: number
  ms?: number
  fixed?: string[]
}

export type WorkspaceTab = 'preview' | 'code' | 'agents' | 'audit' | 'logs'
export type DeviceWidth = 'mobile' | 'tablet' | 'full'

export interface LogEntry {
  id: number
  agent: string
  text: string
  level: 'info' | 'warn' | 'error'
  t: number
}

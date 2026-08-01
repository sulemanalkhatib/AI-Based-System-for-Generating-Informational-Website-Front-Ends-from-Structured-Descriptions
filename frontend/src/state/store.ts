// Single zustand store. SSE handlers (lib/sse.ts) mutate it from outside the
// React tree, which is exactly what zustand is good at — no stale closures.

import { create } from 'zustand'
import { api } from '../lib/api'
import type {
  AgentCardState,
  AppSettings,
  AuditReport,
  DeviceWidth,
  FileMeta,
  LogEntry,
  Message,
  SessionSummary,
  WorkspaceTab,
} from '../lib/types'

let localMessageId = -1 // negative ids for optimistic messages (never collide with DB ids)

export interface StoreState {
  // sessions + chat
  sessions: SessionSummary[]
  activeSessionId: string | null
  messages: Message[]
  chatBusy: boolean
  streamingText: string
  streamingAgent: string
  hasBrief: boolean

  // build pipeline
  buildId: string | null
  buildStatus: 'idle' | 'running' | 'done' | 'failed'
  agents: Record<string, AgentCardState>
  pages: { filename: string; title: string }[]
  buildError: string | null
  outputPath: string | null
  score: number | null
  audit: AuditReport | null

  // files / editor
  files: FileMeta[]
  fileContents: Record<string, { content: string; revision: number }>
  activeFile: string | null
  dirtyFiles: Record<string, string> // filename -> unsaved content

  // developer console
  devLog: LogEntry[]
  devMode: boolean

  // settings + ui
  settings: AppSettings | null
  modelOptions: string[]
  serverStopped: boolean
  tab: WorkspaceTab
  sidebarCollapsed: boolean
  deviceWidth: DeviceWidth
  previewNonce: number
  previewPage: string
  settingsOpen: boolean

  // actions
  set: (partial: Partial<StoreState>) => void
  upsertAgent: (id: string, patch: Partial<AgentCardState>) => void
  seedAgents: (ids: string[]) => void
  appendMessage: (message: Partial<Message> & { role: Message['role']; content: string }) => void
  upsertFile: (meta: FileMeta) => void
  resetBuildState: () => void
}

export const useStore = create<StoreState>((set) => ({
  sessions: [],
  activeSessionId: null,
  messages: [],
  chatBusy: false,
  streamingText: '',
  streamingAgent: 'interviewer',
  hasBrief: false,

  buildId: null,
  buildStatus: 'idle',
  agents: {},
  pages: [],
  buildError: null,
  outputPath: null,
  score: null,
  audit: null,

  files: [],
  fileContents: {},
  activeFile: null,
  dirtyFiles: {},

  devLog: [],
  devMode:
    typeof localStorage !== 'undefined' ? localStorage.getItem('devMode') !== '0' : true,

  settings: null,
  modelOptions: [],
  serverStopped: false,
  tab: 'preview',
  sidebarCollapsed: false,
  deviceWidth: 'full',
  previewNonce: 0,
  previewPage: 'index.html',
  settingsOpen: false,

  set: (partial) => set(partial),

  upsertAgent: (id, patch) =>
    set((state) => {
      const existing = state.agents[id] ?? { id, status: 'queued' as const }
      return { agents: { ...state.agents, [id]: { ...existing, ...patch, id } } }
    }),

  seedAgents: (ids) =>
    set((state) => {
      const agents = { ...state.agents }
      for (const id of ids) {
        if (!agents[id]) agents[id] = { id, status: 'queued' }
      }
      return { agents }
    }),

  appendMessage: (message) =>
    set((state) => ({
      messages: [
        ...state.messages,
        {
          id: message.id ?? localMessageId--,
          role: message.role,
          agent: message.agent ?? null,
          content: message.content,
          created_at: message.created_at ?? new Date().toISOString(),
        },
      ],
    })),

  upsertFile: (meta) =>
    set((state) => {
      const files = state.files.some((f) => f.filename === meta.filename)
        ? state.files.map((f) => (f.filename === meta.filename ? meta : f))
        : [...state.files, meta].sort((a, b) => a.filename.localeCompare(b.filename))
      // Invalidate any cached content so the editor refetches the new revision
      const fileContents = { ...state.fileContents }
      const cached = fileContents[meta.filename]
      if (cached && cached.revision < meta.revision) delete fileContents[meta.filename]
      return { files, fileContents, previewNonce: state.previewNonce + 1 }
    }),

  resetBuildState: () =>
    set({
      buildStatus: 'running',
      agents: {},
      pages: [],
      devLog: [],
      buildError: null,
      outputPath: null,
      score: null,
      audit: null,
      files: [],
      fileContents: {},
      activeFile: null,
      dirtyFiles: {},
      previewNonce: 0,
      previewPage: 'index.html',
    }),
}))

// ---------------------------------------------------------------- dev console

let logSeq = 0

export function pushLog(agent: string, text: string, level: LogEntry['level'] = 'info'): void {
  useStore.setState((s) => ({
    devLog: [
      ...s.devLog.slice(-599), // cap so a long build can't grow unbounded
      { id: ++logSeq, agent, text, level, t: Date.now() },
    ],
  }))
}

export function toggleDevMode(): void {
  const next = !useStore.getState().devMode
  if (typeof localStorage !== 'undefined') localStorage.setItem('devMode', next ? '1' : '0')
  useStore.setState({ devMode: next })
  if (!next && useStore.getState().tab === 'logs') useStore.setState({ tab: 'preview' })
}

// ---------------------------------------------------------------- thunks

export async function loadSessions(): Promise<void> {
  const sessions = await api.listSessions()
  useStore.setState({ sessions })
}

export async function selectSession(sessionId: string): Promise<void> {
  const { closeStreams } = await import('../lib/sse')
  closeStreams()
  const detail = await api.getSession(sessionId)
  useStore.setState({
    chatBusy: false,
    streamingText: '',
    activeSessionId: sessionId,
    messages: detail.messages,
    hasBrief: detail.session.brief != null,
    buildId: null,
    buildStatus: 'idle',
    agents: {},
    pages: [],
    audit: null,
    files: [],
    fileContents: {},
    activeFile: null,
    dirtyFiles: {},
    outputPath: null,
    score: null,
    buildError: null,
    devLog: [],
    tab: 'preview',
  })
  const latest = detail.builds[0]
  if (latest) {
    const { subscribeBuild } = await import('../lib/sse')
    useStore.setState({ buildId: latest.id, buildStatus: latest.status })
    subscribeBuild(latest.id) // replays history (live bus or DB) into the store
  }
}

export async function newSession(): Promise<void> {
  const session = await api.createSession()
  await loadSessions()
  await selectSession(session.id)
}

export async function loadSettings(): Promise<void> {
  useStore.setState({ settings: await api.getSettings() })
}

export async function startBuild(): Promise<void> {
  const { activeSessionId } = useStore.getState()
  if (!activeSessionId) return
  const { build_id } = await api.startBuild(activeSessionId)
  useStore.getState().resetBuildState()
  useStore.setState({ buildId: build_id, tab: 'agents' })
  const { subscribeBuild } = await import('../lib/sse')
  subscribeBuild(build_id)
}

export async function stopBuild(): Promise<void> {
  const { buildId, buildStatus } = useStore.getState()
  if (buildId && buildStatus === 'running') {
    await api.cancelBuild(buildId).catch(() => undefined)
  }
}

export async function sendChatMessage(content: string): Promise<void> {
  const { activeSessionId, chatBusy } = useStore.getState()
  if (!activeSessionId || chatBusy || !content.trim()) return
  useStore.getState().appendMessage({ role: 'user', content })
  useStore.setState({ chatBusy: true })
  try {
    const { run_id } = await api.sendMessage(activeSessionId, content)
    const { subscribeChatRun } = await import('../lib/sse')
    subscribeChatRun(run_id)
  } catch (error) {
    useStore.setState({ chatBusy: false })
    useStore.getState().appendMessage({
      role: 'system',
      content: `Something went wrong: ${(error as Error).message}`,
    })
  }
}

export async function openFile(filename: string): Promise<void> {
  const { buildId, fileContents } = useStore.getState()
  useStore.setState({ activeFile: filename })
  if (!buildId || fileContents[filename]) return
  const file = await api.getFile(buildId, filename)
  useStore.setState((state) => ({
    fileContents: {
      ...state.fileContents,
      [filename]: { content: file.content, revision: file.revision },
    },
  }))
}

let saveTimer: ReturnType<typeof setTimeout> | null = null

export function editFile(filename: string, content: string): void {
  useStore.setState((state) => ({
    dirtyFiles: { ...state.dirtyFiles, [filename]: content },
  }))
  if (saveTimer) clearTimeout(saveTimer)
  saveTimer = setTimeout(() => void flushFile(filename), 400)
}

async function flushFile(filename: string): Promise<void> {
  const { buildId, dirtyFiles } = useStore.getState()
  const content = dirtyFiles[filename]
  if (!buildId || content === undefined) return
  const { revision } = await api.putFile(buildId, filename, content)
  useStore.setState((state) => {
    const dirty = { ...state.dirtyFiles }
    delete dirty[filename]
    return {
      dirtyFiles: dirty,
      fileContents: {
        ...state.fileContents,
        [filename]: { content, revision },
      },
      files: state.files.map((f) =>
        f.filename === filename ? { ...f, revision, size: content.length } : f),
      previewNonce: state.previewNonce + 1,
    }
  })
}

// SSE clients for chat runs and build runs. Payloads carry a monotonic `seq`;
// EventSource auto-reconnects and the server replays history, so dropping
// anything with seq <= lastSeq makes reconnects idempotent.

import { api } from './api'
import { loadSessions, pushLog, startBuild, useStore } from '../state/store'
import type { AuditReport } from './types'

type Payload = Record<string, unknown> & { seq: number }

function listen(
  source: EventSource,
  handlers: Record<string, (data: Payload) => void>,
): void {
  let lastSeq = 0
  for (const [name, handler] of Object.entries(handlers)) {
    source.addEventListener(name, (event) => {
      const data = JSON.parse((event as MessageEvent).data) as Payload
      if (data.seq <= lastSeq) return
      lastSeq = data.seq
      handler(data)
    })
  }
}

// ---------------------------------------------------------------- chat runs

let chatSource: EventSource | null = null

/** Close any open streams — called when the user switches sessions so a
 *  previous session's run can't keep writing into the store. */
export function closeStreams(): void {
  chatSource?.close()
  chatSource = null
  buildSource?.close()
  buildSource = null
}

export function subscribeChatRun(runId: string): void {
  chatSource?.close()
  const source = new EventSource(`/api/runs/${runId}/stream`)
  chatSource = source

  listen(source, {
    token: (d) =>
      useStore.setState((s) => ({
        streamingText: s.streamingText + (d.text as string),
        streamingAgent: (d.agent as string) || 'interviewer',
      })),

    // Edit runs stream status lines instead of tokens ("Rewriting index.html…")
    agent_status: (d) => {
      const agent = (d.agent as string) || 'editor'
      pushLog(agent, d.text as string)
      useStore.setState({ streamingText: d.text as string, streamingAgent: agent })
    },

    // Edited files land on the same build — refresh tree + preview live
    file_written: (d) => {
      pushLog((d.agent as string) || 'editor',
        `wrote ${d.filename} → r${d.revision} (${(d.size as number).toLocaleString()} bytes)`)
      useStore.getState().upsertFile({
        filename: d.filename as string,
        revision: d.revision as number,
        size: d.size as number,
      })
    },

    message_done: (d) => {
      const agent = useStore.getState().streamingAgent
      useStore.setState({ streamingText: '' })
      useStore.getState().appendMessage({
        role: 'assistant',
        agent: agent || 'interviewer',
        content: d.content as string,
      })
    },

    brief_ready: () => {
      pushLog('interviewer', 'brief ready → starting build')
      useStore.setState({ hasBrief: true })
      void loadSessions() // session was renamed to the business name
      void startBuild() // the interview handing straight off to the pipeline
    },

    error: (d) => {
      pushLog('interviewer', d.message as string, 'error')
      useStore.getState().appendMessage({
        role: 'system',
        content: `Chat error: ${d.message as string}`,
      })
    },

    done: () => {
      source.close()
      useStore.setState({ chatBusy: false, streamingText: '' })
    },
  })

  source.onerror = () => {
    // Auto-reconnect is fine; only a permanently closed stream ends the turn.
    if (source.readyState === EventSource.CLOSED) {
      useStore.setState({ chatBusy: false })
    }
  }
}

// ---------------------------------------------------------------- build runs

let buildSource: EventSource | null = null

const FIXED_STAGES = ['copywriter', 'designer', 'recheck', 'audit']

export function subscribeBuild(buildId: string): void {
  buildSource?.close()
  const source = new EventSource(`/api/builds/${buildId}/stream`)
  buildSource = source
  const store = () => useStore.getState()

  listen(source, {
    run_start: (d) => {
      if (!d.replay) {
        store().seedAgents(FIXED_STAGES)
        pushLog('pipeline', 'build started')
      }
    },

    pages_planned: (d) => {
      const pages = d.pages as { filename: string; title: string }[]
      pushLog('pipeline', `planned ${pages.length} pages: ${pages.map((p) => p.filename).join(', ')}`)
      useStore.setState({ pages })
      store().seedAgents([
        'builder:css',
        ...pages.map((p) => `builder:${p.filename}`),
        'builder:js',
      ])
    },

    agent_start: (d) => {
      pushLog(d.agent as string, `▶ started${d.model ? ` · model ${d.model}` : ''}`)
      store().upsertAgent(d.agent as string, {
        status: 'running',
        startedAt: Date.now(),
        detail: undefined,
      })
    },

    agent_skipped: (d) => {
      pushLog(d.agent as string, 'skipped (disabled in settings)', 'warn')
      store().upsertAgent(d.agent as string, {
        status: 'skipped',
        detail: 'disabled in settings',
      })
    },

    agent_status: (d) => {
      const level = /error|invalid|retry|limit/i.test(d.text as string) ? 'warn' : 'info'
      pushLog(d.agent as string, d.text as string, level)
      store().upsertAgent(d.agent as string, { detail: d.text as string })
    },

    agent_done: (d) => {
      const extra = d.fixed && (d.fixed as string[]).length
        ? ` · fixed ${(d.fixed as string[]).join(', ')}`
        : d.notes ? ` · ${d.notes}` : ''
      pushLog(d.agent as string, `✔ done${d.ms ? ` · ${((d.ms as number) / 1000).toFixed(1)}s` : ''}${extra}`)
      store().upsertAgent(d.agent as string, {
        status: 'done',
        ms: d.ms as number,
        fixed: d.fixed as string[] | undefined,
        detail: d.notes ? (d.notes as string) : undefined,
      })
    },

    file_written: (d) => {
      pushLog((d.agent as string) || 'builder',
        `wrote ${d.filename} → r${d.revision} (${(d.size as number).toLocaleString()} bytes)`)
      store().upsertFile({
        filename: d.filename as string,
        revision: d.revision as number,
        size: d.size as number,
      })
    },

    audit: (d) => {
      const report = d.report as unknown as AuditReport
      pushLog('audit', `report → score ${report.score}/100 · ${report.issues.length} issues · ` +
        `${report.machine_checks.filter((c) => !c.passed).length} machine checks failing`)
      useStore.setState({ audit: report, score: report.score })
    },

    error: (d) => {
      pushLog((d.agent as string) || 'pipeline', d.message as string, 'error')
      if (d.fatal) {
        useStore.setState({ buildStatus: 'failed', buildError: d.message as string })
      }
      if (d.agent) {
        store().upsertAgent(d.agent as string, {
          status: 'error',
          detail: d.message as string,
        })
      }
    },

    done: (d) => {
      const raw = (d.status as string) ?? 'done'
      const status: 'done' | 'failed' = raw === 'done' ? 'done' : 'failed'
      pushLog('pipeline', `build ${raw}${d.score != null ? ` · final score ${d.score}` : ''}`)
      source.close()
      useStore.setState((s) => {
        const agents = { ...s.agents }
        for (const id of Object.keys(agents)) {
          // Success: any card still queued/running is really done (the pipeline
          // couldn't finish otherwise) → all-green view. Stopped/failed: whatever
          // was mid-flight becomes an error marker instead of spinning forever.
          if (status === 'done' && (agents[id].status === 'queued' || agents[id].status === 'running')) {
            agents[id] = { ...agents[id], status: 'done' }
          } else if (status === 'failed' && agents[id].status === 'running') {
            agents[id] = { ...agents[id], status: 'error' }
          }
        }
        return {
          agents,
          buildStatus: status,
          outputPath: (d.output_path as string) || null,
          score: (d.score as number) ?? s.score,
          buildError: raw === 'stopped' ? 'Build stopped by you.' : s.buildError,
        }
      })
      if (status === 'done' && !d.replay) {
        useStore.setState({ tab: 'preview' })
      }
      void refreshAfterBuild()
    },
  })
}

async function refreshAfterBuild(): Promise<void> {
  const { activeSessionId, buildId } = useStore.getState()
  if (buildId) {
    // Safety net: make sure the file list matches the DB exactly
    const files = await api.listFiles(buildId)
    useStore.setState({ files })
  }
  if (activeSessionId) {
    // Pick up the backend's "Build finished — score X/100" chat message
    const detail = await api.getSession(activeSessionId)
    useStore.setState({ messages: detail.messages })
  }
  void loadSessions()
}

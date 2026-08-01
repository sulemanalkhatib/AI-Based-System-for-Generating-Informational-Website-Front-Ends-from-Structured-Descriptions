import { useEffect, useRef, useState } from 'react'
import { Terminal, Trash2 } from 'lucide-react'
import { useStore } from '../../state/store'
import type { LogEntry } from '../../lib/types'

// Stable per-agent color so you can scan the stream by who's talking.
const AGENT_COLORS: Record<string, string> = {
  pipeline: '#a0a0a0',
  interviewer: '#7a8ccc',
  copywriter: '#cc785c',
  designer: '#c9a227',
  recheck: '#5db8a6',
  audit: '#5db872',
  editor: '#d98a6f',
  writer: '#6b6b6b',
}

function colorFor(agent: string): string {
  if (AGENT_COLORS[agent]) return AGENT_COLORS[agent]
  if (agent.startsWith('builder')) return '#b98cff'
  return '#a0a0a0'
}

function stamp(t: number): string {
  const d = new Date(t)
  return (
    `${d.getHours().toString().padStart(2, '0')}:` +
    `${d.getMinutes().toString().padStart(2, '0')}:` +
    `${d.getSeconds().toString().padStart(2, '0')}.` +
    `${d.getMilliseconds().toString().padStart(3, '0')}`
  )
}

function Row({ entry }: { entry: LogEntry }) {
  const textColor =
    entry.level === 'error'
      ? 'text-err'
      : entry.level === 'warn'
        ? 'text-warn'
        : 'text-ink-dim'
  return (
    <div className="flex gap-2 px-3 py-0.5 hover:bg-surface-1">
      <span className="shrink-0 text-ink-mute select-none">{stamp(entry.t)}</span>
      <span
        className="w-28 shrink-0 truncate font-semibold"
        style={{ color: colorFor(entry.agent) }}
        title={entry.agent}
      >
        {entry.agent}
      </span>
      <span className={`min-w-0 break-words ${textColor}`}>{entry.text}</span>
    </div>
  )
}

export function ConsolePane() {
  const log = useStore((s) => s.devLog)
  const [autoscroll, setAutoscroll] = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (autoscroll) bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [log.length, autoscroll])

  return (
    <div className="flex h-full flex-col bg-inset">
      <div className="flex h-10 shrink-0 items-center justify-between border-b border-edge px-3">
        <div className="flex items-center gap-2 text-[12px] text-ink-dim">
          <Terminal size={14} className="text-accent" aria-hidden />
          <span>Developer console</span>
          <span className="text-ink-mute">· {log.length} events</span>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex cursor-pointer items-center gap-1.5 text-[11.5px] text-ink-mute">
            <input
              type="checkbox"
              checked={autoscroll}
              onChange={(e) => setAutoscroll(e.target.checked)}
              className="accent-[var(--color-accent)]"
            />
            auto-scroll
          </label>
          <button
            onClick={() => useStore.setState({ devLog: [] })}
            className="flex cursor-pointer items-center gap-1 rounded-sm px-1.5 py-1 text-[11.5px] text-ink-mute transition-colors duration-150 hover:bg-surface-2 hover:text-ink"
          >
            <Trash2 size={12} aria-hidden />
            clear
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto py-1 font-mono text-[11.5px] leading-relaxed">
        {log.length === 0 ? (
          <p className="px-3 py-6 text-center text-ink-mute">
            No activity yet. Every agent request, response, retry, and file write
            will stream here as the pipeline runs.
          </p>
        ) : (
          log.map((entry) => <Row key={entry.id} entry={entry} />)
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

import { useEffect, useState } from 'react'
import {
  Ban,
  Check,
  CircleDashed,
  FileCode2,
  Hammer,
  LoaderCircle,
  Palette,
  PenLine,
  Braces,
  SearchCheck,
  ShieldCheck,
  X,
} from 'lucide-react'
import type { AgentCardState } from '../../lib/types'

function iconFor(id: string) {
  if (id === 'copywriter') return PenLine
  if (id === 'designer') return Palette
  if (id === 'builder:css') return Braces
  if (id === 'builder:js') return FileCode2
  if (id.startsWith('builder')) return Hammer
  if (id === 'recheck') return SearchCheck
  return ShieldCheck
}

function labelFor(id: string): string {
  if (id === 'copywriter') return 'Copywriter'
  if (id === 'designer') return 'Designer'
  if (id === 'builder') return 'Builder'
  if (id === 'builder:css') return 'Stylesheet'
  if (id === 'builder:js') return 'Site script'
  if (id.startsWith('builder:')) return id.slice('builder:'.length)
  if (id === 'recheck') return 'Recheck'
  return 'Audit'
}

function Elapsed({ since }: { since: number }) {
  const [, tick] = useState(0)
  useEffect(() => {
    const timer = setInterval(() => tick((n) => n + 1), 1000)
    return () => clearInterval(timer)
  }, [])
  const seconds = Math.max(0, Math.round((Date.now() - since) / 1000))
  return <span>{seconds}s</span>
}

export function AgentCard({ agent }: { agent: AgentCardState }) {
  const Icon = iconFor(agent.id)
  const running = agent.status === 'running'

  return (
    <div
      className={`flex min-w-0 items-center gap-2.5 rounded-md border bg-surface-2 px-3 py-2.5 transition-colors duration-200 ${
        running
          ? 'agent-running border-transparent'
          : agent.status === 'error'
            ? 'border-err/40'
            : 'border-edge'
      } ${agent.status === 'skipped' ? 'opacity-55' : ''}`}
    >
      <Icon
        size={16}
        className={`shrink-0 ${running ? 'text-accent' : 'text-ink-mute'}`}
        aria-hidden
      />
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <span className="truncate text-[13px] font-medium text-ink">
            {labelFor(agent.id)}
          </span>
          <span className="shrink-0 text-[11px] text-ink-mute">
            {running && agent.startedAt && <Elapsed since={agent.startedAt} />}
            {agent.status === 'done' && agent.ms != null && `${(agent.ms / 1000).toFixed(1)}s`}
          </span>
        </div>
        {(agent.detail || agent.fixed) && (
          <p className="truncate text-[11.5px] text-ink-mute">
            {agent.fixed && agent.fixed.length > 0
              ? `fixed ${agent.fixed.join(', ')}`
              : agent.detail}
          </p>
        )}
      </div>
      <span className="shrink-0" aria-label={agent.status}>
        {agent.status === 'queued' && (
          <CircleDashed size={15} className="text-ink-mute" aria-hidden />
        )}
        {running && <LoaderCircle size={15} className="spin text-accent" aria-hidden />}
        {agent.status === 'done' && <Check size={15} className="text-ok" aria-hidden />}
        {agent.status === 'error' && <X size={15} className="text-err" aria-hidden />}
        {agent.status === 'skipped' && <Ban size={15} className="text-ink-mute" aria-hidden />}
      </span>
    </div>
  )
}

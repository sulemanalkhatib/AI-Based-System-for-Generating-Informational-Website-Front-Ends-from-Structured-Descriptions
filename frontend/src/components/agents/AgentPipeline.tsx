import type { ReactNode } from 'react'
import { Bot } from 'lucide-react'
import { AgentCard } from './AgentCard'
import { useStore } from '../../state/store'
import type { AgentCardState, AgentStatus } from '../../lib/types'

type StageStatus = 'queued' | 'running' | 'done' | 'error'

function stageStatus(agents: AgentCardState[]): StageStatus {
  if (agents.some((a) => a.status === 'running')) return 'running'
  if (agents.some((a) => a.status === 'error')) return 'error'
  if (agents.length > 0 && agents.every((a) => a.status === 'done' || a.status === 'skipped'))
    return 'done'
  return 'queued'
}

const DOT: Record<StageStatus, string> = {
  done: 'border-accent bg-accent',
  running: 'agent-running border-accent bg-canvas',
  error: 'border-err bg-err',
  queued: 'border-edge-3 bg-surface-2',
}

// One node on the vertical timeline: an aligned rail + a state-coloured dot,
// its label, and the row's cards. `last` drops the connector below the node.
function TimelineRow({
  label,
  status,
  last = false,
  children,
}: {
  label: string
  status: StageStatus
  last?: boolean
  children: ReactNode
}) {
  return (
    <div className="relative pb-7 pl-8 last:pb-1">
      {!last && (
        <span
          className="absolute top-2 bottom-0 left-[10px] w-0.5 bg-edge-2"
          aria-hidden
        />
      )}
      <span
        className={`absolute top-[3px] left-1 h-3.5 w-3.5 rounded-full border-2 ${DOT[status]}`}
        aria-hidden
      />
      <p className="mb-2.5 text-[11px] font-semibold tracking-wider text-ink-mute uppercase">
        {label}
      </p>
      {children}
    </div>
  )
}

function cardGrid(agents: AgentCardState[], columns: 1 | 3 = 3) {
  return (
    <div
      className={`grid gap-2 ${
        columns === 1 ? 'grid-cols-1' : 'grid-cols-1 md:grid-cols-2 xl:grid-cols-3'
      }`}
    >
      {agents.map((agent) => (
        <AgentCard key={agent.id} agent={agent} />
      ))}
    </div>
  )
}

export function AgentPipeline() {
  const agents = useStore((s) => s.agents)
  const pages = useStore((s) => s.pages)
  const buildStatus = useStore((s) => s.buildStatus)
  const buildError = useStore((s) => s.buildError)
  const outputPath = useStore((s) => s.outputPath)

  if (Object.keys(agents).length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-center">
        <Bot size={28} className="mb-3 text-ink-mute" aria-hidden />
        <p className="text-sm font-medium text-ink-dim">The team is on standby</p>
        <p className="mt-1 max-w-72 text-[12.5px] text-ink-mute">
          When the interview finishes, you'll watch the copywriter and designer
          work in parallel, then every page build live here.
        </p>
      </div>
    )
  }

  const specialists = [agents.copywriter, agents.designer].filter(
    (a): a is AgentCardState => a != null,
  )
  const builderAgents = [
    agents['builder:css'],
    ...pages.map((p) => agents[`builder:${p.filename}`]),
    agents['builder:js'],
  ].filter((a): a is AgentCardState => a != null)
  const review = [agents.audit, agents.recheck].filter(
    (a): a is AgentCardState => a != null,
  )
  const builderExpanded = builderAgents.length > 0

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-3xl">
        {specialists.length > 0 && (
          <TimelineRow label="1 · Specialists — in parallel" status={stageStatus(specialists)}>
            {cardGrid(specialists)}
          </TimelineRow>
        )}

        {builderExpanded ? (
          <TimelineRow
            label={`2 · Builder — stylesheet, then pages (${pages.length}) + script in parallel`}
            status={stageStatus(builderAgents)}
          >
            {agents['builder:css'] && (
              <div className="mb-2">
                <AgentCard agent={agents['builder:css']} />
              </div>
            )}
            {cardGrid(
              [...pages.map((p) => agents[`builder:${p.filename}`]), agents['builder:js']].filter(
                (a): a is AgentCardState => a != null,
              ),
            )}
          </TimelineRow>
        ) : (
          <TimelineRow label="2 · Builder" status="queued">
            {cardGrid([{ id: 'builder', status: 'queued' as AgentStatus }], 1)}
          </TimelineRow>
        )}

        {review.length > 0 && (
          <TimelineRow
            label="3 · Review loop — audit scores, recheck fixes, re-audit"
            status={stageStatus(review)}
            last
          >
            {cardGrid(review)}
          </TimelineRow>
        )}

        {buildStatus === 'failed' && buildError && (
          <p className="mt-3 rounded-md border border-err/40 bg-err/10 px-3 py-2 text-[12.5px] text-err">
            Build failed: {buildError}
          </p>
        )}
        {buildStatus === 'done' && outputPath && (
          <p className="mt-3 rounded-md border border-edge bg-surface-2 px-3 py-2 text-[12.5px] text-ink-dim">
            Files saved to <span className="font-mono text-ink">{outputPath}</span>
          </p>
        )}
      </div>
    </div>
  )
}

import { Bot, CircleStop, Code2, Eye, Hammer, LoaderCircle, ShieldCheck, Terminal } from 'lucide-react'
import { PreviewPane } from '../preview/PreviewPane'
import { CodePane } from '../code/CodePane'
import { AgentPipeline } from '../agents/AgentPipeline'
import { AuditPanel } from '../audit/AuditPanel'
import { ConsolePane } from '../console/ConsolePane'
import { startBuild, stopBuild, useStore } from '../../state/store'
import type { WorkspaceTab } from '../../lib/types'

const TABS: { id: WorkspaceTab; label: string; icon: typeof Eye }[] = [
  { id: 'preview', label: 'Preview', icon: Eye },
  { id: 'code', label: 'Code', icon: Code2 },
  { id: 'agents', label: 'Agents', icon: Bot },
  { id: 'audit', label: 'Audit', icon: ShieldCheck },
  { id: 'logs', label: 'Logs', icon: Terminal },
]

export function Workspace() {
  const tab = useStore((s) => s.tab)
  const set = useStore((s) => s.set)
  const buildStatus = useStore((s) => s.buildStatus)
  const hasBrief = useStore((s) => s.hasBrief)
  const score = useStore((s) => s.score)
  const devMode = useStore((s) => s.devMode)
  const logCount = useStore((s) => s.devLog.length)
  const tabs = devMode ? TABS : TABS.filter((t) => t.id !== 'logs')

  return (
    <section className="flex h-full min-w-0 flex-1 flex-col bg-canvas">
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-edge px-3">
        <nav className="flex gap-1" aria-label="Workspace tabs">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => set({ tab: id })}
              className={`relative flex cursor-pointer items-center gap-1.5 rounded-sm px-3 py-1.5 text-[13px] font-medium transition-colors duration-150 ${
                tab === id
                  ? 'bg-surface-2 text-ink'
                  : 'text-ink-mute hover:bg-surface-1 hover:text-ink-dim'
              }`}
            >
              <Icon size={14} aria-hidden />
              {label}
              {id === 'agents' && buildStatus === 'running' && (
                <span className="ml-0.5 inline-block h-1.5 w-1.5 rounded-full bg-accent" />
              )}
              {id === 'audit' && score != null && (
                <span className="ml-0.5 rounded-full bg-accent-tint px-1.5 text-[11px] font-semibold text-accent">
                  {score}
                </span>
              )}
              {id === 'logs' && buildStatus === 'running' && logCount > 0 && (
                <span className="ml-0.5 inline-block h-1.5 w-1.5 rounded-full bg-accent" />
              )}
            </button>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          {buildStatus === 'running' && (
            <>
              <span className="flex items-center gap-1.5 text-[12px] text-ink-dim">
                <LoaderCircle size={13} className="spin text-accent" aria-hidden />
                Agents working…
              </span>
              <button
                onClick={() => void stopBuild()}
                className="flex cursor-pointer items-center gap-1.5 rounded-sm border border-err/40 px-3 py-1.5 text-[13px] font-medium text-err transition-colors duration-200 hover:bg-err/10"
              >
                <CircleStop size={13} aria-hidden />
                Stop
              </button>
            </>
          )}
          {buildStatus === 'failed' && (
            <span className="text-[12px] text-err">Build failed</span>
          )}
          {hasBrief && buildStatus !== 'running' && (
            <button
              onClick={() => void startBuild()}
              className="flex cursor-pointer items-center gap-1.5 rounded-sm bg-accent px-3 py-1.5 text-[13px] font-medium text-white transition-colors duration-200 hover:bg-accent-hover"
            >
              <Hammer size={13} aria-hidden />
              {buildStatus === 'idle' ? 'Build website' : 'Rebuild'}
            </button>
          )}
        </div>
      </header>

      <div className="min-h-0 flex-1">
        {tab === 'preview' && <PreviewPane />}
        {tab === 'code' && <CodePane />}
        {tab === 'agents' && <AgentPipeline />}
        {tab === 'audit' && <AuditPanel />}
        {tab === 'logs' && <ConsolePane />}
      </div>
    </section>
  )
}

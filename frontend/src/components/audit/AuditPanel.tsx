import { Check, ShieldCheck, X } from 'lucide-react'
import { ScoreRing } from './ScoreRing'
import { IssueList } from './IssueList'
import { useStore } from '../../state/store'

export function AuditPanel() {
  const audit = useStore((s) => s.audit)
  const buildStatus = useStore((s) => s.buildStatus)

  if (!audit) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-center">
        <ShieldCheck size={28} className="mb-3 text-ink-mute" aria-hidden />
        <p className="text-sm font-medium text-ink-dim">
          {buildStatus === 'running' ? 'Audit runs last…' : 'No audit yet'}
        </p>
        <p className="mt-1 max-w-64 text-[12.5px] text-ink-mute">
          After the recheck agent fixes the code, an independent auditor scores
          the site and lists every issue it finds.
        </p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto p-6">
      <div className="mx-auto max-w-3xl">
        <div className="flex flex-wrap items-center gap-6 rounded-md border border-edge bg-surface-2 p-5">
          <ScoreRing score={audit.score} />
          <div className="min-w-56 flex-1">
            <p className="mb-3 text-[13.5px] leading-relaxed text-ink-dim">{audit.summary}</p>
            <div className="space-y-2">
              {audit.categories.map((category) => (
                <div key={category.name}>
                  <div className="mb-0.5 flex justify-between text-[11.5px]">
                    <span className="text-ink-dim">{category.name}</span>
                    <span className="text-ink-mute">
                      {category.score}/{category.max}
                    </span>
                  </div>
                  <div className="h-1.5 overflow-hidden rounded-full bg-surface-3">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{ width: `${(category.score / category.max) * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <h2 className="mt-6 mb-2 text-[11px] font-semibold tracking-wider text-ink-mute uppercase">
          Machine checks
        </h2>
        <ul className="grid grid-cols-1 gap-1.5 md:grid-cols-2">
          {audit.machine_checks.map((check) => (
            <li
              key={check.name}
              className="flex items-start gap-2 rounded-sm border border-edge bg-surface-1 px-3 py-2"
            >
              {check.passed ? (
                <Check size={14} className="mt-0.5 shrink-0 text-ok" aria-hidden />
              ) : (
                <X size={14} className="mt-0.5 shrink-0 text-err" aria-hidden />
              )}
              <div className="min-w-0">
                <p className="text-[12.5px] text-ink">{check.name}</p>
                {check.detail && (
                  <p className="truncate text-[11.5px] text-ink-mute">{check.detail}</p>
                )}
              </div>
            </li>
          ))}
        </ul>

        <h2 className="mt-6 mb-2 text-[11px] font-semibold tracking-wider text-ink-mute uppercase">
          Issues ({audit.issues.length})
        </h2>
        <IssueList issues={audit.issues} />
      </div>
    </div>
  )
}

import type { AuditIssue } from '../../lib/types'

const SEVERITY_STYLE: Record<AuditIssue['severity'], string> = {
  critical: 'bg-err/15 text-err',
  warning: 'bg-warn/15 text-warn',
  info: 'bg-surface-3 text-ink-dim',
}

export function IssueList({ issues }: { issues: AuditIssue[] }) {
  if (issues.length === 0) {
    return <p className="text-[13px] text-ink-mute">No issues reported. 🎉</p>
  }
  return (
    <ul className="space-y-2">
      {issues.map((issue, index) => (
        <li key={index} className="rounded-md border border-edge bg-surface-2 px-3.5 py-3">
          <div className="mb-1 flex flex-wrap items-center gap-2">
            <span
              className={`rounded-full px-2 py-0.5 text-[10.5px] font-semibold tracking-wide uppercase ${SEVERITY_STYLE[issue.severity]}`}
            >
              {issue.severity}
            </span>
            <span className="text-[11.5px] text-ink-mute">{issue.category}</span>
            {issue.page && (
              <span className="font-mono text-[11.5px] text-ink-mute">{issue.page}</span>
            )}
          </div>
          <p className="text-[13px] text-ink">{issue.message}</p>
          {issue.suggestion && (
            <p className="mt-1 text-[12.5px] text-ink-dim">
              <span className="text-ink-mute">Fix: </span>
              {issue.suggestion}
            </p>
          )}
        </li>
      ))}
    </ul>
  )
}

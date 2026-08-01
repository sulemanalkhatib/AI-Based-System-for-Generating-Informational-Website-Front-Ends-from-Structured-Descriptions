import { Braces, FileCode2, FileText } from 'lucide-react'
import { openFile, useStore } from '../../state/store'

function iconFor(filename: string) {
  if (filename.endsWith('.css')) return Braces
  if (filename.endsWith('.js')) return FileCode2
  return FileText
}

export function FileTree() {
  const files = useStore((s) => s.files)
  const activeFile = useStore((s) => s.activeFile)
  const dirtyFiles = useStore((s) => s.dirtyFiles)

  return (
    <nav
      className="h-full w-52 shrink-0 overflow-y-auto border-r border-edge bg-surface-1 py-2"
      aria-label="Site files"
    >
      <p className="px-3 pb-1.5 text-[11px] font-semibold tracking-wider text-ink-mute uppercase">
        Files
      </p>
      {files.length === 0 && (
        <p className="px-3 py-2 text-[12px] text-ink-mute">No files yet</p>
      )}
      {files.map((file) => {
        const Icon = iconFor(file.filename)
        const active = file.filename === activeFile
        const dirty = dirtyFiles[file.filename] !== undefined
        return (
          <button
            key={file.filename}
            onClick={() => void openFile(file.filename)}
            className={`flex w-full cursor-pointer items-center gap-2 px-3 py-1.5 text-left text-[12.5px] transition-colors duration-150 ${
              active
                ? 'bg-accent-tint text-ink'
                : 'text-ink-dim hover:bg-surface-2 hover:text-ink'
            }`}
          >
            <Icon size={14} className="shrink-0 text-ink-mute" aria-hidden />
            <span className="min-w-0 flex-1 truncate font-mono">{file.filename}</span>
            {dirty && (
              <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-warn" title="Unsaved changes" />
            )}
            {file.revision > 1 && (
              <span
                className="shrink-0 rounded-full bg-surface-3 px-1.5 text-[10px] font-semibold text-accent"
                title={`Revision ${file.revision} — edited after generation`}
              >
                r{file.revision}
              </span>
            )}
          </button>
        )
      })}
    </nav>
  )
}

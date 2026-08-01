import { Download, FolderOpen } from 'lucide-react'
import { FileTree } from './FileTree'
import { EditorPane } from './EditorPane'
import { api } from '../../lib/api'
import { useStore } from '../../state/store'

export function CodePane() {
  const buildId = useStore((s) => s.buildId)
  const files = useStore((s) => s.files)

  if (!buildId || files.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-[13px] text-ink-mute">
        Generated files will appear here once the builders start writing.
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-11 shrink-0 items-center justify-end gap-2 border-b border-edge px-3">
        <a
          href={`/api/builds/${buildId}/export.zip`}
          download
          className="flex cursor-pointer items-center gap-1.5 rounded-sm border border-edge-2 bg-surface-2 px-2.5 py-1.5 text-[12.5px] text-ink-dim transition-colors duration-200 hover:border-accent hover:text-accent"
        >
          <Download size={13} aria-hidden />
          Download zip
        </a>
        <button
          onClick={() => void api.exportToDesktop(buildId)}
          className="flex cursor-pointer items-center gap-1.5 rounded-sm border border-edge-2 bg-surface-2 px-2.5 py-1.5 text-[12.5px] text-ink-dim transition-colors duration-200 hover:border-accent hover:text-accent"
        >
          <FolderOpen size={13} aria-hidden />
          Save to Desktop
        </button>
      </div>
      <div className="flex min-h-0 flex-1">
        <FileTree />
        <EditorPane />
      </div>
    </div>
  )
}

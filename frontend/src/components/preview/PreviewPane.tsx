import { ExternalLink, Globe, Monitor, RefreshCw, Smartphone, Tablet } from 'lucide-react'
import { useStore } from '../../state/store'
import type { DeviceWidth } from '../../lib/types'

const WIDTHS: { id: DeviceWidth; label: string; icon: typeof Monitor; css: string }[] = [
  { id: 'mobile', label: 'Mobile (375px)', icon: Smartphone, css: 'w-[375px]' },
  { id: 'tablet', label: 'Tablet (768px)', icon: Tablet, css: 'w-[768px]' },
  { id: 'full', label: 'Desktop (full width)', icon: Monitor, css: 'w-full' },
]

export function PreviewPane() {
  const buildId = useStore((s) => s.buildId)
  const files = useStore((s) => s.files)
  const nonce = useStore((s) => s.previewNonce)
  const page = useStore((s) => s.previewPage)
  const device = useStore((s) => s.deviceWidth)
  const buildStatus = useStore((s) => s.buildStatus)
  const set = useStore((s) => s.set)

  const htmlFiles = files.filter((f) => f.filename.endsWith('.html'))
  const currentPage = htmlFiles.some((f) => f.filename === page)
    ? page
    : htmlFiles[0]?.filename
  const src = buildId && currentPage ? `/preview/${buildId}/${currentPage}?v=${nonce}` : null
  const widthCss = WIDTHS.find((w) => w.id === device)?.css ?? 'w-full'

  return (
    <div className="flex h-full flex-col">
      <div className="flex h-11 shrink-0 items-center justify-between border-b border-edge px-3">
        <div className="flex items-center gap-2">
          <label htmlFor="preview-page" className="sr-only">
            Page
          </label>
          <select
            id="preview-page"
            value={currentPage ?? ''}
            onChange={(event) => set({ previewPage: event.target.value })}
            disabled={htmlFiles.length === 0}
            className="cursor-pointer rounded-sm border border-edge-2 bg-surface-2 px-2 py-1 text-[12.5px] text-ink outline-none disabled:opacity-40"
          >
            {htmlFiles.map((f) => (
              <option key={f.filename} value={f.filename}>
                {f.filename}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-1">
          <div className="mr-1 flex rounded-sm border border-edge-2 bg-surface-2 p-0.5">
            {WIDTHS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => set({ deviceWidth: id })}
                className={`cursor-pointer rounded-[5px] p-1.5 transition-colors duration-150 ${
                  device === id
                    ? 'bg-surface-3 text-accent'
                    : 'text-ink-mute hover:text-ink-dim'
                }`}
                aria-label={label}
                title={label}
              >
                <Icon size={14} aria-hidden />
              </button>
            ))}
          </div>
          <button
            onClick={() => set({ previewNonce: nonce + 1 })}
            disabled={!src}
            className="cursor-pointer rounded-sm p-1.5 text-ink-mute transition-colors duration-150 hover:bg-surface-2 hover:text-ink disabled:opacity-40"
            aria-label="Refresh preview"
            title="Refresh"
          >
            <RefreshCw size={14} aria-hidden />
          </button>
          <button
            onClick={() => src && window.open(src.split('?')[0], '_blank')}
            disabled={!src}
            className="cursor-pointer rounded-sm p-1.5 text-ink-mute transition-colors duration-150 hover:bg-surface-2 hover:text-ink disabled:opacity-40"
            aria-label="Open preview in new tab"
            title="Open in new tab"
          >
            <ExternalLink size={14} aria-hidden />
          </button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 justify-center overflow-auto bg-inset p-3">
        {src ? (
          <div
            className={`${widthCss} h-full max-w-full overflow-hidden rounded-md border border-edge-2 bg-white transition-[width] duration-300`}
          >
            <iframe
              key={`${currentPage}-${nonce}`}
              src={src}
              title="Website preview"
              sandbox="allow-scripts allow-forms allow-popups"
              className="h-full w-full border-0"
            />
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center text-center">
            <Globe size={28} className="mb-3 text-ink-mute" aria-hidden />
            <p className="text-sm font-medium text-ink-dim">
              {buildStatus === 'running'
                ? 'Waiting for the first page…'
                : 'No website yet'}
            </p>
            <p className="mt-1 max-w-64 text-[12.5px] text-ink-mute">
              {buildStatus === 'running'
                ? 'Pages appear here the moment each builder finishes.'
                : 'Finish the interview on the left and the site will assemble here live.'}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}

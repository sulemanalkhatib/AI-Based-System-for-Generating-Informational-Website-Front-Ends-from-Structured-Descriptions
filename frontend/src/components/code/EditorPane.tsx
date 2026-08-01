import Editor from '@monaco-editor/react'
import { Check, LoaderCircle } from 'lucide-react'
import { editFile, useStore } from '../../state/store'

function languageFor(filename: string): string {
  if (filename.endsWith('.css')) return 'css'
  if (filename.endsWith('.js')) return 'javascript'
  if (filename.endsWith('.json')) return 'json'
  return 'html'
}

export function EditorPane() {
  const activeFile = useStore((s) => s.activeFile)
  const cached = useStore((s) => (s.activeFile ? s.fileContents[s.activeFile] : undefined))
  const dirty = useStore((s) =>
    s.activeFile ? s.dirtyFiles[s.activeFile] !== undefined : false,
  )
  const value = useStore((s) =>
    s.activeFile ? (s.dirtyFiles[s.activeFile] ?? s.fileContents[s.activeFile]?.content) : undefined,
  )

  if (!activeFile) {
    return (
      <div className="flex h-full flex-1 items-center justify-center text-[13px] text-ink-mute">
        Select a file to edit — changes refresh the preview automatically.
      </div>
    )
  }

  return (
    <div className="flex min-w-0 flex-1 flex-col">
      <div className="flex h-9 shrink-0 items-center justify-between border-b border-edge bg-surface-1 px-3">
        <span className="font-mono text-[12px] text-ink-dim">{activeFile}</span>
        <span className="flex items-center gap-1.5 text-[11.5px] text-ink-mute">
          {dirty ? (
            <>
              <LoaderCircle size={12} className="spin" aria-hidden /> saving…
            </>
          ) : (
            <>
              <Check size={12} className="text-ok" aria-hidden />
              saved{cached ? ` · r${cached.revision}` : ''}
            </>
          )}
        </span>
      </div>
      <div className="min-h-0 flex-1">
        <Editor
          path={activeFile}
          language={languageFor(activeFile)}
          value={value ?? '// loading…'}
          onChange={(next) => {
            if (next !== undefined && activeFile) editFile(activeFile, next)
          }}
          theme="app-dark"
          beforeMount={(monaco) => {
            monaco.editor.defineTheme('app-dark', {
              base: 'vs-dark',
              inherit: true,
              rules: [],
              colors: {
                'editor.background': '#141414',
                'editor.lineHighlightBackground': '#1a1a1a',
                'editorLineNumber.foreground': '#6b6b6b',
                'editorGutter.background': '#141414',
                'editor.selectionBackground': '#cc785c40',
              },
            })
          }}
          options={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 13,
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            padding: { top: 10 },
            renderLineHighlight: 'line',
            automaticLayout: true,
          }}
        />
      </div>
    </div>
  )
}

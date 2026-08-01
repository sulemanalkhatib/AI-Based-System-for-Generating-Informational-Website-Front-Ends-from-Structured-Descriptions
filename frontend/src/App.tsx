import { useEffect } from 'react'
import type { CSSProperties } from 'react'
import { SessionSidebar } from './components/sidebar/SessionSidebar'
import { ChatPanel } from './components/chat/ChatPanel'
import { Workspace } from './components/workspace/Workspace'
import { SettingsModal } from './components/settings/SettingsModal'
import {
  loadSessions,
  loadSettings,
  newSession,
  selectSession,
  useStore,
} from './state/store'
import { api } from './lib/api'

let bootstrapped = false // StrictMode double-runs effects in dev; init once

export default function App() {
  const accent = useStore((s) => s.settings?.theme_accent) ?? '#cc785c'
  const serverStopped = useStore((s) => s.serverStopped)

  useEffect(() => {
    if (bootstrapped) return
    bootstrapped = true
    void (async () => {
      await loadSettings().catch(() => undefined)
      const sessions = await api.listSessions().catch(() => [])
      useStore.setState({ sessions })
      if (sessions.length > 0) {
        await selectSession(sessions[0].id)
      } else {
        await newSession()
      }
      await loadSessions()
    })()
  }, [])

  if (serverStopped) {
    return (
      <div className="flex h-full flex-col items-center justify-center bg-canvas text-center">
        <p className="text-[17px] font-semibold text-ink">Server stopped</p>
        <p className="mt-2 max-w-xs text-[13px] leading-relaxed text-ink-mute">
          The local server has been shut down. You can close this tab — run
          <span className="mx-1 font-mono text-ink-dim">start.bat</span>
          whenever you want it back.
        </p>
      </div>
    )
  }

  return (
    <div
      className="flex h-full overflow-hidden bg-canvas text-ink"
      style={{ '--color-accent': accent } as CSSProperties}
    >
      <SessionSidebar />
      <ChatPanel />
      <Workspace />
      <SettingsModal />
    </div>
  )
}

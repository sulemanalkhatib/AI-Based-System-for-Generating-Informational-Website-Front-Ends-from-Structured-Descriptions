import { PanelLeftClose, PanelLeftOpen, Plus, Power, Settings, Sparkles, Trash2 } from 'lucide-react'
import { api } from '../../lib/api'
import { loadSessions, newSession, selectSession, useStore } from '../../state/store'

export function SessionSidebar() {
  const sessions = useStore((s) => s.sessions)
  const activeId = useStore((s) => s.activeSessionId)
  const collapsed = useStore((s) => s.sidebarCollapsed)
  const set = useStore((s) => s.set)

  const remove = async (id: string) => {
    await api.deleteSession(id)
    await loadSessions()
    const remaining = useStore.getState().sessions
    if (id === activeId) {
      if (remaining.length > 0) await selectSession(remaining[0].id)
      else await newSession()
    }
  }

  return (
    <aside
      className={`flex h-full shrink-0 flex-col border-r border-edge bg-surface-1 transition-[width] duration-200 ${
        collapsed ? 'w-14' : 'w-64'
      }`}
    >
      <div className="flex h-14 items-center justify-between px-3">
        {!collapsed && (
          <div className="flex items-center gap-2 overflow-hidden">
            <Sparkles size={18} className="shrink-0 text-accent" aria-hidden />
            <span className="truncate text-sm font-semibold">Website Generator</span>
          </div>
        )}
        <button
          onClick={() => set({ sidebarCollapsed: !collapsed })}
          className="cursor-pointer rounded-sm p-1.5 text-ink-mute transition-colors duration-200 hover:bg-surface-3 hover:text-ink"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <PanelLeftOpen size={17} /> : <PanelLeftClose size={17} />}
        </button>
      </div>

      <div className="px-2.5 pb-2">
        <button
          onClick={() => void newSession()}
          className={`flex w-full cursor-pointer items-center justify-center gap-2 rounded-sm border border-edge-2 bg-surface-2 py-2 text-sm font-medium transition-colors duration-200 hover:border-accent hover:text-accent ${
            collapsed ? 'px-0' : 'px-3'
          }`}
          aria-label="New website"
        >
          <Plus size={16} aria-hidden />
          {!collapsed && <span>New website</span>}
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2.5" aria-label="Sessions">
        {!collapsed &&
          sessions.map((session) => (
            <div
              key={session.id}
              className={`group mb-0.5 flex items-center rounded-sm transition-colors duration-150 ${
                session.id === activeId
                  ? 'bg-accent-tint text-ink'
                  : 'text-ink-dim hover:bg-surface-2'
              }`}
            >
              <button
                onClick={() => void selectSession(session.id)}
                className="min-w-0 flex-1 cursor-pointer px-3 py-2 text-left"
              >
                <span className="block truncate text-[13px]">{session.title}</span>
              </button>
              <button
                onClick={() => void remove(session.id)}
                className="mr-1 hidden cursor-pointer rounded-sm p-1.5 text-ink-mute transition-colors duration-150 hover:text-err group-hover:block"
                aria-label={`Delete ${session.title}`}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
      </nav>

      <div className="border-t border-edge p-2.5">
        <button
          onClick={() => set({ settingsOpen: true })}
          className={`flex w-full cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-sm text-ink-dim transition-colors duration-200 hover:bg-surface-2 hover:text-ink ${
            collapsed ? 'justify-center px-0' : ''
          }`}
          aria-label="Settings"
        >
          <Settings size={16} aria-hidden />
          {!collapsed && <span>Settings</span>}
        </button>
        <button
          onClick={() => {
            if (!window.confirm('Stop the local server? The app will go offline.')) return
            void api
              .shutdown()
              .catch(() => undefined)
              .then(() => set({ serverStopped: true }))
          }}
          className={`flex w-full cursor-pointer items-center gap-2 rounded-sm px-3 py-2 text-sm text-ink-dim transition-colors duration-200 hover:bg-surface-2 hover:text-err ${
            collapsed ? 'justify-center px-0' : ''
          }`}
          aria-label="Stop server"
        >
          <Power size={16} aria-hidden />
          {!collapsed && <span>Stop server</span>}
        </button>
      </div>
    </aside>
  )
}

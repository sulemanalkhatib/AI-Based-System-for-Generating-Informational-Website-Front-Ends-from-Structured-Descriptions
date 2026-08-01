import { MessageList } from './MessageList'
import { Composer } from './Composer'
import { useStore } from '../../state/store'

export function ChatPanel() {
  const title = useStore(
    (s) => s.sessions.find((x) => x.id === s.activeSessionId)?.title ?? 'New website',
  )

  return (
    <section className="flex h-full w-[420px] shrink-0 flex-col border-r border-edge bg-surface-1 xl:w-[440px]">
      <header className="flex h-14 shrink-0 items-center border-b border-edge px-4">
        <h1 className="truncate text-sm font-semibold">{title}</h1>
      </header>
      <MessageList />
      <Composer />
    </section>
  )
}

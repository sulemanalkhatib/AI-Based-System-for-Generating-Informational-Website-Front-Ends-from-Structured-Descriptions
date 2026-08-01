import { useEffect, useRef } from 'react'
import { useStore } from '../../state/store'

const ROLE_LABEL: Record<string, string> = {
  user: 'You',
  assistant: 'Interviewer',
  system: 'System',
}

export function MessageList() {
  const messages = useStore((s) => s.messages)
  const streamingText = useStore((s) => s.streamingText)
  const streamingAgent = useStore((s) => s.streamingAgent)
  const chatBusy = useStore((s) => s.chatBusy)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages.length, streamingText, chatBusy])

  return (
    <div className="flex-1 overflow-y-auto px-4 py-4">
      {messages.length === 0 && !chatBusy && (
        <div className="mt-16 px-2 text-center">
          <p className="text-[15px] font-medium text-ink">
            Tell me about your business.
          </p>
          <p className="mt-2 text-[13px] leading-relaxed text-ink-mute">
            I'll interview you, then a copywriter and a designer will work in
            parallel, builders will write every page, and a reviewer and auditor
            will check the result — live, on the right.
          </p>
        </div>
      )}

      {messages.map((message) => (
        <article key={message.id} className="mb-5">
          <p className="mb-1 text-[11px] font-semibold tracking-wide text-ink-mute uppercase">
            {message.agent && message.agent !== 'interviewer'
              ? message.agent
              : ROLE_LABEL[message.role] ?? message.role}
          </p>
          <div
            className={`text-[13.5px] leading-relaxed whitespace-pre-wrap ${
              message.role === 'user'
                ? 'rounded-md bg-surface-2 px-3.5 py-2.5 text-ink'
                : 'text-ink-dim'
            }`}
          >
            {message.content}
          </div>
        </article>
      ))}

      {streamingText && (
        <article className="mb-5">
          <p className="mb-1 text-[11px] font-semibold tracking-wide text-ink-mute uppercase">
            {streamingAgent}
          </p>
          <div className="stream-caret text-[13.5px] leading-relaxed whitespace-pre-wrap text-ink-dim">
            {streamingText}
          </div>
        </article>
      )}

      {chatBusy && !streamingText && (
        <p className="mb-5 text-[13px] text-ink-mute">
          <span className="stream-caret">Working</span>
        </p>
      )}

      <div ref={bottomRef} />
    </div>
  )
}

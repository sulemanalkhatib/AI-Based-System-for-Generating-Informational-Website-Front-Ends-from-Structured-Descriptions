import { useEffect, useRef, useState } from 'react'
import { SendHorizontal } from 'lucide-react'
import { sendChatMessage, useStore } from '../../state/store'
import { smartPlaceholder } from '../../lib/placeholder'

export function Composer() {
  const [value, setValue] = useState('')
  const chatBusy = useStore((s) => s.chatBusy)
  const editMode = useStore((s) => s.buildStatus === 'done')
  const messages = useStore((s) => s.messages)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // The interviewer's latest question drives a contextual placeholder that hints
  // at the answer to type (only meaningful during the interview, not edit mode).
  const lastQuestion = [...messages].reverse().find((m) => m.role === 'assistant')?.content
  const placeholder = chatBusy
    ? 'Working…'
    : editMode
      ? 'Ask for any change to your website…'
      : smartPlaceholder(lastQuestion)

  // Keep the cursor in the field after a turn finishes, so the user can keep
  // typing (especially editing requests) without clicking back into it.
  useEffect(() => {
    if (!chatBusy) textareaRef.current?.focus()
  }, [chatBusy])

  const send = () => {
    const content = value.trim()
    if (!content || chatBusy) return
    setValue('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
      textareaRef.current.focus()
    }
    void sendChatMessage(content)
  }

  return (
    <div className="shrink-0 border-t border-edge p-3">
      <div className="flex items-end gap-2 rounded-md border border-edge-2 bg-surface-2 p-2 transition-colors duration-200 focus-within:border-accent">
        <label htmlFor="composer" className="sr-only">
          Message
        </label>
        <textarea
          id="composer"
          ref={textareaRef}
          value={value}
          rows={1}
          placeholder={placeholder}
          onChange={(event) => {
            setValue(event.target.value)
            const el = event.target
            el.style.height = 'auto'
            el.style.height = `${Math.min(el.scrollHeight, 160)}px`
          }}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault()
              send()
            }
          }}
          className="max-h-40 flex-1 resize-none bg-transparent px-1.5 py-1 text-[13.5px] leading-relaxed text-ink outline-none placeholder:text-ink-mute"
        />
        <button
          onClick={send}
          disabled={chatBusy || !value.trim()}
          className="cursor-pointer rounded-sm bg-accent p-2 text-white transition-colors duration-200 hover:bg-accent-hover disabled:cursor-default disabled:opacity-40"
          aria-label="Send message"
        >
          <SendHorizontal size={15} aria-hidden />
        </button>
      </div>
      <p className="mt-1.5 px-1 text-[11px] text-ink-mute">
        Enter to send · Shift+Enter for a new line
      </p>
    </div>
  )
}

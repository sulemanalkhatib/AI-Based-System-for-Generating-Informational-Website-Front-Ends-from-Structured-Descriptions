import { useEffect, useState } from 'react'
import { Eye, EyeOff, ListRestart, LoaderCircle, X } from 'lucide-react'
import { api } from '../../lib/api'
import { toggleDevMode, useStore } from '../../state/store'
import type { AppSettings } from '../../lib/types'

const AGENTS = ['interviewer', 'copywriter', 'designer', 'builder', 'recheck', 'audit', 'editor']

const FALLBACK_MODELS = [
  'auto',
  'openai/gpt-4o-mini',
  'openai/gpt-4o',
  'google/gemini-2.5-flash',
  'google/gemini-2.5-pro',
  'meta-llama/llama-3.3-70b-instruct',
  'mistralai/mistral-large',
  'deepseek/deepseek-chat',
]

const ACCENTS = [
  { name: 'Terracotta', value: '#cc785c' },
  { name: 'Gold', value: '#c9a227' },
  { name: 'Sage', value: '#6aa87c' },
  { name: 'Slate blue', value: '#7a8ccc' },
]

const EMPTY: AppSettings = {
  models: Object.fromEntries(AGENTS.map((a) => [a, 'auto'])),
  theme_accent: '#cc785c',
  api_key: '',
  base_url: '',
  enabled: Object.fromEntries(AGENTS.map((a) => [a, true])),
  vision_audit: false,
  use_photos: true,
}

// The interviewer IS the chat — it can't be skipped, so it gets no toggle.
const TOGGLEABLE = new Set(['copywriter', 'designer', 'builder', 'recheck', 'audit'])

export function SettingsModal() {
  const open = useStore((s) => s.settingsOpen)
  const settings = useStore((s) => s.settings)
  const modelOptions = useStore((s) => s.modelOptions)
  const devMode = useStore((s) => s.devMode)
  const set = useStore((s) => s.set)
  const [draft, setDraft] = useState<AppSettings | null>(null)
  const [saving, setSaving] = useState(false)
  const [showKey, setShowKey] = useState(false)
  const [fetching, setFetching] = useState(false)
  const [fetchNote, setFetchNote] = useState('')

  useEffect(() => {
    if (open) {
      setDraft({
        ...EMPTY,
        ...settings,
        models: { ...EMPTY.models, ...settings?.models },
        enabled: { ...EMPTY.enabled, ...settings?.enabled },
      })
      setFetchNote('')
      setShowKey(false)
    }
  }, [open, settings])

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') set({ settingsOpen: false })
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, set])

  if (!open || !draft) return null

  const save = async () => {
    setSaving(true)
    try {
      const saved = await api.putSettings(draft)
      set({ settings: saved, settingsOpen: false })
    } finally {
      setSaving(false)
    }
  }

  const fetchModels = async () => {
    setFetching(true)
    setFetchNote('')
    try {
      const result = await api.fetchModels(draft.base_url, draft.api_key)
      set({ modelOptions: result.models })
      setFetchNote(`${result.models.length} models loaded`)
    } catch (error) {
      setFetchNote(`Failed: ${(error as Error).message}`)
    } finally {
      setFetching(false)
    }
  }

  const optionsFor = (current: string): string[] => {
    const base = modelOptions.length > 0 ? ['auto', ...modelOptions] : FALLBACK_MODELS
    return base.includes(current) ? base : [current, ...base]
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={(event) => {
        if (event.target === event.currentTarget) set({ settingsOpen: false })
      }}
      role="dialog"
      aria-modal="true"
      aria-label="Settings"
    >
      <div className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-md border border-edge-2 bg-surface-2">
        <header className="flex items-center justify-between border-b border-edge px-5 py-4">
          <h2 className="text-[15px] font-semibold">Settings</h2>
          <button
            onClick={() => set({ settingsOpen: false })}
            className="cursor-pointer rounded-sm p-1 text-ink-mute transition-colors duration-150 hover:bg-surface-3 hover:text-ink"
            aria-label="Close settings"
          >
            <X size={16} aria-hidden />
          </button>
        </header>

        <div className="space-y-6 px-5 py-5">
          <section>
            <div className="flex items-center justify-between rounded-md border border-edge bg-surface-1 px-3.5 py-3">
              <div className="pr-4">
                <h3 className="mb-1 text-[13px] font-semibold text-ink">Developer mode</h3>
                <p className="text-[12px] leading-relaxed text-ink-mute">
                  Adds a live <span className="font-medium text-ink-dim">Logs</span> tab
                  showing every agent request — model, chars in/out, duration, retries,
                  and file writes. Applies immediately (saved on this device).
                </p>
              </div>
              <button
                role="switch"
                aria-checked={devMode}
                aria-label={`${devMode ? 'Disable' : 'Enable'} developer mode`}
                onClick={toggleDevMode}
                className={`relative h-5 w-9 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ${
                  devMode ? 'bg-accent' : 'bg-surface-3'
                }`}
              >
                <span
                  className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-[left] duration-200 ${
                    devMode ? 'left-4.5' : 'left-0.5'
                  }`}
                />
              </button>
            </div>
          </section>

          <section>
            <h3 className="mb-1 text-[13px] font-semibold text-ink">Provider</h3>
            <p className="mb-3 text-[12px] leading-relaxed text-ink-mute">
              Any OpenRouter-compatible endpoint. Leave a field empty to use the
              value from <span className="font-mono">backend/.env</span>.
            </p>
            <div className="space-y-2.5">
              <div className="flex items-center gap-3">
                <label htmlFor="base-url" className="w-24 shrink-0 text-[12.5px] text-ink-dim">
                  Base URL
                </label>
                <input
                  id="base-url"
                  value={draft.base_url}
                  placeholder="https://openrouter.ai/api/v1"
                  onChange={(event) => setDraft({ ...draft, base_url: event.target.value })}
                  className="min-w-0 flex-1 rounded-sm border border-edge-2 bg-surface-1 px-2.5 py-1.5 font-mono text-[12px] text-ink outline-none transition-colors duration-150 focus:border-accent placeholder:text-ink-mute"
                />
              </div>
              <div className="flex items-center gap-3">
                <label htmlFor="api-key" className="w-24 shrink-0 text-[12.5px] text-ink-dim">
                  API key
                </label>
                <div className="flex min-w-0 flex-1 items-center gap-1 rounded-sm border border-edge-2 bg-surface-1 transition-colors duration-150 focus-within:border-accent">
                  <input
                    id="api-key"
                    type={showKey ? 'text' : 'password'}
                    value={draft.api_key}
                    placeholder="sk-or-…"
                    autoComplete="off"
                    onChange={(event) => setDraft({ ...draft, api_key: event.target.value })}
                    className="min-w-0 flex-1 bg-transparent px-2.5 py-1.5 font-mono text-[12px] text-ink outline-none placeholder:text-ink-mute"
                  />
                  <button
                    onClick={() => setShowKey(!showKey)}
                    className="cursor-pointer p-1.5 text-ink-mute transition-colors duration-150 hover:text-ink"
                    aria-label={showKey ? 'Hide API key' : 'Show API key'}
                  >
                    {showKey ? <EyeOff size={14} aria-hidden /> : <Eye size={14} aria-hidden />}
                  </button>
                </div>
              </div>
              <div className="flex items-center gap-2 pl-27">
                <button
                  onClick={() => void fetchModels()}
                  disabled={fetching}
                  className="flex cursor-pointer items-center gap-1.5 rounded-sm border border-edge-2 bg-surface-1 px-2.5 py-1.5 text-[12px] text-ink-dim transition-colors duration-150 hover:border-accent hover:text-accent disabled:opacity-50"
                >
                  {fetching ? (
                    <LoaderCircle size={13} className="spin" aria-hidden />
                  ) : (
                    <ListRestart size={13} aria-hidden />
                  )}
                  Fetch models
                </button>
                {fetchNote && (
                  <span
                    className={`text-[11.5px] ${fetchNote.startsWith('Failed') ? 'text-err' : 'text-ok'}`}
                  >
                    {fetchNote}
                  </span>
                )}
              </div>
            </div>
          </section>

          <section>
            <h3 className="mb-1 text-[13px] font-semibold text-ink">Agents</h3>
            <p className="mb-3 text-[12px] leading-relaxed text-ink-mute">
              Pick a model per agent — "auto" lets the router decide; use "Fetch
              models" above for the full list. The switch stops an agent: the
              pipeline skips it and continues with a built-in fallback instead.
              The <span className="font-medium text-ink-dim">editor</span> handles
              post-build change requests; left on "auto" it follows the builder's model.
            </p>
            <div className="space-y-2.5">
              {AGENTS.map((agent) => {
                const current = draft.models[agent] ?? 'auto'
                const on = draft.enabled[agent] !== false
                return (
                  <div key={agent} className="flex items-center gap-3">
                    <label
                      htmlFor={`model-${agent}`}
                      className={`w-24 shrink-0 text-[12.5px] capitalize ${
                        on ? 'text-ink-dim' : 'text-ink-mute line-through'
                      }`}
                    >
                      {agent}
                    </label>
                    <select
                      id={`model-${agent}`}
                      value={current}
                      disabled={!on}
                      onChange={(event) =>
                        setDraft({
                          ...draft,
                          models: { ...draft.models, [agent]: event.target.value },
                        })
                      }
                      className="min-w-0 flex-1 cursor-pointer rounded-sm border border-edge-2 bg-surface-1 px-2 py-1.5 font-mono text-[12px] text-ink outline-none transition-colors duration-150 focus:border-accent disabled:cursor-default disabled:opacity-40"
                    >
                      {optionsFor(current).map((id) => (
                        <option key={id} value={id}>
                          {id}
                        </option>
                      ))}
                    </select>
                    {TOGGLEABLE.has(agent) ? (
                      <button
                        role="switch"
                        aria-checked={on}
                        aria-label={`${on ? 'Stop' : 'Enable'} ${agent} agent`}
                        title={on ? 'Stop this agent (pipeline will skip it)' : 'Enable this agent'}
                        onClick={() =>
                          setDraft((d) =>
                            d && {
                              ...d,
                              enabled: {
                                ...d.enabled,
                                [agent]: d.enabled[agent] === false,
                              },
                            })
                        }
                        className={`relative h-5 w-9 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ${
                          on ? 'bg-accent' : 'bg-surface-3'
                        }`}
                      >
                        <span
                          className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-[left] duration-200 ${
                            on ? 'left-4.5' : 'left-0.5'
                          }`}
                        />
                      </button>
                    ) : (
                      <span className="w-9 shrink-0" aria-hidden />
                    )}
                  </div>
                )
              })}
            </div>
          </section>

          <section>
            <div className="flex items-center justify-between">
              <div className="pr-4">
                <h3 className="mb-1 text-[13px] font-semibold text-ink">Visual audit</h3>
                <p className="text-[12px] leading-relaxed text-ink-mute">
                  The auditor screenshots the rendered home page and scores the design
                  from what it actually looks like — not just the code. Needs a
                  vision-capable audit model (e.g. gpt-4o-mini) and Playwright on the
                  server. Off by default: slower and costs more per build.
                </p>
              </div>
              <button
                role="switch"
                aria-checked={draft.vision_audit}
                aria-label={`${draft.vision_audit ? 'Disable' : 'Enable'} visual audit`}
                onClick={() =>
                  setDraft((d) => d && { ...d, vision_audit: !d.vision_audit })
                }
                className={`relative h-5 w-9 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ${
                  draft.vision_audit ? 'bg-accent' : 'bg-surface-3'
                }`}
              >
                <span
                  className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-[left] duration-200 ${
                    draft.vision_audit ? 'left-4.5' : 'left-0.5'
                  }`}
                />
              </button>
            </div>
          </section>

          <section>
            <div className="flex items-center justify-between">
              <div className="pr-4">
                <h3 className="mb-1 text-[13px] font-semibold text-ink">Stock photography</h3>
                <p className="text-[12px] leading-relaxed text-ink-mute">
                  Generated sites use real stock photos (heroes, galleries, story
                  sections). Turn off to build with brand-gradient placeholders only —
                  fully offline-safe with no external image URLs, ideal for exported
                  sites with no network. On by default.
                </p>
              </div>
              <button
                role="switch"
                aria-checked={draft.use_photos !== false}
                aria-label={`${draft.use_photos !== false ? 'Disable' : 'Enable'} stock photography`}
                onClick={() =>
                  setDraft((d) => d && { ...d, use_photos: d.use_photos === false })
                }
                className={`relative h-5 w-9 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ${
                  draft.use_photos !== false ? 'bg-accent' : 'bg-surface-3'
                }`}
              >
                <span
                  className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-[left] duration-200 ${
                    draft.use_photos !== false ? 'left-4.5' : 'left-0.5'
                  }`}
                />
              </button>
            </div>
          </section>

          <section>
            <h3 className="mb-1 text-[13px] font-semibold text-ink">Accent color</h3>
            <p className="mb-3 text-[12px] text-ink-mute">
              The single saturated color used across the app.
            </p>
            <div className="flex items-center gap-2">
              {ACCENTS.map((accent) => (
                <button
                  key={accent.value}
                  onClick={() => setDraft({ ...draft, theme_accent: accent.value })}
                  className={`h-8 w-8 cursor-pointer rounded-full border-2 transition-transform duration-150 hover:scale-105 ${
                    draft.theme_accent === accent.value ? 'border-ink' : 'border-transparent'
                  }`}
                  style={{ background: accent.value }}
                  aria-label={`Accent ${accent.name}`}
                  title={accent.name}
                />
              ))}
              <input
                type="color"
                value={draft.theme_accent}
                onChange={(event) => setDraft({ ...draft, theme_accent: event.target.value })}
                className="h-8 w-10 cursor-pointer rounded-sm border border-edge-2 bg-surface-1"
                aria-label="Custom accent color"
                title="Custom color"
              />
            </div>
          </section>
        </div>

        <footer className="flex justify-end gap-2 border-t border-edge px-5 py-4">
          <button
            onClick={() => set({ settingsOpen: false })}
            className="cursor-pointer rounded-sm border border-edge-2 px-4 py-1.5 text-[13px] text-ink-dim transition-colors duration-150 hover:bg-surface-3 hover:text-ink"
          >
            Cancel
          </button>
          <button
            onClick={() => void save()}
            disabled={saving}
            className="cursor-pointer rounded-sm bg-accent px-4 py-1.5 text-[13px] font-medium text-white transition-colors duration-200 hover:bg-accent-hover disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save'}
          </button>
        </footer>
      </div>
    </div>
  )
}

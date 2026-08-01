// Smart composer placeholder: reads the interviewer's most recent question and
// suggests an example ANSWER, so the field hints at what to type (like a chat app
// showing a contextual prompt). Pure + deterministic — no LLM call. The interviewer
// asks about a fixed set of brief topics (see prompts/interviewer.py), so keyword
// matching on the question is reliable. Order matters: most specific first.

const DEFAULT = 'Describe your business…'

type Rule = { test: (q: string) => boolean; hint: string }

const has = (q: string, ...needles: string[]) => needles.some((n) => q.includes(n))

const RULES: Rule[] = [
  // Confirmation / "ready to build?" turn — invite the go-ahead.
  {
    test: (q) =>
      has(q, 'sound right', 'sound good', 'anything missing', 'anything i missed',
        'anything else', 'anything you', 'shall i', 'shall we', 'ready to', 'kick off',
        'start the build', "say 'go'", 'say go', 'or tweak', 'look correct', 'all correct'),
    hint: "Type 'go' to start the build — or add anything I missed…",
  },
  // Business name.
  {
    test: (q) =>
      has(q, 'name of your', 'business name', "business's name", 'called', 'what is it called',
        "what's it called", 'what should i call', 'brand name', 'company name'),
    hint: 'e.g. Ember & Oak',
  },
  // Colours / palette.
  {
    test: (q) => has(q, 'color', 'colour', 'palette', 'brand colours', 'brand colors'),
    hint: 'e.g. deep charcoal, warm cream, and ember orange',
  },
  // Tone / style / vibe.
  {
    test: (q) =>
      has(q, 'tone', 'vibe', 'feel', 'style', 'personality', 'mood', 'atmosphere', 'aesthetic'),
    hint: 'e.g. warm, elegant, and inviting',
  },
  // Pages / sections.
  {
    test: (q) => has(q, 'pages', 'sections', 'which page'),
    hint: 'e.g. Home, Menu, About, Contact',
  },
  // Primary goal / call to action.
  {
    test: (q) =>
      has(q, 'most important action', 'main goal', 'primary goal', 'want visitors to',
        'want people to', 'call to action', 'one thing', 'single most', 'take action',
        'visitors to do', 'main thing'),
    hint: 'e.g. get people to book a table',
  },
  // Target audience.
  {
    test: (q) =>
      has(q, 'audience', 'who is', "who's it for", 'who is it for', 'customers', 'clients',
        'who does', 'who are you', 'target', 'who you serve', 'who it serves'),
    hint: 'e.g. couples aged 25–45 after a warm night out',
  },
  // References / inspiration.
  {
    test: (q) =>
      has(q, 'admire', 'inspiration', 'inspired', 'reference', 'websites you like',
        'sites you like', 'look and feel', 'north star', 'visual direction', 'like the look'),
    hint: 'e.g. the airy, editorial feel of Aesop and Bloom & Wild',
  },
  // Concrete content details.
  {
    test: (q) =>
      has(q, 'hours', 'opening', 'price', 'pricing', 'location', 'address', 'tagline',
        'team', 'menu', 'dishes', 'services', 'products', 'testimonial', 'contact', 'phone',
        'email', 'signature'),
    hint: 'e.g. open Tue–Sun 17:00–23:00 · signature: 48-hour short rib',
  },
  // Opening / discovery — what the business is.
  {
    test: (q) =>
      has(q, 'what kind of', 'what type', 'what does your', 'tell me about', "what's your business",
        'what is your business', 'what you do', 'what do you do', 'describe your'),
    hint: 'e.g. a cozy wood-fired bistro serving seasonal small plates',
  },
]

/**
 * Given the interviewer's latest message, return an example-answer placeholder.
 * Falls back to a generic prompt when there's no question yet or nothing matches.
 */
export function smartPlaceholder(lastQuestion: string | undefined | null): string {
  const q = (lastQuestion ?? '').toLowerCase()
  if (!q.trim()) return DEFAULT
  for (const rule of RULES) {
    if (rule.test(q)) return rule.hint
  }
  // There is a question, but it didn't match a known topic — nudge generically.
  return q.includes('?') ? 'Type your answer…' : DEFAULT
}

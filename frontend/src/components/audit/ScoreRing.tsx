export function ScoreRing({ score }: { score: number }) {
  const radius = 44
  const circumference = 2 * Math.PI * radius
  const filled = (Math.max(0, Math.min(100, score)) / 100) * circumference
  const color =
    score >= 80 ? 'var(--color-ok)' : score >= 60 ? 'var(--color-warn)' : 'var(--color-err)'

  return (
    <svg
      width="120"
      height="120"
      viewBox="0 0 120 120"
      role="img"
      aria-label={`Audit score ${score} out of 100`}
    >
      <circle
        cx="60"
        cy="60"
        r={radius}
        fill="none"
        stroke="var(--color-surface-3)"
        strokeWidth="9"
      />
      <circle
        cx="60"
        cy="60"
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth="9"
        strokeLinecap="round"
        strokeDasharray={`${filled} ${circumference - filled}`}
        transform="rotate(-90 60 60)"
      />
      <text
        x="60"
        y="57"
        textAnchor="middle"
        fill="var(--color-ink)"
        fontSize="26"
        fontWeight="700"
        fontFamily="Inter, sans-serif"
      >
        {score}
      </text>
      <text
        x="60"
        y="76"
        textAnchor="middle"
        fill="var(--color-ink-mute)"
        fontSize="11"
        fontFamily="Inter, sans-serif"
      >
        / 100
      </text>
    </svg>
  )
}

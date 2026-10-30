export function SeverityBadge({ level }: { level: 'high' | 'medium' | 'low' }) {
  const styles: Record<string, string> = {
    high: 'severity-badge severity-high',
    medium: 'severity-badge severity-medium',
    low: 'severity-badge severity-low',
  }
  return <span className={styles[level] || styles.low}>{level.toUpperCase()}</span>
}


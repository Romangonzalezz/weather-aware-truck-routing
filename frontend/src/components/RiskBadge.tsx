import { levelColor, type Level } from "../domain/levels";

export function RiskBadge({ level }: { level: Level }) {
  return (
    <span className="risk-badge">
      <span className="risk-dot" style={{ background: levelColor(level) }} aria-hidden="true" />
      {level}
    </span>
  );
}

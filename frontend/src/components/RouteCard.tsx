import type { Route } from "../api/types";
import { formatDuration, formatMiles, formatTime } from "../domain/format";
import { routeColorForRank } from "../map/geojson";
import { RiskBadge } from "./RiskBadge";

interface Props {
  route: Route;
  reason?: string;
  selected: boolean;
  onSelect: (id: string) => void;
}

export function RouteCard({ route, reason, selected, onSelect }: Props) {
  const { summary } = route;
  return (
    <button className="route-card" type="button" aria-pressed={selected} onClick={() => onSelect(route.id)}>
      <span className="route-card-title">
        <span className="route-swatch" style={{ background: routeColorForRank(route.rank) }} aria-hidden="true" />
        Route {route.rank}
        {route.recommended && <span className="recommended-tag">Recommended</span>}
        <RiskBadge level={summary.max_level} />
      </span>
      {reason && <span className="route-reason">{reason}</span>}
      <span className="route-trip">
        {formatMiles(summary.distance_mi)} &middot; {formatDuration(summary.duration_h)} &middot; arrives{" "}
        {formatTime(summary.arrival)}
      </span>
      <dl className="route-stats">
        <Stat label="No Travel" value={formatMiles(summary.no_travel_mi)} />
        <Stat label="Severe" value={formatMiles(summary.severe_mi)} />
        <Stat label="High" value={formatMiles(summary.high_mi)} />
        <Stat label="Avg risk" value={`${summary.avg_risk.toFixed(2)} / 4`} />
      </dl>
    </button>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

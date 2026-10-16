import type { Route } from "../api/types";
import { formatConditions, formatMiles, formatTime } from "../domain/format";
import { RiskBadge } from "./RiskBadge";

export function CheckpointList({ route }: { route: Route }) {
  return (
    <section aria-labelledby="checkpoints-heading">
      <h2 id="checkpoints-heading">Route {route.rank} checkpoints</h2>
      <ol className="checkpoints">
        {route.checkpoints.map((checkpoint) => (
          <li key={checkpoint.mile}>
            <div className="checkpoint-head">
              <span>
                {formatMiles(checkpoint.mile)} &middot; {formatTime(checkpoint.eta)}
              </span>
              <RiskBadge level={checkpoint.level} />
            </div>
            <div className="checkpoint-conditions">{formatConditions(checkpoint)}</div>
            {checkpoint.reasons.length > 0 && <div className="checkpoint-reasons">{checkpoint.reasons.join("; ")}</div>}
          </li>
        ))}
      </ol>
    </section>
  );
}

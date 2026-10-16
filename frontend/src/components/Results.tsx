import { memo } from "react";
import type { Plan } from "../api/types";
import { CheckpointList } from "./CheckpointList";
import { RouteCard } from "./RouteCard";

const WANTED_ROUTES = 3;

interface Props {
  plan: Plan;
  selectedRouteId: string;
  onSelect: (id: string) => void;
}

// memo: the heatmap slider re-renders the app on every tick, and this list has nothing to do with the hour.
export const Results = memo(function Results({ plan, selectedRouteId, onSelect }: Props) {
  const selected = plan.routes.find((route) => route.id === selectedRouteId) ?? plan.routes[0];
  return (
    <div className="results">
      <section aria-labelledby="routes-heading">
        <h2 id="routes-heading">
          {plan.origin.name} to {plan.destination.name}
        </h2>
        <ul className="route-list">
          {plan.routes.map((route) => (
            <li key={route.id}>
              <RouteCard
                route={route}
                reason={route.recommended ? plan.recommendation_reason : undefined}
                selected={route.id === selected.id}
                onSelect={onSelect}
              />
            </li>
          ))}
        </ul>
        {plan.routes.length < WANTED_ROUTES && (
          <p className="note">
            Only {plan.routes.length} distinct route{plan.routes.length === 1 ? "" : "s"} found for this trip.
          </p>
        )}
      </section>
      <CheckpointList route={selected} />
    </div>
  );
});

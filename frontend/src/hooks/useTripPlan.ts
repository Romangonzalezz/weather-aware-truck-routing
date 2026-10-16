import { useCallback, useRef, useState } from "react";
import { fetchCorridor, planTrip } from "../api/client";
import type { Corridor, Plan, PlanRequest } from "../api/types";
import { corridorRequestFor } from "../domain/tripForm";

export type PlanState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; plan: Plan };

export type CorridorState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; corridor: Corridor };

const messageOf = (error: unknown) => (error instanceof Error ? error.message : "Something went wrong.");
const wasAborted = (error: unknown) => error instanceof DOMException && error.name === "AbortError";

/** Plans a trip, then fetches its heatmap corridor once; a newer request cancels the one in flight. */
export function useTripPlan() {
  const [planState, setPlanState] = useState<PlanState>({ status: "idle" });
  const [corridorState, setCorridorState] = useState<CorridorState>({ status: "idle" });
  const inFlight = useRef<AbortController>(undefined);

  const submit = useCallback(async (request: PlanRequest) => {
    inFlight.current?.abort();
    const abort = new AbortController();
    inFlight.current = abort;
    setPlanState({ status: "loading" });
    setCorridorState({ status: "idle" });

    let plan: Plan;
    try {
      plan = await planTrip(request, abort.signal);
    } catch (error) {
      if (!wasAborted(error)) setPlanState({ status: "error", message: messageOf(error) });
      return;
    }
    setPlanState({ status: "ready", plan });
    setCorridorState({ status: "loading" });

    try {
      setCorridorState({ status: "ready", corridor: await fetchCorridor(corridorRequestFor(plan), abort.signal) });
    } catch (error) {
      if (!wasAborted(error)) setCorridorState({ status: "error", message: messageOf(error) });
    }
  }, []);

  return { planState, corridorState, submit };
}

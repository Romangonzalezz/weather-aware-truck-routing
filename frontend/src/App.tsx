import { useCallback, useState } from "react";
import { MapControls } from "./components/MapControls";
import { Results } from "./components/Results";
import { TripFormPanel } from "./components/TripFormPanel";
import { useTripPlan } from "./hooks/useTripPlan";
import { MapView } from "./map/MapView";

export default function App() {
  const { planState, corridorState, submit } = useTripPlan();
  const [chosenRouteId, setChosenRouteId] = useState<string>();
  const [hour, setHour] = useState(0);
  const [heatmapVisible, setHeatmapVisible] = useState(true);
  const [playing, setPlaying] = useState(false);

  const plan = planState.status === "ready" ? planState.plan : undefined;
  const selectedRouteId = chosenRouteId ?? plan?.recommended_route_id;
  const corridor = corridorState.status === "ready" ? corridorState.corridor : undefined;

  const planTrip = useCallback(
    (...args: Parameters<typeof submit>) => {
      setChosenRouteId(undefined);
      setHour(0);
      setPlaying(false);
      return submit(...args);
    },
    [submit],
  );

  return (
    <div className="app">
      <aside className="panel">
        <h1>Weather-aware truck routing</h1>
        <TripFormPanel loading={planState.status === "loading"} onSubmit={planTrip} />
        <div aria-live="polite">
          {planState.status === "loading" && (
            <p className="note">Finding routes and checking the forecast at each checkpoint. This can take 10 to 15 seconds.</p>
          )}
          {planState.status === "error" && (
            <p className="form-error" role="alert">
              {planState.message}
            </p>
          )}
        </div>
        {plan && selectedRouteId && <Results plan={plan} selectedRouteId={selectedRouteId} onSelect={setChosenRouteId} />}
      </aside>

      <main className="map-area">
        <MapView plan={plan} selectedRouteId={selectedRouteId} corridor={corridor} hour={hour} heatmapVisible={heatmapVisible} />
        <MapControls
          corridor={corridorState}
          hour={hour}
          onHourChange={setHour}
          visible={heatmapVisible}
          onVisibleChange={setHeatmapVisible}
          playing={playing}
          onPlayingChange={setPlaying}
        />
      </main>
    </div>
  );
}

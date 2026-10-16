import { useEffect } from "react";
import type { CorridorState } from "../hooks/useTripPlan";
import { formatWindowHour } from "../domain/format";
import { LEVELS } from "../domain/levels";

const PLAY_INTERVAL_MS = 400;

interface Props {
  corridor: CorridorState;
  hour: number;
  onHourChange: (hour: number) => void;
  visible: boolean;
  onVisibleChange: (visible: boolean) => void;
  playing: boolean;
  onPlayingChange: (playing: boolean) => void;
}

export function MapControls({ corridor, hour, onHourChange, visible, onVisibleChange, playing, onPlayingChange }: Props) {
  const times = corridor.status === "ready" ? corridor.corridor.times : [];
  const lastHour = Math.max(times.length - 1, 0);

  useEffect(() => {
    if (!playing) return;
    const timer = setInterval(() => onHourChange(hour >= lastHour ? 0 : hour + 1), PLAY_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [playing, hour, lastHour, onHourChange]);

  return (
    <div className="map-controls">
      <label className="toggle">
        <input type="checkbox" checked={visible} onChange={(event) => onVisibleChange(event.target.checked)} />
        Weather heatmap
      </label>

      {corridor.status === "loading" && <p className="note">Loading the forecast along the route...</p>}
      {corridor.status === "error" && (
        <p className="note" role="alert">
          {corridor.message} The routes above are still valid; the heatmap is unavailable.
        </p>
      )}

      {times.length > 0 && (
        <div className="slider-row">
          <button
            type="button"
            className="play"
            aria-label={playing ? "Pause forecast animation" : "Play forecast animation"}
            onClick={() => onPlayingChange(!playing)}
          >
            {playing ? "Pause" : "Play"}
          </button>
          <div className="slider">
            <label htmlFor="forecast-hour">
              <span>+{hour} h</span>
              <strong>{formatWindowHour(times[hour])}</strong>
            </label>
            <input
              id="forecast-hour"
              type="range"
              min={0}
              max={lastHour}
              step={1}
              value={hour}
              onChange={(event) => onHourChange(Number(event.target.value))}
              aria-valuetext={`${hour} hours after departure, ${formatWindowHour(times[hour])}`}
            />
          </div>
        </div>
      )}

      <ul className="legend" aria-label="Risk levels">
        {LEVELS.map((level) => (
          <li key={level.label}>
            <span className="risk-dot" style={{ background: level.color }} aria-hidden="true" />
            {level.label}
          </li>
        ))}
      </ul>
    </div>
  );
}

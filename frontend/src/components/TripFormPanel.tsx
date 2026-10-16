import { useState, type FormEvent } from "react";
import type { IntervalMiles, PlanRequest } from "../api/types";
import { nextFullHour, toDateTimeLocalValue } from "../domain/format";
import { MAX_LOAD_LB, planRequestFrom, type TripForm } from "../domain/tripForm";
import { PlaceInput } from "./PlaceInput";

const INTERVALS: IntervalMiles[] = [10, 25, 50];
const FORECAST_DAYS = 15;
const MS_PER_DAY = 24 * 3600 * 1000;

interface Props {
  loading: boolean;
  onSubmit: (request: PlanRequest) => void;
}

export function TripFormPanel({ loading, onSubmit }: Props) {
  const [now] = useState(() => new Date());
  const [form, setForm] = useState<TripForm>(() => ({
    origin: { text: "" },
    destination: { text: "" },
    departure: toDateTimeLocalValue(nextFullHour(now)),
    loadLb: "38000",
    intervalMiles: 25,
  }));
  const [error, setError] = useState<string>();

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const result = planRequestFrom(form);
    setError(result.ok ? undefined : result.error);
    if (result.ok) onSubmit(result.request);
  };

  return (
    <form className="trip-form" onSubmit={submit} noValidate>
      <PlaceInput label="Origin" value={form.origin} onChange={(origin) => setForm({ ...form, origin })} />
      <PlaceInput label="Destination" value={form.destination} onChange={(destination) => setForm({ ...form, destination })} />

      <div className="field-row">
        <div className="field">
          <label htmlFor="departure">Departure</label>
          <input
            id="departure"
            type="datetime-local"
            value={form.departure}
            min={toDateTimeLocalValue(now)}
            max={toDateTimeLocalValue(new Date(now.getTime() + FORECAST_DAYS * MS_PER_DAY))}
            onChange={(event) => setForm({ ...form, departure: event.target.value })}
          />
        </div>
        <div className="field">
          <label htmlFor="load">Load weight (lb)</label>
          <input
            id="load"
            type="number"
            inputMode="numeric"
            min={0}
            max={MAX_LOAD_LB}
            step={500}
            value={form.loadLb}
            onChange={(event) => setForm({ ...form, loadLb: event.target.value })}
          />
        </div>
      </div>

      <fieldset className="segmented">
        <legend>Weather checkpoint every</legend>
        <div className="segments">
          {INTERVALS.map((miles) => (
            <label key={miles}>
              <input
                type="radio"
                name="interval"
                checked={form.intervalMiles === miles}
                onChange={() => setForm({ ...form, intervalMiles: miles })}
              />
              <span>{miles} mi</span>
            </label>
          ))}
        </div>
      </fieldset>

      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <button className="primary" type="submit" disabled={loading}>
        {loading ? "Planning..." : "Plan routes"}
      </button>
    </form>
  );
}

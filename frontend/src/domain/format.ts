const MINUTES_PER_HOUR = 60;

export function formatDuration(hours: number): string {
  const totalMinutes = Math.round(hours * MINUTES_PER_HOUR);
  const wholeHours = Math.floor(totalMinutes / MINUTES_PER_HOUR);
  const minutes = totalMinutes % MINUTES_PER_HOUR;
  if (wholeHours === 0) return `${minutes} min`;
  return minutes === 0 ? `${wholeHours} h` : `${wholeHours} h ${minutes} min`;
}

export function formatMiles(miles: number): string {
  return `${Math.round(miles).toLocaleString("en-US")} mi`;
}

export function formatTime(iso: string, timeZone?: string): string {
  return intl(iso, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit", timeZone });
}

export function formatWindowHour(iso: string, timeZone?: string): string {
  return intl(iso, { weekday: "short", hour: "numeric", minute: "2-digit", timeZone });
}

function intl(iso: string, options: Intl.DateTimeFormatOptions): string {
  // Newer ICU puts a narrow no-break space before AM/PM; a plain space renders and compares the same everywhere.
  return new Intl.DateTimeFormat("en-US", options).format(new Date(iso)).replaceAll("\u202f", " ");
}

export function nextFullHour(now: Date): Date {
  const next = new Date(now);
  next.setMinutes(0, 0, 0);
  next.setHours(next.getHours() + 1);
  return next;
}

export function toDateTimeLocalValue(date: Date): string {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function departureToIso(dateTimeLocalValue: string): string {
  return new Date(dateTimeLocalValue).toISOString();
}

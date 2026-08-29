const DATE_LONG: Intl.DateTimeFormatOptions = {
  weekday: "long",
  month: "short",
  day: "numeric",
};

const DATE_SHORT: Intl.DateTimeFormatOptions = {
  weekday: "short",
  month: "short",
  day: "numeric",
};

const TIME: Intl.DateTimeFormatOptions = {
  hour: "numeric",
  minute: "2-digit",
};

export const SPECIALTIES = [
  "Primary Care",
  "Cardiology",
  "Orthopedics",
  "Dermatology",
  "Neurology",
] as const;

export const LOCATIONS = ["Main Clinic", "North Clinic", "Specialty Center"] as const;

export function greeting(name: string, now = new Date()): string {
  const hour = now.getHours();
  const part = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  return `${part}, ${name}`;
}

export function shortClinicianName(displayName: string): string {
  const parts = displayName.trim().split(/\s+/);
  if (parts[0] === "Dr." && parts.length >= 2) {
    return `Dr. ${parts[parts.length - 1]}`;
  }
  return parts[0] ?? displayName;
}

export function firstName(displayName: string): string {
  return displayName.trim().split(/\s+/)[0] ?? displayName;
}

export function formatWhen(value: string | Date): string {
  const date = value instanceof Date ? value : new Date(value);
  return new Intl.DateTimeFormat(undefined, { ...DATE_SHORT, ...TIME }).format(date);
}

export function formatDateLong(value: string | Date): string {
  const date = value instanceof Date ? value : new Date(value);
  return new Intl.DateTimeFormat(undefined, DATE_LONG).format(date);
}

export function formatDateShort(value: string | Date): string {
  const date = value instanceof Date ? value : new Date(value);
  return new Intl.DateTimeFormat(undefined, DATE_SHORT).format(date);
}

export function formatTime(value: string | Date): string {
  const date = value instanceof Date ? value : new Date(value);
  return new Intl.DateTimeFormat(undefined, TIME).format(date);
}

export function formatWait(from: string, now = new Date()): string {
  const created = new Date(from).getTime();
  const minutes = Math.max(0, Math.round((now.getTime() - created) / 60_000));
  if (minutes < 60) return `${minutes} min waiting`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours} hr waiting`;
  return `${Math.round(hours / 24)} days waiting`;
}

export function isMorning(value: string | Date): boolean {
  const date = value instanceof Date ? value : new Date(value);
  return date.getHours() < 12;
}

export function relativeDayLabel(value: string | Date, now = new Date()): string {
  const date = value instanceof Date ? value : new Date(value);
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate());
  const diff = Math.round((target.getTime() - start.getTime()) / 86_400_000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Tomorrow";
  if (diff === -1) return "Yesterday";
  return formatDateLong(date);
}

/**
 * Demo fixtures namespace every patient record as `patient-synthetic-NNN`. That
 * namespace is a backend guard — voice callbacks and the demo controls hard-fail
 * on an id that lacks it — not something a reader needs on screen. Strip it for
 * display only; never round-trip this value back into an API call.
 */
export function displayPatientId(id: string): string {
  return id.replace(/^patient-synthetic-/, "patient-");
}

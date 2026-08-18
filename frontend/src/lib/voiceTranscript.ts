export type TranscriptRole = "eir" | "you";

export type TranscriptLine = {
  role: TranscriptRole;
  text: string;
  pending: boolean;
};

export function mergeUtterance(previous: string, next: string): string {
  const a = previous.replace(/\s+/g, " ").trim();
  const b = next.replace(/\s+/g, " ").trim();
  if (!a) {
    return b;
  }
  if (!b) {
    return a;
  }
  if (b === a || b.startsWith(a) || (b.includes(a) && b.length > a.length)) {
    return b;
  }
  if (a.startsWith(b) || a.includes(b)) {
    return a;
  }
  return a.length >= b.length ? a : b;
}

export function applyTranscript(
  lines: TranscriptLine[],
  role: TranscriptRole,
  text: string,
  finished: boolean,
): TranscriptLine[] {
  const clean = text.replace(/\s+/g, " ").trim();
  if (!clean) {
    return lines;
  }
  const last = lines[lines.length - 1];
  const canMerge = Boolean(last && last.role === role && last.pending);
  if (canMerge && last) {
    return [...lines.slice(0, -1), { role, text: mergeUtterance(last.text, clean), pending: !finished }].slice(-30);
  }
  return [...lines, { role, text: clean, pending: !finished }].slice(-30);
}

export type TranscriptRole = "eir" | "you";

export type TranscriptLine = {
  /** Turn id minted by the scenario. Deltas carrying the same id extend this line. */
  id: number;
  role: TranscriptRole;
  text: string;
  pending: boolean;
};

const MAX_LINES = 30;
const TURN_TEXT_LIMIT = 4000;

/**
 * Gemini Live streams transcription as incremental deltas, so a chunk is
 * appended, never reconciled against what came before. Whitespace runs are
 * collapsed but the leading space is kept: it carries the word break between
 * one delta and the next ("Hi" + " Alex" vs "record" + "ing").
 */
function normalizeDelta(delta: string): string {
  return delta.replace(/\s+/g, " ");
}

function extend(text: string, delta: string): string {
  const next = text ? text + delta : delta.replace(/^ /, "");
  return next.length > TURN_TEXT_LIMIT ? next.slice(0, TURN_TEXT_LIMIT) : next;
}

export function appendTranscript(
  lines: TranscriptLine[],
  turn: number,
  role: TranscriptRole,
  delta: string,
  finished: boolean,
): TranscriptLine[] {
  const chunk = normalizeDelta(delta);
  const index = lines.findIndex((line) => line.id === turn);

  if (index !== -1) {
    const line = lines[index];
    const text = extend(line.text, chunk);
    const pending = line.pending && !finished;
    if (text === line.text && pending === line.pending) {
      return lines;
    }
    const next = [...lines];
    next[index] = { ...line, text, pending };
    return next;
  }

  // A finish-only message for a turn already evicted from the window: nothing to open.
  const text = extend("", chunk);
  if (!text.trim()) {
    return lines;
  }
  // The other speaker starting means the previous turn is over.
  const closed = lines.map((line) => (line.pending ? { ...line, pending: false } : line));
  return [...closed, { id: turn, role, text, pending: !finished }].slice(-MAX_LINES);
}

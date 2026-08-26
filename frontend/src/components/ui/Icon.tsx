import type { ReactElement } from "react";

import { cn } from "@/lib/cn";

/**
 * The drawn icon set, copied from `docs/design/canvas/System.dc.html` and the
 * nav rows of the role artboards. Stroke-only on a 24 grid, `fill="none"`,
 * `stroke="currentColor"`, so a glyph recolours with the control it sits in
 * and never carries state on its own.
 *
 * Icons are permitted in three positions only:
 *   1. leading a nav row,
 *   2. inside a control whose action is directional or destructive,
 *   3. marking a halt.
 * Never beside a headline, never inside a status chip, never in a tinted
 * rounded square.
 */

const STROKE_ACTION = 1.8;
const STROKE_DEFAULT = 1.6;

interface Glyph {
  path: ReactElement;
  stroke?: number;
}

const GLYPHS = {
  // --- surfaces, verbatim from System.dc.html -------------------------
  home: { path: <path d="M3 10.5 12 3l9 7.5V21h-6v-7H9v7H3z" /> },
  schedule: {
    path: (
      <>
        <path d="M4 6h16v15H4z" />
        <path d="M8 3v5M16 3v5M4 11h16" />
      </>
    ),
  },
  recovery: { path: <path d="M3 12h4l2.5-7 4 14L16 12h5" /> },
  reviews: {
    path: (
      <>
        <path d="M4 5h16v14H4z" />
        <path d="M4 13h4l1.5 3h5L16 13h4" />
      </>
    ),
  },
  patients: {
    path: (
      <>
        <circle cx="9" cy="8" r="3.4" />
        <path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6" />
        <path d="M16.5 5.4a3.2 3.2 0 0 1 0 6.2M17.4 14.6c2.6.7 4.6 2.8 4.6 5.4" />
      </>
    ),
  },
  fleet: {
    path: (
      <>
        <circle cx="12" cy="5.5" r="2.5" />
        <circle cx="5.5" cy="18" r="2.5" />
        <circle cx="18.5" cy="18" r="2.5" />
        <path d="M12 8v3.5M12 11.5 6.6 15.9M12 11.5l5.4 4.4" />
      </>
    ),
  },
  observe: {
    path: (
      <>
        <path d="M2 12s3.6-6.5 10-6.5S22 12 22 12s-3.6 6.5-10 6.5S2 12 2 12z" />
        <circle cx="12" cy="12" r="2.4" />
      </>
    ),
  },
  inventory: {
    path: (
      <>
        <path d="M12 3 3.5 7.5v9L12 21l8.5-4.5v-9z" />
        <path d="M3.5 7.5 12 12l8.5-4.5M12 12v9" />
      </>
    ),
  },
  search: {
    path: (
      <>
        <circle cx="11" cy="11" r="7" />
        <path d="M16.2 16.2 21 21" />
      </>
    ),
  },

  // --- actions, verbatim from System.dc.html (1.8 stroke) -------------
  open: {
    path: (
      <>
        <path d="M14 4h6v6M20 4l-9 9" />
        <path d="M18 14v6H4V6h6" />
      </>
    ),
    stroke: STROKE_ACTION,
  },
  approve: { path: <path d="M4.5 12.5 9.5 17.5 19.5 7" />, stroke: STROKE_ACTION },
  decline: {
    path: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M6.4 6.4 17.6 17.6" />
      </>
    ),
    stroke: STROKE_ACTION,
  },
  halt: {
    path: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M9.5 9.5h5v5h-5z" />
      </>
    ),
    stroke: STROKE_ACTION,
  },

  // --- nav glyphs used on the role artboards --------------------------
  today: {
    path: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3.5 2" />
      </>
    ),
  },
  assistant: { path: <path d="M4 5h16v11H9l-5 4z" /> },
  overview: {
    path: <path d="M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z" />,
  },

  // --- directional affordances, drawn to the same rules ---------------
  arrowRight: { path: <path d="M5 12h13M12.5 5.5 19 12l-6.5 6.5" />, stroke: STROKE_ACTION },
  arrowLeft: { path: <path d="M19 12H6M11.5 5.5 5 12l6.5 6.5" />, stroke: STROKE_ACTION },
  chevronRight: { path: <path d="M9.5 5.5 16 12l-6.5 6.5" />, stroke: STROKE_ACTION },
  chevronDown: { path: <path d="M5.5 9.5 12 16l6.5-6.5" />, stroke: STROKE_ACTION },
  close: { path: <path d="M6 6 18 18M18 6 6 18" />, stroke: STROKE_ACTION },
  menu: { path: <path d="M4 7h16M4 12h16M4 17h16" /> },
  refresh: {
    path: (
      <>
        <path d="M20.5 12a8.5 8.5 0 1 1-2.6-6.1" />
        <path d="M20.5 4v4.5H16" />
      </>
    ),
  },
  plus: { path: <path d="M12 5v14M5 12h14" />, stroke: STROKE_ACTION },
  voice: {
    path: (
      <path d="M6 3h3.6l1.8 4.6-2.3 1.4a11.4 11.4 0 0 0 5 5l1.4-2.3L20 13.4V17a2 2 0 0 1-2.2 2A15.8 15.8 0 0 1 5 6.2 2 2 0 0 1 6 3z" />
    ),
  },
  signOut: {
    path: (
      <>
        <path d="M14 20H5V4h9" />
        <path d="M18 12H10M15 8.5 18.5 12 15 15.5" />
      </>
    ),
  },
} satisfies Record<string, Glyph>;

export type IconName = keyof typeof GLYPHS;

export function Icon({
  name,
  size = 18,
  className,
}: {
  name: IconName;
  size?: number;
  className?: string;
}) {
  const glyph: Glyph = GLYPHS[name];
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={glyph.stroke ?? STROKE_DEFAULT}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className={cn("shrink-0", className)}
    >
      {glyph.path}
    </svg>
  );
}

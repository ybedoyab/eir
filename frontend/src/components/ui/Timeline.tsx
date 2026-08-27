/**
 * Hairline-ruled rows, mono timestamp in its own column. No bullet glyphs —
 * the rule and the column carry the sequence.
 */
export function Timeline({
  items,
}: {
  items: Array<{
    id: string;
    title: string;
    detail?: string;
    at: string;
  }>;
}) {
  if (!items.length) return null;
  return (
    <ol className="flex flex-col">
      {items.map((item) => (
        <li
          key={item.id}
          className="grid grid-cols-[108px_minmax(0,1fr)] items-baseline gap-5 border-b border-rule py-[18px]"
        >
          <span className="font-mono text-[0.75rem] text-muted">{item.at}</span>
          <div className="min-w-0">
            <p className="text-[0.9375rem] leading-[1.6] text-body">{item.title}</p>
            {item.detail ? (
              <p className="mt-1 text-[13.5px] leading-snug text-secondary">{item.detail}</p>
            ) : null}
          </div>
        </li>
      ))}
    </ol>
  );
}

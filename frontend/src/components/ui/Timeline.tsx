/**
 * Hairline-ruled rows, mono timestamp in its own column. No bullet glyphs —
 * the rule and the column carry the sequence. The whole log sits on a raised
 * surface: it is a record of what happened, not part of the page's prose, and
 * the surface change says so without a heading.
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
    <ol className="on-raised flex flex-col bg-raised px-6">
      {items.map((item) => (
        <li
          key={item.id}
          className="grid grid-cols-[108px_minmax(0,1fr)] items-baseline gap-5 border-b border-rule py-[18px] last:border-b-0"
        >
          <span className="font-mono text-[0.75rem] text-accent">{item.at}</span>
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

import { Icon } from "@/components/ui/Icon";

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
    <ol className="eir-surface eir-stagger on-surface flex flex-col px-6">
      {items.map((item) => (
        <li
          key={item.id}
          className="grid grid-cols-[20px_108px_minmax(0,1fr)] items-start gap-4 border-b border-rule py-[18px] last:border-b-0"
        >
          <span className="eir-icon-shell mt-0.5 h-6 w-6 rounded-full" aria-hidden>
            <Icon name="activity" size={12} />
          </span>
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

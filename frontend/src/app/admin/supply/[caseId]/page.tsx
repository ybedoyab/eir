"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/Button";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/PageHeader";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { cn } from "@/lib/cn";
import { eventLabel, eventOutcome } from "@/lib/eventLabels";
import {
  purchaseOrderStatus,
  replenishmentStatus,
  supplyUrgency,
} from "@/lib/statusLabels";
import {
  approvePurchaseOrder,
  getReplenishmentCase,
  listReplenishmentEvents,
  receiveDelivery,
} from "@/services/api";
import type { DomainEvent, ReplenishmentCase, SupplierQuote } from "@/types";

function formatWhen(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

/** Why a cheaper quote lost. Availability beats price when stock is the problem. */
function quoteNote(quote: SupplierQuote, order: ReplenishmentCase): string {
  const selected = order.purchase_order?.supplier_id === quote.supplier_id;
  if (selected) return "selected";
  if (quote.available_units < order.requested_quantity) {
    return `can only ship ${quote.available_units} of ${order.requested_quantity}`;
  }
  return "higher unit price";
}

export default function ReplenishmentCasePage({
  params,
}: {
  params: Promise<{ caseId: string }>;
}) {
  const [caseId, setCaseId] = useState("");
  const [supplyCase, setSupplyCase] = useState<ReplenishmentCase | null>(null);
  const [events, setEvents] = useState<DomainEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);

  const refresh = useCallback(async (id: string) => {
    setError(null);
    try {
      const [item, eventItems] = await Promise.all([
        getReplenishmentCase(id),
        listReplenishmentEvents(id),
      ]);
      setSupplyCase(item);
      setEvents(eventItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load the case");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void params.then((value) => setCaseId(value.caseId));
  }, [params]);

  useEffect(() => {
    if (caseId) {
      void refresh(caseId);
    }
  }, [caseId, refresh]);

  const order = supplyCase?.purchase_order ?? null;
  const awaitingApproval = supplyCase?.status === "AWAITING_APPROVAL";
  const canReceive = order?.status === "PLACED" || order?.status === "APPROVED";

  const quotes = useMemo(() => {
    if (!supplyCase) return [];
    return [...supplyCase.quotes].sort((a, b) => a.unit_price - b.unit_price);
  }, [supplyCase]);

  async function authorize() {
    if (!supplyCase) return;
    setWorking(true);
    try {
      await approvePurchaseOrder(supplyCase.id, "Authorized from operations command center");
      await refresh(supplyCase.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authorization failed");
    } finally {
      setWorking(false);
    }
  }

  async function markDelivered() {
    if (!supplyCase) return;
    setWorking(true);
    try {
      await receiveDelivery(supplyCase.id);
      await refresh(supplyCase.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not record the delivery");
    } finally {
      setWorking(false);
    }
  }

  return (
    <section className="flex flex-col">
      <Link
        href="/admin/inventory"
        className="focus-ink -mt-2 mb-2 inline-flex min-h-11 w-fit items-center gap-2 font-mono text-[11.5px] text-muted hover:text-ink"
      >
        <Icon name="arrowLeft" size={14} />
        Back to inventory
      </Link>

      <PageHeader
        eyebrow="Replenishment case"
        title={supplyCase ? supplyCase.item_name || supplyCase.sku : "Replenishment"}
        description={
          supplyCase
            ? `${supplyCase.sku} · opened ${formatWhen(supplyCase.opened_at)}`
            : "Loading case…"
        }
        density="dense"
        actions={
          supplyCase ? (
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge status={replenishmentStatus(supplyCase.status)} />
              <StatusBadge status={supplyUrgency(supplyCase.urgency)} />
            </div>
          ) : null
        }
      />

      {error ? <ErrorAlert message={error} /> : null}

      {loading ? (
        <CardSkeleton rows={6} />
      ) : supplyCase ? (
        <div className="flex flex-col gap-7">
          <section className="flex flex-col">
            <SectionHeader title="Why this case opened" />
            <p className="max-w-[74ch] text-[14px] leading-[1.6] text-secondary">
              {supplyCase.rationale}
            </p>
            <dl className="mt-4 grid grid-cols-[168px_minmax(0,1fr)] gap-x-5 gap-y-2 font-mono text-[13px]">
              <dt className="text-muted">requested_quantity</dt>
              <dd className="text-ink">{supplyCase.requested_quantity}</dd>
              <dt className="text-muted">suppliers_called</dt>
              <dd className="text-ink">{supplyCase.contacted_supplier_ids.length}</dd>
              <dt className="text-muted">assigned_agents</dt>
              <dd className="text-ink">{supplyCase.assigned_agents.join(" → ") || "—"}</dd>
            </dl>
          </section>

          {order ? (
            <section
              className={cn(
                "flex flex-col",
                awaitingApproval && "border-l-[3px] border-warn bg-warn-tint px-5 py-4",
              )}
            >
              <div className="flex items-baseline justify-between gap-4 border-b border-rule-strong pb-2.5">
                <h2 className="font-mono text-[10.5px] font-medium uppercase tracking-[0.1em] text-secondary">
                  Purchase order {order.id}
                </h2>
                <StatusBadge status={purchaseOrderStatus(order.status)} />
              </div>
              <p className="mt-3 max-w-[74ch] text-[13.5px] leading-[1.6] text-secondary">
                {awaitingApproval
                  ? "The agent drafted this order. Nothing is sent to the supplier until you authorize it."
                  : `Placed with ${order.supplier_name}.`}
              </p>
              <dl className="mt-4 grid grid-cols-[168px_minmax(0,1fr)] gap-x-5 gap-y-2 font-mono text-[13px]">
                <dt className="text-muted">supplier</dt>
                <dd className="text-ink">{order.supplier_name}</dd>
                <dt className="text-muted">quantity</dt>
                <dd className="text-ink">{order.quantity}</dd>
                <dt className="text-muted">unit_price</dt>
                <dd className="text-ink">
                  {order.unit_price.toFixed(2)} {order.currency}
                </dd>
                <dt className="text-muted">total_cost</dt>
                <dd className="text-ink">
                  {order.total_cost.toFixed(2)} {order.currency}
                </dd>
                {order.approved_by ? (
                  <>
                    <dt className="text-muted">authorized_by</dt>
                    <dd className="text-ink">
                      {order.approved_by} · {formatWhen(order.approved_at)}
                    </dd>
                    <dt className="text-muted">expected_delivery</dt>
                    <dd className="text-ink">{formatWhen(order.expected_delivery)}</dd>
                  </>
                ) : null}
              </dl>
              <div className="mt-5 flex flex-wrap gap-2">
                {awaitingApproval ? (
                  <Button onClick={() => void authorize()} disabled={working}>
                    <Icon name="approve" size={16} />
                    {working ? "Authorizing…" : "Authorize purchase order"}
                  </Button>
                ) : null}
                {canReceive ? (
                  <Button
                    variant="secondary"
                    onClick={() => void markDelivered()}
                    disabled={working}
                  >
                    {working ? "Recording…" : "Record delivery"}
                  </Button>
                ) : null}
              </div>
            </section>
          ) : null}

          {quotes.length ? (
            <section className="flex flex-col">
              <SectionHeader
                title="Supplier quotes"
                description="Recorded from the calls. The agent never states a figure a supplier did not give."
              />
              <div className="overflow-x-auto">
                <table className="w-full min-w-[38rem] border-collapse text-left">
                  <thead>
                    <tr className="border-b border-rule-strong">
                      {["Supplier", "Unit price", "Available", "Lead time", "Outcome"].map(
                        (head) => (
                          <th
                            key={head}
                            scope="col"
                            className="pb-2.5 pr-4 font-mono text-[10px] font-medium uppercase tracking-[0.1em] text-muted last:pr-0"
                          >
                            {head}
                          </th>
                        ),
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {quotes.map((quote) => {
                      const selected = order?.supplier_id === quote.supplier_id;
                      return (
                        <tr
                          key={quote.supplier_id}
                          className={cn(
                            "border-b border-rule",
                            selected && "bg-raised shadow-[inset_3px_0_0_0_var(--color-accent)]",
                          )}
                        >
                          <th
                            scope="row"
                            className={cn(
                              "min-h-11 py-3 pr-4 text-[14px] font-normal text-ink",
                              selected && "pl-2.5 font-medium",
                            )}
                          >
                            {quote.supplier_name}
                          </th>
                          <td className="py-3 pr-4 font-mono text-[13px] text-secondary">
                            {quote.unit_price.toFixed(2)} {quote.currency}
                          </td>
                          <td className="py-3 pr-4 font-mono text-[13px] text-secondary">
                            {quote.available_units}
                          </td>
                          <td className="py-3 pr-4 font-mono text-[13px] text-secondary">
                            {quote.lead_time_days}d
                          </td>
                          <td
                            className={cn(
                              "py-3 font-mono text-[12px]",
                              selected ? "text-ok" : "text-muted",
                            )}
                          >
                            {quoteNote(quote, supplyCase)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </section>
          ) : null}

          <section className="flex flex-col">
            <SectionHeader
              title="Audit timeline"
              description="Every step the supply fleet took on this case."
              meta={events.length ? `${events.length} events` : undefined}
            />
            <ol className="flex flex-col">
              {events.map((event) => {
                const label = eventLabel(event.event_type);
                return (
                  <li
                    key={event.event_id}
                    className="grid gap-2 border-b border-rule py-[18px] sm:grid-cols-[168px_minmax(0,1fr)] sm:gap-5"
                  >
                    <span className="flex flex-col gap-1">
                      <span className="font-mono text-[12px] text-muted">
                        {formatWhen(event.occurred_at)}
                      </span>
                      <span className="font-mono text-[11px] text-inactive">
                        {event.event_type}
                      </span>
                    </span>
                    <div className="min-w-0">
                      <p className="text-[15px] leading-[1.5] text-ink">{label.title}</p>
                      <p className="mt-1 text-[13.5px] leading-[1.55] text-secondary">
                        {label.description}
                      </p>
                      <p className="mt-2 font-mono text-[11.5px] text-muted">
                        outcome · {eventOutcome(event)}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </section>
        </div>
      ) : null}
    </section>
  );
}

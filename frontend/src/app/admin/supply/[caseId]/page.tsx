"use client";

import { ArrowLeft, PackageCheck, PhoneCall, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatusBadge } from "@/components/ui/StatusBadge";
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
  if (selected) return "Selected";
  if (quote.available_units < order.requested_quantity) {
    return `Can only ship ${quote.available_units} of ${order.requested_quantity}`;
  }
  return "Higher unit price";
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
    <section>
      <Link
        href="/admin/inventory"
        className="mb-4 inline-flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-slate-900"
      >
        <ArrowLeft aria-hidden className="h-4 w-4" />
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
        <CardSkeleton />
      ) : supplyCase ? (
        <div className="space-y-6">
          <Card className="border-teal-200 bg-gradient-to-br from-teal-50/80 to-white">
            <p className="text-xs uppercase tracking-wide text-teal-700">Why this case opened</p>
            <p className="mt-2 text-sm text-slate-700">{supplyCase.rationale}</p>
            <dl className="mt-4 grid gap-4 sm:grid-cols-3">
              <div>
                <dt className="text-xs text-slate-500">Requested</dt>
                <dd className="text-lg font-semibold text-slate-900">
                  {supplyCase.requested_quantity}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Suppliers called</dt>
                <dd className="text-lg font-semibold text-slate-900">
                  {supplyCase.contacted_supplier_ids.length}
                </dd>
              </div>
              <div>
                <dt className="text-xs text-slate-500">Agents involved</dt>
                <dd className="text-sm font-medium text-slate-900">
                  {supplyCase.assigned_agents.join(" → ") || "—"}
                </dd>
              </div>
            </dl>
          </Card>

          {order ? (
            <Card
              className={
                awaitingApproval ? "border-amber-200 bg-amber-50/60" : undefined
              }
            >
              <CardHeader
                title={`Purchase order ${order.id}`}
                description={
                  awaitingApproval
                    ? "The agent drafted this order. Nothing is sent to the supplier until you authorize it."
                    : `Placed with ${order.supplier_name}.`
                }
                action={<StatusBadge status={purchaseOrderStatus(order.status)} />}
              />
              <dl className="grid gap-4 sm:grid-cols-4">
                <div>
                  <dt className="text-xs text-slate-500">Supplier</dt>
                  <dd className="text-sm font-medium text-slate-900">{order.supplier_name}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Quantity</dt>
                  <dd className="text-sm font-medium text-slate-900">{order.quantity}</dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Unit price</dt>
                  <dd className="text-sm font-medium text-slate-900">
                    {order.unit_price.toFixed(2)} {order.currency}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-slate-500">Total</dt>
                  <dd className="text-base font-semibold text-slate-900">
                    {order.total_cost.toFixed(2)} {order.currency}
                  </dd>
                </div>
              </dl>
              {order.approved_by ? (
                <p className="mt-4 text-xs text-slate-500">
                  Authorized by {order.approved_by} on {formatWhen(order.approved_at)} · expected{" "}
                  {formatWhen(order.expected_delivery)}
                </p>
              ) : null}
              <div className="mt-5 flex flex-wrap gap-2">
                {awaitingApproval ? (
                  <Button onClick={() => void authorize()} disabled={working}>
                    <ShieldCheck aria-hidden className="h-4 w-4" />
                    {working ? "Authorizing…" : "Authorize purchase order"}
                  </Button>
                ) : null}
                {canReceive ? (
                  <Button
                    variant="secondary"
                    onClick={() => void markDelivered()}
                    disabled={working}
                  >
                    <PackageCheck aria-hidden className="h-4 w-4" />
                    {working ? "Recording…" : "Record delivery"}
                  </Button>
                ) : null}
              </div>
            </Card>
          ) : null}

          {quotes.length ? (
            <Card className="overflow-x-auto">
              <CardHeader
                title="Supplier quotes"
                description="Recorded from the calls. The agent never states a figure a supplier did not give."
              />
              <table className="w-full min-w-[38rem] text-left text-sm">
                <thead className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th scope="col" className="py-2 pr-4 font-medium">Supplier</th>
                    <th scope="col" className="py-2 pr-4 font-medium">Unit price</th>
                    <th scope="col" className="py-2 pr-4 font-medium">Available</th>
                    <th scope="col" className="py-2 pr-4 font-medium">Lead time</th>
                    <th scope="col" className="py-2 font-medium">Outcome</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {quotes.map((quote) => {
                    const selected = order?.supplier_id === quote.supplier_id;
                    return (
                      <tr key={quote.supplier_id} className={selected ? "bg-emerald-50/60" : undefined}>
                        <th scope="row" className="py-3 pr-4 font-normal text-slate-900">
                          {quote.supplier_name}
                        </th>
                        <td className="py-3 pr-4 text-slate-700">
                          {quote.unit_price.toFixed(2)} {quote.currency}
                        </td>
                        <td className="py-3 pr-4 text-slate-700">{quote.available_units}</td>
                        <td className="py-3 pr-4 text-slate-700">{quote.lead_time_days} days</td>
                        <td className="py-3 text-slate-600">{quoteNote(quote, supplyCase)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Card>
          ) : null}

          <Card>
            <CardHeader
              title="Audit timeline"
              description="Every step the supply fleet took on this case."
            />
            <ol className="space-y-4">
              {events.map((event) => {
                const label = eventLabel(event.event_type);
                return (
                  <li key={event.event_id} className="flex gap-3">
                    <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-teal-50 text-teal-800">
                      <PhoneCall aria-hidden className="h-4 w-4" />
                    </span>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-900">{label.title}</p>
                      <p className="text-sm text-slate-600">{label.description}</p>
                      <p className="mt-0.5 text-xs text-slate-500">
                        {eventOutcome(event)} · {formatWhen(event.occurred_at)}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ol>
          </Card>
        </div>
      ) : null}
    </section>
  );
}

"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { FilterChips } from "@/components/ui/FilterChips";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/PageHeader";
import { SearchInput } from "@/components/ui/SearchInput";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatCard, StatStrip } from "@/components/ui/StatCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ERROR_MESSAGES, getErrorMessage } from "@/lib/errors";
import {
  purchaseOrderStatus,
  replenishmentStatus,
  stockStatus,
  supplyUrgency,
} from "@/lib/statusLabels";
import { listInventory, listReplenishmentCases } from "@/services/api";
import type { InventoryItem, ReplenishmentCase } from "@/types";

type StockFilter = "all" | "attention" | "critical";

const CLOSED_CASES = new Set(["COMPLETED", "CANCELLED"]);

function coverLabel(item: InventoryItem): string {
  if (item.days_of_cover === null) return "usage not recorded";
  return `${item.days_of_cover}d cover`;
}

export default function AdminInventoryPage() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const [cases, setCases] = useState<ReplenishmentCase[]>([]);
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<StockFilter>("all");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    setLoading(true);
    setError(null);
    try {
      const [inventoryItems, caseItems] = await Promise.all([
        listInventory(),
        listReplenishmentCases(),
      ]);
      setItems(inventoryItems);
      setCases(caseItems);
    } catch (err) {
      setError(getErrorMessage(err, ERROR_MESSAGES.inventory));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void refresh();
  }, []);

  const openCases = useMemo(
    () => cases.filter((item) => !CLOSED_CASES.has(item.status)),
    [cases],
  );

  const caseBySku = useMemo(() => {
    const map: Record<string, ReplenishmentCase> = {};
    for (const item of openCases) {
      map[item.sku] = item;
    }
    return map;
  }, [openCases]);

  const lowStock = useMemo(
    () => items.filter((item) => item.on_hand <= item.reorder_point),
    [items],
  );

  const awaitingApproval = useMemo(
    () => openCases.filter((item) => item.status === "AWAITING_APPROVAL"),
    [openCases],
  );

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return items
      .filter((item) => {
        const matchesQuery =
          !q ||
          item.name.toLowerCase().includes(q) ||
          item.sku.toLowerCase().includes(q) ||
          item.form.toLowerCase().includes(q);
        const matchesFilter =
          filter === "all" ||
          (filter === "attention" && item.on_hand <= item.reorder_point) ||
          (filter === "critical" &&
            (item.status === "CRITICAL" || item.status === "OUT_OF_STOCK"));
        return matchesQuery && matchesFilter;
      })
      .sort((a, b) => {
        const aRatio = a.reorder_point ? a.on_hand / a.reorder_point : 99;
        const bRatio = b.reorder_point ? b.on_hand / b.reorder_point : 99;
        return aRatio - bRatio;
      });
  }, [items, query, filter]);

  return (
    <section className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Operations"
        title="Pharmacy inventory"
        description="Stock the clinic dispenses to patients. When a medication crosses its reorder point, the supply fleet sources it and brings back a purchase order for authorization."
        density="dense"
        actions={
          <Button variant="secondary" onClick={() => void refresh()} disabled={loading}>
            <span className={loading ? "inline-flex motion-safe:animate-spin" : "inline-flex"}>
              <Icon name="refresh" size={16} />
            </span>
            {loading ? "Refreshing…" : "Refresh"}
          </Button>
        }
      />

      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}

      <StatStrip className="sm:grid-cols-3">
        <StatCard
          label="Below reorder point"
          value={lowStock.length}
          tone={lowStock.length ? "warn" : "ok"}
          hint={lowStock.length ? "the supply fleet is sourcing these" : "every medication is stocked"}
        />
        <StatCard
          label="Open replenishments"
          value={openCases.length}
          hint="cases the fleet is working right now"
        />
        <StatCard
          label="Awaiting authorization"
          value={awaitingApproval.length}
          tone={awaitingApproval.length ? "high" : "ok"}
          hint={
            awaitingApproval.length
              ? "no order is placed until you authorize it"
              : "nothing is waiting on a person"
          }
        />
      </StatStrip>

      {awaitingApproval.length ? (
        <section className="flex flex-col">
          <SectionHeader
            level="major"
            title="Purchase orders waiting on you"
            description="The procurement agent drafted these. No order is placed until an operations admin authorizes it."
          />
          <ul className="flex flex-col">
            {awaitingApproval.map((item) => (
              <li key={item.id}>
                <Link
                  href={`/admin/supply/${item.id}`}
                  className="focus-ink grid min-h-11 grid-cols-[minmax(0,1fr)_auto] items-center gap-4 border-b border-rule py-2 hover:bg-hover"
                >
                  <span className="flex min-w-0 flex-col gap-0.5">
                    <span className="truncate text-[0.875rem] text-ink">
                      {item.item_name || item.sku}
                    </span>
                    <span className="truncate font-mono text-[11.5px] text-muted">
                      {item.purchase_order
                        ? `${item.purchase_order.id} · ${item.purchase_order.quantity} units · ${item.purchase_order.supplier_name} · ${item.purchase_order.total_cost.toFixed(2)} ${item.purchase_order.currency}`
                        : "draft pending"}
                    </span>
                  </span>
                  <span className="flex shrink-0 items-center gap-2.5">
                    <StatusBadge status={supplyUrgency(item.urgency)} />
                    <Icon name="chevronRight" size={14} className="text-muted" />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <div className="flex flex-col gap-4">
        <SearchInput
          placeholder="Search medication, SKU, or form"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          className="max-w-md"
        />
        <FilterChips<StockFilter>
          label="Stock level"
          value={filter}
          onChange={setFilter}
          options={[
            { id: "all", label: "All medications" },
            { id: "attention", label: "Needs replenishment" },
            { id: "critical", label: "Critically low" },
          ]}
        />
      </div>

      {loading ? (
        <CardSkeleton rows={6} />
      ) : rows.length ? (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[52rem] border-collapse text-left">
            <thead>
              <tr className="border-b border-rule-strong">
                {[
                  "Medication",
                  "On hand",
                  "Reorder point",
                  "Cover",
                  "Patients",
                  "Status",
                  "Replenishment",
                ].map((head) => (
                  <th
                    key={head}
                    scope="col"
                    className="pb-2.5 pr-4 font-mono text-[0.75rem] font-medium uppercase tracking-[0.1em] text-muted last:pr-0"
                  >
                    {head}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((item) => {
                const activeCase = caseBySku[item.sku];
                return (
                  <tr key={item.sku} className="border-b border-rule align-middle">
                    <th scope="row" className="py-2.5 pr-4 font-normal">
                      <span className="flex min-h-11 flex-col justify-center gap-0.5">
                        <span className="flex items-center gap-2.5">
                          <span className="text-[0.875rem] text-ink">{item.name}</span>
                          {item.critical ? (
                            <StatusBadge status={{ label: "Critical", tone: "danger" }} />
                          ) : null}
                        </span>
                        <span className="font-mono text-[11.5px] text-muted">
                          {item.form || item.sku}
                        </span>
                      </span>
                    </th>
                    <td className="py-2.5 pr-4 font-mono text-[0.8125rem] text-ink">
                      {item.on_hand}
                      <span className="ml-1 text-[0.75rem] text-muted">{item.unit}</span>
                    </td>
                    <td className="py-2.5 pr-4 font-mono text-[0.8125rem] text-secondary">
                      {item.reorder_point}
                    </td>
                    <td className="py-2.5 pr-4 font-mono text-[0.75rem] text-secondary">
                      {coverLabel(item)}
                    </td>
                    <td className="py-2.5 pr-4 font-mono text-[0.8125rem] text-secondary">
                      {item.patient_count ?? 0}
                    </td>
                    <td className="py-2.5 pr-4">
                      <StatusBadge status={stockStatus(item.status)} />
                    </td>
                    <td className="py-2.5">
                      {activeCase ? (
                        <Link
                          href={`/admin/supply/${activeCase.id}`}
                          className="focus-ink inline-flex min-h-11 items-center gap-2 hover:text-ink"
                        >
                          <StatusBadge status={replenishmentStatus(activeCase.status)} />
                          {activeCase.purchase_order ? (
                            <StatusBadge
                              status={purchaseOrderStatus(activeCase.purchase_order.status)}
                            />
                          ) : null}
                        </Link>
                      ) : (
                        <span className="font-mono text-[11.5px] text-inactive">none open</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <EmptyState
          title="No medications match"
          description="Adjust the search or filter to see stock."
        />
      )}
    </section>
  );
}

"use client";

import { AlertTriangle, ArrowRight, Package, PhoneCall, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { FilterChips } from "@/components/ui/FilterChips";
import { PageHeader } from "@/components/ui/PageHeader";
import { SearchInput } from "@/components/ui/SearchInput";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { StatCard } from "@/components/ui/StatCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
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
  if (item.days_of_cover === null) return "Usage not recorded";
  return `${item.days_of_cover} days of cover`;
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
      setError(err instanceof Error ? err.message : "Could not load inventory");
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
    <section className="space-y-6">
      <PageHeader
        eyebrow="Operations"
        title="Pharmacy inventory"
        description="Stock the clinic dispenses to patients. When a medication crosses its reorder point, the supply fleet sources it and brings back a purchase order for authorization."
        actions={
          <Button variant="secondary" onClick={() => void refresh()} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </Button>
        }
      />

      {error ? <ErrorAlert message={error} onRetry={() => void refresh()} /> : null}

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Below reorder point"
          value={lowStock.length}
          icon={AlertTriangle}
          hint={lowStock.length ? "Supply fleet is sourcing" : "All medications stocked"}
        />
        <StatCard
          label="Open replenishments"
          value={openCases.length}
          icon={PhoneCall}
          hint="Cases the fleet is working"
        />
        <StatCard
          label="Awaiting authorization"
          value={awaitingApproval.length}
          icon={ShieldCheck}
          hint="Orders that need a human"
        />
      </div>

      {awaitingApproval.length ? (
        <Card className="border-amber-200 bg-amber-50/60">
          <CardHeader
            title="Purchase orders waiting on you"
            description="The procurement agent drafted these. No order is placed until an operations admin authorizes it."
          />
          <ul className="space-y-2">
            {awaitingApproval.map((item) => (
              <li key={item.id}>
                <Link
                  href={`/admin/supply/${item.id}`}
                  className="flex items-center justify-between gap-3 rounded-xl bg-white px-4 py-3 ring-1 ring-amber-200 transition hover:ring-amber-300"
                >
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium text-slate-900">
                      {item.item_name || item.sku}
                    </span>
                    <span className="block text-xs text-slate-500">
                      {item.purchase_order
                        ? `${item.purchase_order.id} · ${item.purchase_order.quantity} units from ${item.purchase_order.supplier_name} · ${item.purchase_order.total_cost.toFixed(2)} ${item.purchase_order.currency}`
                        : "Draft pending"}
                    </span>
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    <StatusBadge status={supplyUrgency(item.urgency)} />
                    <ArrowRight aria-hidden className="h-4 w-4 text-slate-400" />
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      <SearchInput
        placeholder="Search medication, SKU, or form"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
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

      {loading ? (
        <CardSkeleton />
      ) : rows.length ? (
        <Card className="overflow-x-auto p-0">
          <table className="w-full min-w-[46rem] text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50/80 text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th scope="col" className="px-5 py-3 font-medium">Medication</th>
                <th scope="col" className="px-5 py-3 font-medium">On hand</th>
                <th scope="col" className="px-5 py-3 font-medium">Reorder point</th>
                <th scope="col" className="px-5 py-3 font-medium">Cover</th>
                <th scope="col" className="px-5 py-3 font-medium">Status</th>
                <th scope="col" className="px-5 py-3 font-medium">Replenishment</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {rows.map((item) => {
                const activeCase = caseBySku[item.sku];
                return (
                  <tr key={item.sku} className="align-middle">
                    <th scope="row" className="px-5 py-4 font-normal">
                      <span className="block text-sm font-medium text-slate-900">
                        {item.name}
                        {item.critical ? (
                          <span className="ml-2 rounded-full bg-rose-50 px-2 py-0.5 text-[11px] font-medium text-rose-700 ring-1 ring-inset ring-rose-200">
                            Critical
                          </span>
                        ) : null}
                      </span>
                      <span className="block text-xs text-slate-500">
                        {item.form || item.sku}
                      </span>
                    </th>
                    <td className="px-5 py-4 text-slate-900">
                      {item.on_hand}
                      <span className="ml-1 text-xs text-slate-500">{item.unit}</span>
                    </td>
                    <td className="px-5 py-4 text-slate-600">{item.reorder_point}</td>
                    <td className="px-5 py-4 text-slate-600">{coverLabel(item)}</td>
                    <td className="px-5 py-4">
                      <StatusBadge status={stockStatus(item.status)} />
                    </td>
                    <td className="px-5 py-4">
                      {activeCase ? (
                        <Link
                          href={`/admin/supply/${activeCase.id}`}
                          className="inline-flex items-center gap-2 text-sm font-medium text-teal-800 hover:underline"
                        >
                          <StatusBadge status={replenishmentStatus(activeCase.status)} />
                          {activeCase.purchase_order ? (
                            <StatusBadge
                              status={purchaseOrderStatus(activeCase.purchase_order.status)}
                            />
                          ) : null}
                        </Link>
                      ) : (
                        <span className="text-xs text-slate-400">None open</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
      ) : (
        <EmptyState
          icon={Package}
          title="No medications match"
          description="Adjust the search or filter to see stock."
        />
      )}
    </section>
  );
}

"use client";

import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { Icon, type IconName } from "@/components/ui/Icon";
import { UI_TIMING } from "@/config/app";
import { cn } from "@/lib/cn";

type ToastTone = "success" | "error";

interface ToastItem {
  id: number;
  message: string;
  tone: ToastTone;
}

interface ToastContextValue {
  toast: (message: string, tone?: ToastTone) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const TOAST_VIEW: Record<ToastTone, { border: string; icon: IconName; label: string }> = {
  success: { border: "border-ok", icon: "checkCircle", label: "Done" },
  error: { border: "border-high", icon: "alertCircle", label: "Failed" },
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);

  const toast = useCallback((message: string, tone: ToastTone = "success") => {
    const id = Date.now() + Math.random();
    setItems((prev) => [...prev, { id, message, tone }]);
    window.setTimeout(() => {
      setItems((prev) => prev.filter((item) => item.id !== id));
    }, UI_TIMING.toast);
  }, []);

  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-[min(100%-2rem,22rem)] flex-col gap-2"
        aria-live="polite"
        aria-relevant="additions"
      >
        {items.map((item) => {
          const view = TOAST_VIEW[item.tone];
          return (
            <div
              key={item.id}
              role="status"
              className={cn(
                "eir-enter pointer-events-auto flex items-start gap-3 rounded-xl border bg-ink px-4 py-3 shadow-[0_18px_48px_rgb(10_23_40/0.28)]",
                view.border,
              )}
            >
              <Icon name={view.icon} size={18} className="mt-0.5 text-paper" />
              <span className="flex min-w-0 flex-col gap-1">
                <span className="font-mono text-[10.5px] uppercase tracking-[0.1em] text-on-ink-muted">
                  {view.label}
                </span>
                <span className="text-[13.5px] leading-snug text-on-ink">{item.message}</span>
              </span>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const value = useContext(ToastContext);
  if (!value) {
    return {
      toast: () => undefined,
    };
  }
  return value;
}

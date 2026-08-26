"use client";

import { useEffect, useRef, useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { cn } from "@/lib/cn";
import { loadSession } from "@/lib/auth";
import { createAccessSession, sendAccessMessage } from "@/services/api";

type ChatMessage = { role: "user" | "assistant"; text: string };

const SUGGESTIONS = [
  "Show my appointments",
  "Find cardiology availability",
  "Reschedule my next appointment",
  "How is my recovery going?",
];

export default function PatientAssistantPage() {
  const session = loadSession();
  const [sessionId, setSessionId] = useState("");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: "assistant",
      text: "Hi, I'm EIR. I can help with appointments, reminders, recovery routing, or connect you with staff.",
    },
  ]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    void createAccessSession()
      .then((access) => setSessionId(access.id))
      .catch((err) => setError(err instanceof Error ? err.message : "Could not start assistant"));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function send(textValue?: string) {
    const text = (textValue ?? input).trim();
    if (!text || !sessionId || busy) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text }]);
    setBusy(true);
    setError(null);
    try {
      const response = await sendAccessMessage(sessionId, text);
      setMessages((prev) => [...prev, { role: "assistant", text: response.reply }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Message failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="flex flex-col">
      <PageHeader
        eyebrow="Ask EIR"
        title="Hospital assistant"
        description="Ask about appointments, availability, or recovery. Nothing here is a stored transcript."
        density="patient"
      />

      {error ? <ErrorAlert message={error} /> : null}

      <div className="flex min-h-[28rem] flex-col border-t border-rule-strong">
        <div
          className="flex flex-1 flex-col gap-5 overflow-y-auto py-6"
          aria-live="polite"
        >
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={cn(
                "flex max-w-[85%] gap-3",
                message.role === "user" && "ml-auto flex-row-reverse",
              )}
            >
              {message.role === "assistant" ? (
                <span
                  aria-hidden
                  className="inline-flex h-8 w-8 shrink-0 items-center justify-center bg-accent font-mono text-[11px] tracking-[0.06em] text-paper"
                >
                  EIR
                </span>
              ) : (
                <Avatar name={session?.display_name ?? "You"} size="sm" />
              )}
              <p
                className={cn(
                  "px-4 py-3 text-[15px] leading-[1.6]",
                  message.role === "user"
                    ? "on-raised bg-raised text-body"
                    : "border-l-[3px] border-accent text-body",
                )}
              >
                {message.text}
              </p>
            </div>
          ))}
          {busy ? (
            <p className="font-mono text-[12px] text-muted">EIR is typing…</p>
          ) : null}
          <div ref={endRef} />
        </div>

        <div className="flex flex-wrap gap-2 border-t border-rule pt-4">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => void send(suggestion)}
              className="focus-ink inline-flex min-h-11 items-center border border-rule-strong px-3.5 text-[13px] text-secondary hover:bg-hover hover:text-ink"
            >
              {suggestion}
            </button>
          ))}
        </div>

        <form
          className="mt-4 flex flex-col gap-3 sm:flex-row"
          onSubmit={(event) => {
            event.preventDefault();
            void send();
          }}
        >
          <label className="sr-only" htmlFor="assistant-input">
            Message EIR
          </label>
          <input
            id="assistant-input"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask about an appointment or recovery"
            className="focus-ink h-11 flex-1 border border-rule-strong bg-paper px-4 text-[15px] text-ink placeholder:text-muted focus:border-accent"
          />
          <Button type="submit" disabled={busy || !sessionId}>
            {busy ? "Sending…" : "Send"}
          </Button>
        </form>
      </div>
    </section>
  );
}

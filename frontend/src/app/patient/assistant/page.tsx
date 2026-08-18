"use client";

import { MessageCircle } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
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
    <section className="space-y-6">
      <PageHeader
        eyebrow="Ask EIR"
        title="Hospital assistant"
        description="Ask about appointments, availability, or recovery. Nothing here is a stored transcript."
      />
      {error ? <ErrorAlert message={error} /> : null}
      <Card className="flex min-h-[28rem] flex-col">
        <div className="flex-1 space-y-4 overflow-y-auto rounded-xl bg-slate-50 p-4" aria-live="polite">
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`flex max-w-[85%] items-end gap-2 ${
                message.role === "user" ? "ml-auto flex-row-reverse" : ""
              }`}
            >
              {message.role === "assistant" ? (
                <span className="flex h-8 w-8 items-center justify-center rounded-full bg-teal-700 text-white">
                  <MessageCircle aria-hidden className="h-4 w-4" />
                </span>
              ) : (
                <Avatar name={session?.display_name ?? "You"} size="sm" />
              )}
              <div
                className={`rounded-2xl px-4 py-3 text-sm leading-6 ${
                  message.role === "user"
                    ? "bg-teal-700 text-white"
                    : "bg-white text-slate-800 ring-1 ring-slate-200"
                }`}
              >
                {message.text}
              </div>
            </div>
          ))}
          {busy ? (
            <p className="text-sm text-slate-500">EIR is typing…</p>
          ) : null}
          <div ref={endRef} />
        </div>
        <div className="mt-4 flex flex-wrap gap-2">
          {SUGGESTIONS.map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => void send(suggestion)}
              className="rounded-full bg-white px-3 py-2 text-xs font-medium text-slate-600 ring-1 ring-slate-200 hover:bg-teal-50 hover:text-teal-800"
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
            className="h-11 flex-1 rounded-xl border border-slate-200 px-4 text-sm focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-100"
          />
          <Button type="submit" disabled={busy || !sessionId}>
            {busy ? "Sending…" : "Send"}
          </Button>
        </form>
      </Card>
    </section>
  );
}

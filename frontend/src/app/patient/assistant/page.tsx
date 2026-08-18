"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/Button";
import { Card, CardHeader } from "@/components/ui/Card";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { PageHeader } from "@/components/ui/PageHeader";
import { createAccessSession, sendAccessMessage } from "@/services/api";

type ChatMessage = { role: "user" | "assistant"; text: string };

export default function PatientAssistantPage() {
  const [sessionId, setSessionId] = useState<string>("");
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
      .then((session) => setSessionId(session.id))
      .catch((err) => setError(err instanceof Error ? err.message : "Could not start assistant"));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send() {
    const text = input.trim();
    if (!text || !sessionId) return;
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text }]);
    setBusy(true);
    setError(null);
    try {
      const response = await sendAccessMessage(sessionId, text);
      setMessages((prev) => [...prev, { role: "assistant", text: response.reply }]);
      if (response.route) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", text: `You can continue in ${response.route}.` },
        ]);
      }
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
        description="Text is available now. Voice calling will use the same access service when live funds return."
      />
      {error ? <ErrorAlert message={error} /> : null}
      <Card className="flex min-h-[420px] flex-col">
        <CardHeader title="Conversation" description="No full transcript is stored on the server." />
        <div className="flex-1 space-y-4 overflow-y-auto rounded-xl bg-slate-50 p-4" aria-live="polite">
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-6 ${
                message.role === "user"
                  ? "ml-auto bg-teal-700 text-white"
                  : "bg-white text-slate-800 ring-1 ring-slate-200"
              }`}
            >
              {message.text}
            </div>
          ))}
          <div ref={endRef} />
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
            placeholder="Example: Move my cardiology appointment to next Tuesday afternoon."
            className="flex-1 rounded-xl border border-slate-200 px-4 py-3 text-sm focus:border-teal-600 focus:outline-none focus:ring-2 focus:ring-teal-100"
          />
          <Button type="submit" disabled={busy || !sessionId}>
            Send
          </Button>
        </form>
      </Card>
      <p className="text-sm text-slate-500">
        Developer voice preview lives at{" "}
        <Link href="/dev/voice-preview" className="font-medium text-teal-700">
          /dev/voice-preview
        </Link>
        . Live audio is not verified this sprint.
      </p>
    </section>
  );
}

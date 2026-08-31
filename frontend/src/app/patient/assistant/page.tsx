"use client";

import { useEffect, useRef, useState } from "react";

import { Avatar } from "@/components/ui/Avatar";
import { Button } from "@/components/ui/Button";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Icon } from "@/components/ui/Icon";
import { PageHeader } from "@/components/ui/PageHeader";
import { cn } from "@/lib/cn";
import { loadSession } from "@/lib/auth";
import { ERROR_MESSAGES, getErrorMessage } from "@/lib/errors";
import { createAccessSession, sendAccessMessage } from "@/services/api";

const CHAT_ROLE = {
  assistant: "assistant",
  user: "user",
} as const;

type ChatRole = (typeof CHAT_ROLE)[keyof typeof CHAT_ROLE];
type ChatMessage = { role: ChatRole; text: string };

const CHAT_COPY = {
  intro:
    "Hi, I'm EIR. I can help with appointments, reminders, recovery routing, or connect you with staff.",
  typing: "EIR is typing…",
} as const;

const SUGGESTIONS = [
  "Show my appointments",
  "Find cardiology availability",
  "Reschedule my next appointment",
  "How is my recovery going?",
] as const;

function MessageBubble({
  message,
  patientName,
}: {
  message: ChatMessage;
  patientName: string;
}) {
  const isUser = message.role === CHAT_ROLE.user;

  return (
    <div className={cn("flex max-w-[85%] gap-3", isUser && "ml-auto flex-row-reverse")}>
      {isUser ? (
        <Avatar name={patientName} size="sm" />
      ) : (
        <span
          aria-hidden
          className="eir-chip inline-flex h-8 w-8 shrink-0 items-center justify-center bg-accent text-paper"
        >
          <Icon name="assistant" size={16} />
        </span>
      )}
      <p
        className={cn(
          "eir-message border px-4 py-3 text-[0.9375rem] leading-[1.6] shadow-[0_6px_18px_rgb(22_75_130/0.05)]",
          isUser
            ? "border-rule bg-raised text-body"
            : "border-accent/20 bg-accent-tint/45 text-body",
        )}
      >
        {message.text}
      </p>
    </div>
  );
}

function SuggestionChip({ label, onSelect }: { label: string; onSelect: () => void }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      className="eir-control focus-ink inline-flex min-h-11 items-center gap-2 border border-rule-strong bg-surface/70 px-3.5 text-[0.8125rem] text-secondary hover:border-accent/30 hover:bg-accent-tint hover:text-ink"
    >
      <Icon name="sparkles" size={14} />
      {label}
    </button>
  );
}

export default function PatientAssistantPage() {
  const [session, setSession] = useState<ReturnType<typeof loadSession>>(null);
  const [sessionId, setSessionId] = useState("");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      role: CHAT_ROLE.assistant,
      text: CHAT_COPY.intro,
    },
  ]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => setSession(loadSession()), []);

  useEffect(() => {
    void createAccessSession()
      .then((access) => setSessionId(access.id))
      .catch((err) => setError(getErrorMessage(err, ERROR_MESSAGES.assistant)));
  }, []);

  const scrolled = useRef(false);
  useEffect(() => {
    if (!scrolled.current) {
      scrolled.current = true;
      return;
    }
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [messages, busy]);

  async function send(textValue?: string) {
    const text = (textValue ?? input).trim();
    if (!text || !sessionId || busy) return;
    setInput("");
    setMessages((prev) => [...prev, { role: CHAT_ROLE.user, text }]);
    setBusy(true);
    setError(null);
    try {
      const response = await sendAccessMessage(sessionId, text);
      setMessages((prev) => [
        ...prev,
        { role: CHAT_ROLE.assistant, text: response.reply },
      ]);
    } catch (err) {
      setError(getErrorMessage(err, ERROR_MESSAGES.message));
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

      <div className="eir-surface on-surface flex min-h-[28rem] flex-col overflow-hidden p-4 sm:p-6">
        <div
          className="flex flex-1 flex-col gap-5 overflow-y-auto py-6"
          aria-live="polite"
        >
          {messages.map((message, index) => (
            <MessageBubble
              key={`${message.role}-${index}`}
              message={message}
              patientName={session?.display_name ?? "You"}
            />
          ))}
          {busy ? (
            <p className="font-mono text-[0.75rem] text-muted">{CHAT_COPY.typing}</p>
          ) : null}
          <div ref={endRef} />
        </div>

        <div className="flex flex-wrap gap-2 border-t border-rule pt-4">
          {SUGGESTIONS.map((suggestion) => (
            <SuggestionChip
              key={suggestion}
              label={suggestion}
              onSelect={() => void send(suggestion)}
            />
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
            className="eir-control focus-ink h-11 flex-1 border border-rule-strong bg-paper px-4 text-[0.9375rem] text-ink placeholder:text-muted focus:border-accent"
          />
          <Button type="submit" disabled={busy || !sessionId}>
            <Icon name="send" size={16} />
            {busy ? "Sending…" : "Send"}
          </Button>
        </form>
      </div>
    </section>
  );
}

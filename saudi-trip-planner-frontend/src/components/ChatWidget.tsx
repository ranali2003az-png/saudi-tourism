import { useState, useRef, useEffect } from "react";
import { askAssistant, ApiError } from "../lib/api";
import type { ChatMessage, TripPreferences } from "../lib/types";

export default function ChatWidget({
  prefs,
  excludedPlaces,
}: {
  prefs: TripPreferences;
  excludedPlaces: string[];
}) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, open]);

  async function send() {
    const text = input.trim();
    if (!text || sending) return;
    setInput("");
    setMessages((cur) => [...cur, { role: "user", text }]);
    setSending(true);
    try {
      const { reply } = await askAssistant(text, prefs, excludedPlaces);
      setMessages((cur) => [...cur, { role: "assistant", text: reply }]);
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : "Couldn't reach the assistant. Is the backend running?";
      setMessages((cur) => [...cur, { role: "assistant", text: msg }]);
    } finally {
      setSending(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-6 right-6 z-50 bg-palm-600 hover:bg-palm-700 text-sand-50 rounded-full h-14 w-14 shadow-lg flex items-center justify-center text-2xl transition-colors"
        aria-label="Open trip assistant chat"
      >
        💬
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-[340px] max-w-[calc(100vw-2rem)] bg-white rounded-2xl shadow-xl border border-ink-900/10 flex flex-col overflow-hidden">
      <div className="bg-palm-600 text-sand-50 px-4 py-3 flex items-center justify-between">
        <span className="font-body font-medium text-sm">🤖 Trip Assistant</span>
        <button onClick={() => setOpen(false)} aria-label="Close chat" className="text-sand-50/90 hover:text-sand-50 text-lg leading-none">
          ✕
        </button>
      </div>

      <div ref={scrollRef} className="flex-1 max-h-80 overflow-y-auto px-4 py-3 space-y-2 bg-sand-100">
        {messages.length === 0 && (
          <p className="text-sm text-ink-700/70 font-body">
            Ask about your itinerary — hours, prices, why a place was recommended, or say "remove X".
          </p>
        )}
        {messages.map((m, i) => (
          <div
            key={i}
            className={`text-sm font-body rounded-xl px-3 py-2 max-w-[85%] whitespace-pre-wrap ${
              m.role === "user" ? "bg-palm-600 text-sand-50 ml-auto" : "bg-white text-ink-900 border border-ink-900/10"
            }`}
          >
            {m.text}
          </div>
        ))}
        {sending && <div className="text-sm text-ink-700/60 font-body px-3">Typing…</div>}
      </div>

      <div className="border-t border-ink-900/10 p-2 flex gap-2 bg-white">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask a question…"
          className="flex-1 border border-ink-900/15 rounded-full px-3 py-2 text-sm font-body outline-none focus:border-palm-600"
        />
        <button
          onClick={send}
          disabled={sending || !input.trim()}
          className="bg-palm-600 hover:bg-palm-700 disabled:opacity-50 text-sand-50 rounded-full px-4 text-sm font-body"
        >
          Send
        </button>
      </div>
    </div>
  );
}

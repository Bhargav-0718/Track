"use client";

import {
  useState, useRef, useEffect, useCallback,
} from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Send, Trash2, Dumbbell, Footprints, Flame,
  ChevronDown, Bot,
} from "lucide-react";
import { useSWRConfig } from "swr";

import { getCoachHistory, clearCoachHistory, sendCoachMessage } from "@/lib/api/coach";
import { cn } from "@/lib/utils/format";
import type { ChatBubble, CoachSSEEvent } from "@/lib/types";

const uid = () => crypto.randomUUID();

// ── Starters ──────────────────────────────────────────────────────────────────

const STARTERS = [
  "I had poha for breakfast 🍽️",
  "Just finished a 45 min strength session 💪",
  "What did I eat today?",
  "I walked 8000 steps today 🚶",
];

// ── Action Event Card ─────────────────────────────────────────────────────────

function ActionCard({ event }: { event: CoachSSEEvent }) {
  if (event.type === "food_logged") {
    return (
      <div className="flex items-center gap-2 mt-2 px-3 py-2 rounded-xl
                      bg-emerald-500/10 border border-emerald-500/20 text-sm">
        <Flame className="w-4 h-4 text-emerald-400 shrink-0" />
        <span className="text-emerald-300 font-medium">Logged</span>
        <span className="text-text-secondary truncate">{event.food_name}</span>
        <span className="ml-auto text-emerald-400 font-semibold shrink-0">
          {event.calories} kcal
        </span>
      </div>
    );
  }

  if (event.type === "workout_logged") {
    return (
      <div className="flex items-center gap-2 mt-2 px-3 py-2 rounded-xl
                      bg-indigo-500/10 border border-indigo-500/20 text-sm">
        <Dumbbell className="w-4 h-4 text-indigo-400 shrink-0" />
        <span className="text-indigo-300 font-medium">Logged</span>
        <span className="text-text-secondary capitalize">{event.workout_type}</span>
        <span className="text-text-muted">{event.duration_minutes} min</span>
        {event.calories_burned > 0 && (
          <span className="ml-auto text-indigo-400 font-semibold shrink-0">
            -{event.calories_burned} kcal
          </span>
        )}
      </div>
    );
  }

  if (event.type === "steps_logged") {
    return (
      <div className="flex items-center gap-2 mt-2 px-3 py-2 rounded-xl
                      bg-blue-500/10 border border-blue-500/20 text-sm">
        <Footprints className="w-4 h-4 text-blue-400 shrink-0" />
        <span className="text-blue-300 font-medium">Logged</span>
        <span className="text-text-secondary">
          {event.steps.toLocaleString()} steps
        </span>
      </div>
    );
  }

  return null;
}

// ── Typing Indicator ──────────────────────────────────────────────────────────

function TypingDots() {
  return (
    <div className="flex items-center gap-1 py-1 px-1">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="w-2 h-2 rounded-full bg-text-muted"
          animate={{ opacity: [0.3, 1, 0.3], y: [0, -4, 0] }}
          transition={{ duration: 1, delay: i * 0.2, repeat: Infinity }}
        />
      ))}
    </div>
  );
}

// ── Message Bubble ────────────────────────────────────────────────────────────

function MessageBubble({ bubble }: { bubble: ChatBubble }) {
  const isUser = bubble.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn("flex gap-2", isUser ? "justify-end" : "justify-start")}
    >
      {/* Avatar — coach only */}
      {!isUser && (
        <div className="w-8 h-8 rounded-xl bg-indigo-gradient flex items-center
                        justify-center shrink-0 mt-0.5 shadow-glow-indigo">
          <Bot className="w-4 h-4 text-white" />
        </div>
      )}

      <div className={cn("max-w-[80%] flex flex-col", isUser && "items-end")}>
        {/* Bubble */}
        <div
          className={cn(
            "px-4 py-3 rounded-2xl text-sm leading-relaxed",
            isUser
              ? "bg-emerald-500 text-white rounded-br-sm"
              : "bg-surface-elevated border border-border text-text-primary rounded-bl-sm"
          )}
        >
          {bubble.streaming && bubble.content === "" ? (
            <TypingDots />
          ) : (
            <span style={{ whiteSpace: "pre-wrap" }}>{bubble.content}</span>
          )}
          {bubble.streaming && bubble.content !== "" && (
            <span className="inline-block w-0.5 h-3.5 bg-current ml-0.5
                             align-middle animate-pulse rounded-full" />
          )}
        </div>

        {/* Action event cards */}
        {bubble.actionEvents && bubble.actionEvents.length > 0 && (
          <div className="w-full mt-1 space-y-1">
            {bubble.actionEvents.map((ev, i) => (
              <ActionCard key={i} event={ev} />
            ))}
          </div>
        )}

        {/* Timestamp */}
        <span className="text-[10px] text-text-muted mt-1 px-1">
          {bubble.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>
    </motion.div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function CoachPage() {
  const [bubbles, setBubbles] = useState<ChatBubble[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { mutate } = useSWRConfig();

  // ── Load history on mount ────────────────────────────────────────────────────

  useEffect(() => {
    getCoachHistory(40)
      .then((session) => {
        if (session.messages.length > 0) {
          setBubbles(
            session.messages.map((m) => ({
              id: uid(),
              role: m.role,
              content: m.content,
              timestamp: new Date(m.created_at),
            }))
          );
        }
      })
      .catch(() => {})
      .finally(() => setHistoryLoaded(true));
  }, []);

  // ── Auto-scroll to bottom ────────────────────────────────────────────────────

  const scrollToBottom = useCallback((smooth = true) => {
    bottomRef.current?.scrollIntoView({ behavior: smooth ? "smooth" : "instant" });
  }, []);

  useEffect(() => {
    if (historyLoaded) scrollToBottom(false);
  }, [historyLoaded, scrollToBottom]);

  useEffect(() => {
    if (streaming) scrollToBottom(true);
  }, [bubbles, streaming, scrollToBottom]);

  // Detect if user scrolled up (show scroll-to-bottom button)
  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setShowScrollBtn(distFromBottom > 120);
  };

  // ── Auto-resize textarea ─────────────────────────────────────────────────────

  const resizeTextarea = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  };

  // ── Send message ─────────────────────────────────────────────────────────────

  const handleSend = useCallback(async (text?: string) => {
    const message = (text ?? input).trim();
    if (!message || streaming) return;

    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    // Add user bubble
    const userBubble: ChatBubble = {
      id: uid(),
      role: "user",
      content: message,
      timestamp: new Date(),
    };
    setBubbles((prev) => [...prev, userBubble]);

    // Add empty assistant bubble (streaming placeholder)
    const assistantId = uid();
    const assistantBubble: ChatBubble = {
      id: assistantId,
      role: "assistant",
      content: "",
      streaming: true,
      timestamp: new Date(),
      actionEvents: [],
    };
    setBubbles((prev) => [...prev, assistantBubble]);
    setStreaming(true);

    await sendCoachMessage(message, {
      onDelta: (chunk) => {
        setBubbles((prev) =>
          prev.map((b) =>
            b.id === assistantId
              ? { ...b, content: b.content + chunk }
              : b
          )
        );
      },
      onEvent: (event) => {
        setBubbles((prev) =>
          prev.map((b) =>
            b.id === assistantId
              ? { ...b, actionEvents: [...(b.actionEvents ?? []), event] }
              : b
          )
        );
        // Invalidate SWR caches so Log / Home pages refresh
        if (event.type === "food_logged") {
          mutate((key) => typeof key === "string" && key.includes("food-logs"));
          mutate((key) => typeof key === "string" && key.includes("daily"));
        }
        if (event.type === "workout_logged") {
          mutate((key) => typeof key === "string" && key.includes("workout-logs"));
        }
        if (event.type === "steps_logged") {
          mutate((key) => typeof key === "string" && key.includes("activity"));
        }
      },
      onDone: () => {
        setBubbles((prev) =>
          prev.map((b) =>
            b.id === assistantId ? { ...b, streaming: false } : b
          )
        );
        setStreaming(false);
      },
      onError: (msg) => {
        setBubbles((prev) =>
          prev.map((b) =>
            b.id === assistantId
              ? { ...b, content: msg, streaming: false }
              : b
          )
        );
        setStreaming(false);
      },
    });
  }, [input, streaming, mutate]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // ── Clear history ────────────────────────────────────────────────────────────

  const handleClear = async () => {
    if (streaming) return;
    await clearCoachHistory().catch(() => {});
    setBubbles([]);
  };

  // ── Render ───────────────────────────────────────────────────────────────────

  const isEmpty = historyLoaded && bubbles.length === 0;

  return (
    <div className="flex flex-col h-dvh bg-background">
      {/* ── Header ── */}
      <div className="relative flex items-center justify-between px-4 pt-safe-top
                      pb-3 pt-4 border-b border-border-subtle glass z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-indigo-gradient flex items-center
                          justify-center shadow-glow-indigo">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <div>
            <p className="font-semibold text-text-primary text-sm">Vajra</p>
            <p className="text-[11px] text-emerald-400">Your fitness coach</p>
          </div>
        </div>

        {bubbles.length > 0 && (
          <button
            onClick={handleClear}
            disabled={streaming}
            className="p-2 rounded-xl hover:bg-surface-elevated transition-colors
                       text-text-muted hover:text-red-400 disabled:opacity-40"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* ── Messages ── */}
      <div
        ref={scrollRef}
        onScroll={onScroll}
        className="flex-1 overflow-y-auto px-4 py-4 space-y-4 scroll-smooth"
      >
        {/* Empty state / welcome */}
        <AnimatePresence>
          {isEmpty && (
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center h-full
                         text-center pt-16 pb-8 gap-4"
            >
              <div className="w-20 h-20 rounded-3xl bg-indigo-gradient flex items-center
                              justify-center shadow-glow-indigo mb-2">
                <Bot className="w-10 h-10 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-text-primary">Hey! I'm Vajra 👋</h2>
                <p className="text-sm text-text-muted mt-1 max-w-xs mx-auto">
                  Your personal fitness coach. Tell me what you ate, log a workout, or
                  just ask how you're doing today.
                </p>
              </div>

              {/* Starter prompts */}
              <div className="grid grid-cols-1 gap-2 w-full max-w-sm mt-2">
                {STARTERS.map((s) => (
                  <button
                    key={s}
                    onClick={() => handleSend(s)}
                    className="text-left px-4 py-3 rounded-2xl bg-surface-elevated
                               border border-border text-sm text-text-secondary
                               hover:border-emerald-500/40 hover:text-text-primary
                               transition-all duration-200 active:scale-[0.98]"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Bubbles */}
        {bubbles.map((bubble) => (
          <MessageBubble key={bubble.id} bubble={bubble} />
        ))}

        {/* Scroll anchor */}
        <div ref={bottomRef} />
      </div>

      {/* Scroll to bottom button */}
      <AnimatePresence>
        {showScrollBtn && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            onClick={() => scrollToBottom()}
            className="absolute bottom-28 right-4 z-20 w-9 h-9 rounded-full
                       bg-surface-elevated border border-border shadow-float
                       flex items-center justify-center text-text-muted
                       hover:text-text-primary transition-colors"
          >
            <ChevronDown className="w-4 h-4" />
          </motion.button>
        )}
      </AnimatePresence>

      {/* ── Input bar ── */}
      <div className="px-4 pt-2 pb-safe-bottom pb-4 border-t border-border-subtle glass">
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              resizeTextarea();
            }}
            onKeyDown={handleKeyDown}
            placeholder="Message Vajra…"
            disabled={streaming}
            className={cn(
              "flex-1 resize-none rounded-2xl px-4 py-3 text-sm",
              "bg-surface-elevated border border-border",
              "text-text-primary placeholder:text-text-muted",
              "focus:outline-none focus:border-emerald-500/50",
              "transition-colors duration-200 leading-relaxed",
              "disabled:opacity-60 max-h-[140px] overflow-y-auto"
            )}
          />

          <motion.button
            whileTap={{ scale: 0.9 }}
            onClick={() => handleSend()}
            disabled={!input.trim() || streaming}
            className={cn(
              "w-11 h-11 rounded-2xl flex items-center justify-center shrink-0",
              "transition-all duration-200",
              input.trim() && !streaming
                ? "bg-emerald-500 text-white shadow-glow-emerald"
                : "bg-surface-elevated text-text-muted border border-border"
            )}
          >
            <Send className="w-4 h-4" />
          </motion.button>
        </div>

        <p className="text-[10px] text-text-muted text-center mt-2">
          Vajra can make mistakes — always double-check logged entries
        </p>
      </div>
    </div>
  );
}

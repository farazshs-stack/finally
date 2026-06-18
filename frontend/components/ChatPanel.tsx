"use client";

// ────────────────────────────────────────────────────────────────────────────
// AI Chat Panel — collapsible sidebar, scrolling history, loading indicator
// ────────────────────────────────────────────────────────────────────────────
import React, { useRef, useEffect, useState } from "react";
import type { ChatMessage, ExecutedTrade, WatchlistChange } from "@/lib/types";

interface ChatPanelProps {
  messages: ChatMessage[];
  sending: boolean;
  onSend: (text: string) => void;
  collapsed: boolean;
  onToggle: () => void;
}

function TradeConfirmation({ trades }: { trades: ExecutedTrade[] }) {
  return (
    <div style={{ marginTop: "6px" }}>
      {trades.map((t, i) => (
        <div
          key={i}
          style={{
            fontSize: "11px",
            color: t.error ? "#f85149" : "#3fb950",
            background: t.error ? "rgba(248,81,73,0.1)" : "rgba(63,185,80,0.1)",
            borderRadius: "4px",
            padding: "3px 7px",
            marginBottom: "3px",
          }}
        >
          {t.error ? "✗" : "✓"}{" "}
          {t.side?.toUpperCase()} {t.quantity} {t.ticker}
          {t.price != null ? ` @ $${t.price.toFixed(2)}` : ""}
          {t.error ? ` — ${t.error}` : ""}
        </div>
      ))}
    </div>
  );
}

function WatchlistConfirmation({ changes }: { changes: WatchlistChange[] }) {
  return (
    <div style={{ marginTop: "6px" }}>
      {changes.map((c, i) => (
        <div
          key={i}
          style={{
            fontSize: "11px",
            color: c.success === false ? "#f85149" : "#8b949e",
            background: "rgba(139,148,158,0.1)",
            borderRadius: "4px",
            padding: "3px 7px",
            marginBottom: "3px",
          }}
        >
          {c.action === "add" ? "+" : "−"} Watchlist: {c.ticker}
        </div>
      ))}
    </div>
  );
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <div
      style={{
        marginBottom: "12px",
        display: "flex",
        flexDirection: "column",
        alignItems: isUser ? "flex-end" : "flex-start",
      }}
    >
      <div
        style={{
          maxWidth: "90%",
          background: isUser ? "#1f3a4d" : "#1c2128",
          border: `1px solid ${isUser ? "#209dd7" : "#30363d"}`,
          borderRadius: isUser ? "12px 12px 2px 12px" : "12px 12px 12px 2px",
          padding: "8px 12px",
          fontSize: "12px",
          lineHeight: "1.5",
          color: "#e6edf3",
          whiteSpace: "pre-wrap",
          wordBreak: "break-word",
        }}
      >
        {msg.content}
      </div>

      {/* Actions */}
      {msg.actions?.trades?.length ? (
        <TradeConfirmation trades={msg.actions.trades} />
      ) : null}
      {msg.actions?.watchlist_changes?.length ? (
        <WatchlistConfirmation changes={msg.actions.watchlist_changes} />
      ) : null}

      <span style={{ color: "#6e7681", fontSize: "10px", marginTop: "3px" }}>
        {isUser ? "You" : "FinAlly AI"} ·{" "}
        {new Date(msg.created_at).toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}
      </span>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: "6px", padding: "6px 0" }}>
      {[0, 1, 2].map((i) => (
        <div
          key={i}
          style={{
            width: "6px",
            height: "6px",
            borderRadius: "50%",
            background: "#209dd7",
            animation: `bounce 1.2s ease-in-out ${i * 0.2}s infinite`,
          }}
        />
      ))}
      <style>{`
        @keyframes bounce {
          0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
          30% { transform: translateY(-5px); opacity: 1; }
        }
      `}</style>
    </div>
  );
}

export function ChatPanel({ messages, sending, onSend, collapsed, onToggle }: ChatPanelProps) {
  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, sending]);

  function handleSend() {
    const text = input.trim();
    if (!text || sending) return;
    onSend(text);
    setInput("");
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  const panelWidth = collapsed ? "48px" : "320px";

  return (
    <div
      style={{
        width: panelWidth,
        minWidth: panelWidth,
        maxWidth: panelWidth,
        height: "100%",
        background: "#161b22",
        border: "1px solid #30363d",
        borderRadius: "6px",
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        transition: "width 0.2s ease, min-width 0.2s ease, max-width 0.2s ease",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "8px 10px",
          borderBottom: "1px solid #30363d",
          display: "flex",
          alignItems: "center",
          gap: "8px",
          flexShrink: 0,
          cursor: "pointer",
        }}
        onClick={onToggle}
        title={collapsed ? "Open AI chat" : "Collapse AI chat"}
      >
        <span style={{ fontSize: "16px" }}>🤖</span>
        {!collapsed && (
          <span
            style={{
              color: "#8b949e",
              fontSize: "11px",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              flex: 1,
            }}
          >
            AI Assistant
          </span>
        )}
        <span style={{ color: "#6e7681", fontSize: "14px", marginLeft: "auto" }}>
          {collapsed ? "›" : "‹"}
        </span>
      </div>

      {!collapsed && (
        <>
          {/* Welcome message if no messages */}
          {messages.length === 0 && (
            <div
              style={{
                padding: "16px 12px",
                color: "#6e7681",
                fontSize: "12px",
                lineHeight: "1.6",
              }}
            >
              <div style={{ color: "#209dd7", fontWeight: 600, marginBottom: "8px" }}>
                FinAlly AI ready
              </div>
              <div>Ask me to:</div>
              <ul style={{ margin: "6px 0", paddingLeft: "14px" }}>
                <li>Analyze your portfolio</li>
                <li>Buy or sell shares</li>
                <li>Add tickers to watchlist</li>
                <li>Suggest trades</li>
              </ul>
            </div>
          )}

          {/* Message history */}
          <div
            ref={scrollRef}
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "12px",
            }}
          >
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}
            {sending && <TypingIndicator />}
          </div>

          {/* Input area */}
          <div
            style={{
              padding: "10px",
              borderTop: "1px solid #30363d",
              display: "flex",
              gap: "6px",
              flexShrink: 0,
            }}
          >
            <textarea
              data-testid="chat-input"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask FinAlly AI…"
              rows={2}
              disabled={sending}
              style={{
                flex: 1,
                background: "#0d1117",
                border: "1px solid #30363d",
                borderRadius: "6px",
                color: "#e6edf3",
                fontSize: "12px",
                padding: "7px 10px",
                resize: "none",
                outline: "none",
                fontFamily: "inherit",
                lineHeight: "1.4",
              }}
            />
            <button
              data-testid="chat-send-button"
              onClick={handleSend}
              disabled={sending || !input.trim()}
              style={{
                background: "#753991",
                border: "none",
                borderRadius: "6px",
                color: "#fff",
                fontSize: "18px",
                width: "36px",
                cursor: sending || !input.trim() ? "not-allowed" : "pointer",
                opacity: sending || !input.trim() ? 0.5 : 1,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                alignSelf: "flex-end",
                padding: "7px 0",
              }}
              title="Send (Enter)"
            >
              ↑
            </button>
          </div>
        </>
      )}
    </div>
  );
}

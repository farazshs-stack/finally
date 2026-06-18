"use client";

// ────────────────────────────────────────────────────────────────────────────
// Chat hook — manages conversation with the AI assistant
// ────────────────────────────────────────────────────────────────────────────
import { useState, useCallback } from "react";
import { sendChatMessage } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

export interface UseChatResult {
  messages: ChatMessage[];
  sending: boolean;
  error: string | null;
  send: (text: string) => Promise<void>;
  clear: () => void;
}

let msgId = 0;
function nextId(): string {
  return `local-${++msgId}-${Date.now()}`;
}

export function useChat(
  onTradeExecuted?: () => void,
  onWatchlistChanged?: () => void
): UseChatResult {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = useCallback(
    async (text: string) => {
      if (!text.trim() || sending) return;

      const userMsg: ChatMessage = {
        id: nextId(),
        role: "user",
        content: text.trim(),
        actions: null,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, userMsg]);
      setSending(true);
      setError(null);

      try {
        const response = await sendChatMessage({ message: text.trim() });

        const assistantMsg: ChatMessage = {
          id: response.id || nextId(),
          role: "assistant",
          content: response.content,
          actions: response.actions ?? null,
          created_at: response.created_at || new Date().toISOString(),
        };

        setMessages((prev) => [...prev, assistantMsg]);

        // Trigger refreshes if the assistant made changes
        if (response.actions?.trades?.length) {
          onTradeExecuted?.();
        }
        if (response.actions?.watchlist_changes?.length) {
          onWatchlistChanged?.();
        }
      } catch (e) {
        const msg = e instanceof Error ? e.message : "Failed to send message";
        setError(msg);
        // Add error message to chat
        setMessages((prev) => [
          ...prev,
          {
            id: nextId(),
            role: "assistant",
            content: `Sorry, I encountered an error: ${msg}`,
            actions: null,
            created_at: new Date().toISOString(),
          },
        ]);
      } finally {
        setSending(false);
      }
    },
    [sending, onTradeExecuted, onWatchlistChanged]
  );

  const clear = useCallback(() => {
    setMessages([]);
    setError(null);
  }, []);

  return { messages, sending, error, send, clear };
}

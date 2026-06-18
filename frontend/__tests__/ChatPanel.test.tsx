import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ChatPanel } from "@/components/ChatPanel";
import type { ChatMessage } from "@/lib/types";

const mockMessages: ChatMessage[] = [
  {
    id: "1",
    role: "user",
    content: "What is my portfolio worth?",
    actions: null,
    created_at: new Date().toISOString(),
  },
  {
    id: "2",
    role: "assistant",
    content: "Your portfolio is worth $10,500 with 2 positions.",
    actions: null,
    created_at: new Date().toISOString(),
  },
];

describe("ChatPanel", () => {
  const onSend = vi.fn();
  const onToggle = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders chat input and send button when expanded", () => {
    render(
      <ChatPanel
        messages={[]}
        sending={false}
        onSend={onSend}
        collapsed={false}
        onToggle={onToggle}
      />
    );
    expect(screen.getByTestId("chat-input")).toBeTruthy();
    expect(screen.getByTestId("chat-send-button")).toBeTruthy();
  });

  it("does not render input when collapsed", () => {
    render(
      <ChatPanel
        messages={[]}
        sending={false}
        onSend={onSend}
        collapsed={true}
        onToggle={onToggle}
      />
    );
    expect(screen.queryByTestId("chat-input")).toBeNull();
  });

  it("renders message history", () => {
    render(
      <ChatPanel
        messages={mockMessages}
        sending={false}
        onSend={onSend}
        collapsed={false}
        onToggle={onToggle}
      />
    );
    expect(screen.getByText("What is my portfolio worth?")).toBeTruthy();
    expect(screen.getByText("Your portfolio is worth $10,500 with 2 positions.")).toBeTruthy();
  });

  it("calls onSend when send button is clicked", () => {
    render(
      <ChatPanel
        messages={[]}
        sending={false}
        onSend={onSend}
        collapsed={false}
        onToggle={onToggle}
      />
    );
    const input = screen.getByTestId("chat-input");
    fireEvent.change(input, { target: { value: "Buy 10 AAPL" } });
    fireEvent.click(screen.getByTestId("chat-send-button"));
    expect(onSend).toHaveBeenCalledWith("Buy 10 AAPL");
  });

  it("calls onSend on Enter key press", () => {
    render(
      <ChatPanel
        messages={[]}
        sending={false}
        onSend={onSend}
        collapsed={false}
        onToggle={onToggle}
      />
    );
    const input = screen.getByTestId("chat-input");
    fireEvent.change(input, { target: { value: "Analyze my portfolio" } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onSend).toHaveBeenCalledWith("Analyze my portfolio");
  });

  it("does not call onSend when input is empty", () => {
    render(
      <ChatPanel
        messages={[]}
        sending={false}
        onSend={onSend}
        collapsed={false}
        onToggle={onToggle}
      />
    );
    fireEvent.click(screen.getByTestId("chat-send-button"));
    expect(onSend).not.toHaveBeenCalled();
  });

  it("disables input and send button when sending", () => {
    render(
      <ChatPanel
        messages={[]}
        sending={true}
        onSend={onSend}
        collapsed={false}
        onToggle={onToggle}
      />
    );
    const input = screen.getByTestId("chat-input") as HTMLTextAreaElement;
    const btn = screen.getByTestId("chat-send-button") as HTMLButtonElement;
    expect(input.disabled).toBe(true);
    expect(btn.disabled).toBe(true);
  });

  it("shows trade confirmations from assistant actions", () => {
    const msgWithTrades: ChatMessage[] = [
      {
        id: "3",
        role: "assistant",
        content: "I bought 5 shares of AAPL for you.",
        actions: {
          trades: [{ ticker: "AAPL", side: "buy", quantity: 5, price: 190, success: true }],
        },
        created_at: new Date().toISOString(),
      },
    ];
    render(
      <ChatPanel
        messages={msgWithTrades}
        sending={false}
        onSend={onSend}
        collapsed={false}
        onToggle={onToggle}
      />
    );
    expect(screen.getByText(/BUY 5 AAPL/)).toBeTruthy();
  });

  it("calls onToggle when header is clicked", () => {
    render(
      <ChatPanel
        messages={[]}
        sending={false}
        onSend={onSend}
        collapsed={false}
        onToggle={onToggle}
      />
    );
    // Click the header div (the div that has the onClick={onToggle} handler)
    const header = screen.getByText("AI Assistant").closest("div")!;
    fireEvent.click(header);
    expect(onToggle).toHaveBeenCalled();
  });
});

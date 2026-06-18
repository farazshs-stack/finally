"use client";

// ────────────────────────────────────────────────────────────────────────────
// FinAlly Trading Workstation — Main Page
// Single-page app with all panels laid out in a trading terminal aesthetic
// ────────────────────────────────────────────────────────────────────────────
import React, { useState, useCallback } from "react";

import { Header } from "@/components/Header";
import { WatchlistPanel } from "@/components/WatchlistPanel";
import { MainChart } from "@/components/MainChart";
import { PortfolioHeatmap } from "@/components/PortfolioHeatmap";
import { PnlChart } from "@/components/PnlChart";
import { PositionsTable } from "@/components/PositionsTable";
import { TradeBar } from "@/components/TradeBar";
import { ChatPanel } from "@/components/ChatPanel";

import { usePriceStream } from "@/hooks/usePriceStream";
import { usePortfolio, computeLiveTotal } from "@/hooks/usePortfolio";
import { useWatchlist } from "@/hooks/useWatchlist";
import { useChat } from "@/hooks/useChat";

export default function TradingWorkstation() {
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [chatCollapsed, setChatCollapsed] = useState(false);
  const [pnlRefreshTrigger, setPnlRefreshTrigger] = useState(0);

  // Data hooks
  const { prices, sparklines, status, flashMap } = usePriceStream();
  const { portfolio, refresh: refreshPortfolio, trade } = usePortfolio();
  const { watchlist, add: addTicker, remove: removeTicker, refresh: refreshWatchlist } = useWatchlist();

  const onTradeExecuted = useCallback(() => {
    refreshPortfolio();
    setPnlRefreshTrigger((t) => t + 1);
  }, [refreshPortfolio]);

  const onWatchlistChanged = useCallback(() => {
    refreshWatchlist();
  }, [refreshWatchlist]);

  const { messages, sending, send: sendChat } = useChat(onTradeExecuted, onWatchlistChanged);

  // Live total = cash + live positions value
  const liveTotal = portfolio
    ? computeLiveTotal(portfolio.positions, prices, portfolio.cash_balance)
    : 0;

  const cashBalance = portfolio?.cash_balance ?? 0;
  const positions = portfolio?.positions ?? [];

  // Selected ticker sparkline data for main chart
  const selectedSparkline = selectedTicker ? (sparklines[selectedTicker] ?? []) : [];
  const selectedPrice = selectedTicker ? prices[selectedTicker]?.price : undefined;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        height: "100vh",
        background: "#0d1117",
        overflow: "hidden",
      }}
    >
      {/* Header */}
      <Header totalValue={liveTotal} cashBalance={cashBalance} status={status} />

      {/* Main layout */}
      <div
        style={{
          flex: 1,
          display: "flex",
          gap: "6px",
          padding: "6px",
          overflow: "hidden",
          minHeight: 0,
        }}
      >
        {/* Left column: Watchlist */}
        <div
          style={{
            width: "300px",
            minWidth: "260px",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <WatchlistPanel
            watchlist={watchlist}
            prices={prices}
            sparklines={sparklines}
            flashMap={flashMap}
            selectedTicker={selectedTicker}
            onSelectTicker={setSelectedTicker}
            onAddTicker={addTicker}
            onRemoveTicker={removeTicker}
          />
        </div>

        {/* Center column: charts + positions + trade bar */}
        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            gap: "6px",
            minWidth: 0,
            overflow: "hidden",
          }}
        >
          {/* Top: Main chart + Portfolio heatmap */}
          <div
            style={{
              flex: "0 0 260px",
              display: "flex",
              gap: "6px",
            }}
          >
            {/* Main price chart */}
            <div style={{ flex: 2, minWidth: 0 }}>
              <MainChart
                ticker={selectedTicker}
                data={selectedSparkline}
                currentPrice={selectedPrice}
              />
            </div>

            {/* Portfolio heatmap */}
            <div style={{ flex: 1, minWidth: 160 }}>
              <PortfolioHeatmap positions={positions} prices={prices} />
            </div>
          </div>

          {/* Middle: P&L chart */}
          <div style={{ flex: "0 0 160px" }}>
            <PnlChart refreshTrigger={pnlRefreshTrigger} />
          </div>

          {/* Bottom: Positions table + Trade bar */}
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              gap: "6px",
              minHeight: 0,
            }}
          >
            {/* Trade bar */}
            <TradeBar
              onTrade={trade}
              defaultTicker={selectedTicker ?? undefined}
              cashBalance={cashBalance}
            />

            {/* Positions table */}
            <div style={{ flex: 1, minHeight: 0 }}>
              <PositionsTable positions={positions} prices={prices} />
            </div>
          </div>
        </div>

        {/* Right column: AI Chat */}
        <ChatPanel
          messages={messages}
          sending={sending}
          onSend={sendChat}
          collapsed={chatCollapsed}
          onToggle={() => setChatCollapsed((c) => !c)}
        />
      </div>
    </div>
  );
}

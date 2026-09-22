import os

html_content = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>NIFTY 50 Options Arbitrage & Trading Engine</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --gf-bg: #171717;
      --gf-surface: #202124;
      --gf-card: #202124;
      --gf-card-inner: #292a2d;
      --gf-border: #3c4043;
      --gf-border-subtle: rgba(255, 255, 255, 0.08);
      --gf-text-primary: #e8eaed;
      --gf-text-secondary: #9aa0a6;
      --gf-blue: #8ab4f8;
      --gf-blue-hover: #aecbfa;
      --gf-red: #f28b82;
      --gf-red-pill: rgba(242, 139, 130, 0.18);
      --gf-green: #81c995;
      --gf-green-pill: rgba(129, 201, 149, 0.18);
      --gf-pill-bg: #303134;
      --gf-pill-hover: #3c4043;
      --font-gf: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-tap-highlight-color: transparent;
      font-family: var(--font-gf);
    }

    body {
      background: var(--gf-bg);
      color: var(--gf-text-primary);
      min-height: 100vh;
      font-size: 14px;
      line-height: 1.4;
      padding-bottom: 70px;
      position: relative;
      overflow-x: hidden;
      -webkit-font-smoothing: antialiased;
    }

    /* Top Platform Header */
    .platform-header {
      background: #202124;
      padding: 12px 18px;
      position: sticky;
      top: 0;
      z-index: 100;
      border-bottom: 1px solid var(--gf-border);
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 14px;
      flex-wrap: wrap;
    }

    .header-brand-wrap {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .brand-logo-icon {
      width: 36px;
      height: 36px;
      border-radius: 10px;
      background: #292a2d;
      border: 1px solid var(--gf-border);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .brand-title {
      font-size: 15px;
      font-weight: 800;
      color: #fff;
      letter-spacing: -0.2px;
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .brand-sub-badge {
      font-size: 10px;
      font-weight: 700;
      background: rgba(138, 180, 248, 0.15);
      color: var(--gf-blue);
      border: 1px solid rgba(138, 180, 248, 0.3);
      padding: 2px 7px;
      border-radius: 6px;
      letter-spacing: 0.5px;
      font-family: 'JetBrains Mono', monospace;
    }

    .brand-meta {
      font-size: 11px;
      color: var(--gf-text-secondary);
      margin-top: 1px;
    }

    .header-telemetry-wrap {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
    }

    .telemetry-chip {
      padding: 5px 10px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 600;
      display: flex;
      align-items: center;
      gap: 6px;
      background: #303134;
      border: 1px solid var(--gf-border);
      color: var(--gf-text-primary);
      font-family: 'JetBrains Mono', monospace;
      white-space: nowrap;
    }

    .mode-chip {
      background: rgba(251, 188, 5, 0.12);
      border-color: rgba(251, 188, 5, 0.3);
      color: #fbbc05;
    }

    .live-chip {
      background: rgba(129, 201, 149, 0.15);
      border-color: rgba(129, 201, 149, 0.3);
      color: var(--gf-green);
    }

    .top-kill-btn {
      background: var(--gf-red-pill);
      border: 1px solid var(--gf-red);
      color: var(--gf-red);
      padding: 5px 12px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
      transition: all 0.2s;
      white-space: nowrap;
    }

    .top-kill-btn:hover {
      background: var(--gf-red);
      color: #202124;
    }

    .pulse-dot {
      width: 6px;
      height: 6px;
      border-radius: 50%;
      background: var(--gf-green);
      box-shadow: 0 0 6px var(--gf-green);
      animation: pulseGlow 2s infinite ease-in-out;
    }

    @keyframes pulseGlow {
      0%, 100% { opacity: 0.4; transform: scale(0.9); }
      50% { opacity: 1; transform: scale(1.15); }
    }

    /* Active Platform Navigation Bar */
    .platform-nav-bar {
      background: #202124;
      position: sticky;
      top: 61px;
      z-index: 99;
      border-bottom: 1px solid var(--gf-border);
      display: flex;
      gap: 4px;
      overflow-x: auto;
      padding: 0 14px;
      scrollbar-width: none;
    }
    .platform-nav-bar::-webkit-scrollbar { display: none; }

    .nav-tab-item {
      color: var(--gf-text-secondary);
      font-size: 13px;
      font-weight: 600;
      padding: 12px 14px;
      white-space: nowrap;
      cursor: pointer;
      border-bottom: 3px solid transparent;
      transition: all 0.2s;
      text-decoration: none;
      display: inline-flex;
      align-items: center;
      gap: 6px;
    }

    .nav-tab-item:hover {
      color: #fff;
      background: rgba(255, 255, 255, 0.03);
    }

    .nav-tab-item.active {
      color: #8ab4f8;
      border-bottom-color: #8ab4f8;
      font-weight: 700;
      background: rgba(138, 180, 248, 0.06);
    }

    /* Main Content Container */
    .gf-main-container {
      max-width: 920px;
      margin: 0 auto;
      padding: 16px 14px;
    }

    /* Tab Section Panels */
    .tab-section {
      display: none;
    }
    .tab-section.active {
      display: block;
      animation: fadeIn 0.2s ease-out;
    }
    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* Stand-down Alert Banner */
    #market-status-banner {
      background: rgba(242, 139, 130, 0.12);
      border: 1px solid rgba(242, 139, 130, 0.35);
      border-radius: 16px;
      padding: 12px 16px;
      margin-bottom: 16px;
      display: none;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
    }

    /* Kill Switch Notification Banner */
    #kill-alert {
      display: none;
      background: var(--gf-red-pill);
      border: 1px solid var(--gf-red);
      color: #fff;
      border-radius: 14px;
      padding: 12px 16px;
      margin-bottom: 16px;
    }

    /* ======================================================== */
    /* GOOGLE FINANCE HERO CARD (Matches Screenshot)             */
    /* ======================================================== */
    .gf-hero-card {
      background: var(--gf-card);
      border-radius: 20px;
      padding: 18px 20px;
      margin-bottom: 16px;
      border: 1px solid var(--gf-border);
    }

    .gf-title-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 6px;
    }

    .gf-asset-title {
      font-size: 20px;
      font-weight: 700;
      color: #fff;
      letter-spacing: -0.2px;
    }

    .gf-asset-meta {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: var(--gf-text-secondary);
      margin-top: 2px;
    }

    .meta-dot { font-size: 8px; }

    .gf-follow-btn {
      background: #8ab4f8;
      color: #202124;
      border: none;
      border-radius: 20px;
      padding: 7px 18px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 5px;
      transition: background 0.2s;
    }
    .gf-follow-btn:hover { background: var(--gf-blue-hover); }

    /* Price Display */
    .gf-price-container {
      margin-top: 10px;
    }

    .gf-spot-big {
      font-size: 38px;
      font-weight: 700;
      color: #fff;
      letter-spacing: -0.5px;
      line-height: 1.1;
      font-family: var(--font-gf);
    }

    .gf-pill-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-top: 6px;
    }

    .gf-change-pill {
      display: inline-flex;
      align-items: center;
      gap: 4px;
      padding: 3px 8px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 700;
      font-family: 'JetBrains Mono', monospace;
    }

    .gf-change-pill.down {
      background: var(--gf-red-pill);
      color: var(--gf-red);
    }

    .gf-change-pill.up {
      background: var(--gf-green-pill);
      color: var(--gf-green);
    }

    .gf-change-pts {
      font-size: 13px;
      font-weight: 500;
      font-family: 'JetBrains Mono', monospace;
    }
    .gf-change-pts.down { color: var(--gf-red); }
    .gf-change-pts.up { color: var(--gf-green); }

    .gf-market-timestamp {
      font-size: 12px;
      color: var(--gf-text-secondary);
      margin-top: 2px;
    }

    /* Timeframe Selector Pills */
    .gf-timeframe-row {
      display: flex;
      gap: 6px;
      overflow-x: auto;
      padding: 10px 0 14px 0;
      scrollbar-width: none;
    }
    .gf-timeframe-row::-webkit-scrollbar { display: none; }

    .gf-tf-pill {
      padding: 6px 14px;
      border-radius: 18px;
      background: transparent;
      border: 1px solid transparent;
      color: var(--gf-text-secondary);
      font-size: 13px;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }

    .gf-tf-pill:hover {
      background: var(--gf-pill-hover);
      color: #fff;
    }

    .gf-tf-pill.active {
      background: #8ab4f8;
      color: #202124;
      font-weight: 700;
    }

    /* Chart Canvas Container */
    .gf-chart-wrap {
      position: relative;
      width: 100%;
      height: 250px;
      margin-bottom: 16px;
    }

    #nifty-chart-canvas {
      width: 100%;
      height: 100%;
      display: block;
    }

    .chart-hover-pill {
      position: absolute;
      top: 6px;
      background: #303134;
      border: 1px solid var(--gf-border);
      color: #fff;
      padding: 4px 10px;
      border-radius: 12px;
      font-size: 11px;
      font-family: 'JetBrains Mono', monospace;
      pointer-events: none;
      display: none;
      box-shadow: 0 4px 12px rgba(0,0,0,0.4);
      z-index: 10;
    }

    /* Key Statistics 6-Item Grid */
    .gf-stats-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 12px 18px;
      padding-top: 14px;
      border-top: 1px solid var(--gf-border);
      margin-bottom: 16px;
    }

    @media (max-width: 580px) {
      .gf-stats-grid {
        grid-template-columns: repeat(2, 1fr);
      }
    }

    .gf-stat-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 4px 0;
      border-bottom: 1px solid rgba(255,255,255,0.05);
      font-size: 12px;
    }

    .gf-stat-label {
      color: var(--gf-text-secondary);
    }

    .gf-stat-value {
      color: #fff;
      font-weight: 600;
      font-family: 'JetBrains Mono', monospace;
    }

    /* Related Markets Card */
    .gf-related-card {
      background: var(--gf-card);
      border: 1px solid var(--gf-border);
      border-radius: 20px;
      padding: 16px 18px;
      margin-bottom: 16px;
    }

    .gf-section-title {
      font-size: 16px;
      font-weight: 700;
      color: #fff;
      margin-bottom: 12px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .related-market-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 9px 0;
      border-bottom: 1px solid rgba(255,255,255,0.05);
      font-size: 13px;
    }
    .related-market-row:last-child { border-bottom: none; }

    .related-name {
      color: #fff;
      font-weight: 500;
    }

    .related-right {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .related-price {
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      color: #fff;
      font-weight: 600;
    }

    .related-pill {
      display: inline-flex;
      align-items: center;
      gap: 2px;
      padding: 3px 8px;
      border-radius: 12px;
      font-size: 11px;
      font-weight: 700;
      font-family: 'JetBrains Mono', monospace;
      min-width: 65px;
      justify-content: center;
    }

    .related-pill.down {
      background: var(--gf-red-pill);
      color: var(--gf-red);
    }
    .related-pill.up {
      background: var(--gf-green-pill);
      color: var(--gf-green);
    }

    /* "Analyse NIFTY 50 >" Full Width Button */
    .gf-analyse-banner {
      width: 100%;
      background: #303134;
      border: 1px solid var(--gf-border);
      color: #fff;
      border-radius: 24px;
      padding: 12px 20px;
      font-size: 14px;
      font-weight: 600;
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: pointer;
      margin-bottom: 20px;
      transition: all 0.2s;
    }
    .gf-analyse-banner:hover {
      background: #3c4043;
      border-color: #5f6368;
    }

    /* News Grid & Cards */
    .gf-news-section {
      margin-bottom: 24px;
    }

    .gf-news-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 12px;
    }

    .gf-news-title {
      font-size: 18px;
      font-weight: 700;
      color: #fff;
    }

    .gf-news-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
    }
    @media (max-width: 600px) {
      .gf-news-grid {
        grid-template-columns: 1fr;
      }
    }

    .gf-news-card {
      background: var(--gf-card);
      border: 1px solid var(--gf-border);
      border-radius: 16px;
      padding: 14px;
      display: flex;
      gap: 12px;
      justify-content: space-between;
      transition: all 0.2s;
      text-decoration: none;
      color: inherit;
    }
    .gf-news-card:hover {
      border-color: #5f6368;
      background: #252629;
    }

    .gf-news-content {
      flex: 1;
    }

    .gf-news-source {
      font-size: 11px;
      color: var(--gf-text-secondary);
      margin-bottom: 4px;
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .source-badge-live {
      background: rgba(242, 139, 130, 0.2);
      color: var(--gf-red);
      padding: 1px 5px;
      border-radius: 4px;
      font-size: 9px;
      font-weight: 800;
    }

    .gf-news-heading {
      font-size: 13px;
      font-weight: 600;
      color: #fff;
      line-height: 1.35;
      margin-bottom: 6px;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .gf-news-time {
      font-size: 11px;
      color: var(--gf-text-secondary);
    }

    .gf-news-thumb {
      width: 58px;
      height: 58px;
      border-radius: 12px;
      background: #303134;
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 22px;
    }

    /* Trading & HUD Styles */
    .trading-stat-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
      margin-bottom: 16px;
    }
    @media (max-width: 500px) {
      .trading-stat-grid { grid-template-columns: 1fr; }
    }

    .trading-metric-box {
      background: var(--gf-card);
      border: 1px solid var(--gf-border);
      border-radius: 16px;
      padding: 14px 16px;
    }

    .t-label {
      font-size: 11px;
      font-weight: 600;
      color: var(--gf-text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 4px;
    }

    .t-val {
      font-size: 22px;
      font-weight: 800;
      font-family: 'JetBrains Mono', monospace;
      color: #fff;
    }

    .t-sub {
      font-size: 12px;
      color: var(--gf-text-secondary);
      margin-top: 3px;
    }

    .btn-row {
      display: flex;
      gap: 10px;
      margin-bottom: 16px;
    }

    .btn-primary-act {
      flex: 1;
      background: #8ab4f8;
      color: #202124;
      border: none;
      padding: 12px 18px;
      border-radius: 14px;
      font-weight: 700;
      font-size: 13px;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      transition: background 0.2s;
    }
    .btn-primary-act:hover { background: #aecbfa; }

    .btn-danger-act {
      flex: 1;
      background: var(--gf-red-pill);
      color: var(--gf-red);
      border: 1px solid rgba(242, 139, 130, 0.4);
      padding: 12px 18px;
      border-radius: 14px;
      font-weight: 700;
      font-size: 13px;
      cursor: pointer;
      transition: background 0.2s;
    }
    .btn-danger-act:hover { background: rgba(242, 139, 130, 0.3); }

    /* Orders, Trades & Option Lists */
    .gf-list-card {
      background: var(--gf-card);
      border: 1px solid var(--gf-border);
      border-radius: 18px;
      padding: 16px;
      margin-bottom: 16px;
    }

    .gf-list-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 0;
      border-bottom: 1px solid rgba(255,255,255,0.05);
      font-size: 13px;
    }
    .gf-list-item:last-child { border-bottom: none; }

    .btn-buy-chip {
      background: rgba(129, 201, 149, 0.2);
      border: 1px solid var(--gf-green);
      color: var(--gf-green);
      padding: 4px 10px;
      border-radius: 8px;
      font-size: 11px;
      font-weight: 700;
      cursor: pointer;
    }
    .btn-buy-chip:hover {
      background: var(--gf-green);
      color: #202124;
    }

    /* Macro Card Grid */
    .macro-stat-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin-bottom: 16px;
    }
    @media (max-width: 650px) {
      .macro-stat-grid { grid-template-columns: repeat(2, 1fr); }
    }
  </style>
</head>
<body>

  <!-- Top Platform Header -->
  <header class="platform-header">
    <div class="header-brand-wrap">
      <div class="brand-logo-icon">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <rect x="3" y="10" width="4" height="11" rx="1.5" fill="#8ab4f8"/>
          <line x1="5" y1="3" x2="5" y2="10" stroke="#8ab4f8" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="5" y1="21" x2="5" y2="23" stroke="#8ab4f8" stroke-width="1.8" stroke-linecap="round"/>
          <rect x="10" y="6" width="4" height="15" rx="1.5" fill="#81c995"/>
          <line x1="12" y1="2" x2="12" y2="6" stroke="#81c995" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="12" y1="21" x2="12" y2="23" stroke="#81c995" stroke-width="1.8" stroke-linecap="round"/>
          <rect x="17" y="13" width="4" height="8" rx="1.5" fill="#f28b82"/>
          <line x1="19" y1="7" x2="19" y2="13" stroke="#f28b82" stroke-width="1.8" stroke-linecap="round"/>
          <line x1="19" y1="21" x2="19" y2="23" stroke="#f28b82" stroke-width="1.8" stroke-linecap="round"/>
        </svg>
      </div>
      <div>
        <div class="brand-title">
          <span>NIFTY 50</span>
          <span class="brand-sub-badge">OPTIONS & ARBITRAGE</span>
        </div>
        <div class="brand-meta">NSE Derivatives · Autonomous Execution · ₹3,000 Micro-Cap</div>
      </div>
    </div>

    <div class="header-telemetry-wrap">
      <div class="telemetry-chip mode-chip" id="mode-badge">PAPER TRADING</div>
      <div class="telemetry-chip live-chip" id="live-status-container">
        <div class="pulse-dot" id="live-dot"></div>
        <span id="ws-status-text">LIVE</span>
        <span id="ws-latency" style="opacity: 0.7; font-size: 10px; margin-left: 2px;"></span>
      </div>
      <div class="telemetry-chip cash-chip">
        <span style="opacity:0.7;">Cash:</span>
        <span id="top-cash-val" style="color:var(--gf-green); font-weight:700;">₹3,000.00</span>
      </div>
      <button class="top-kill-btn" onclick="engageKillSwitch()">
        🛑 KILL SWITCH
      </button>
    </div>
  </header>

  <!-- Active Platform Navigation Bar with Real Working Links -->
  <nav class="platform-nav-bar">
    <a href="#overview" class="nav-tab-item active" data-tab="overview" onclick="switchMainTab('overview', event)">
      <span>📈</span> Overview
    </a>
    <a href="#trading" class="nav-tab-item" data-tab="trading" onclick="switchMainTab('trading', event)">
      <span>⚡</span> Trading HUD
    </a>
    <a href="#chain" class="nav-tab-item" data-tab="chain" onclick="switchMainTab('chain', event)">
      <span>🎯</span> Option Chain
    </a>
    <a href="#orders" class="nav-tab-item" data-tab="orders" onclick="switchMainTab('orders', event)">
      <span>📋</span> Orders & PnL
    </a>
    <a href="#greeks" class="nav-tab-item" data-tab="greeks" onclick="switchMainTab('greeks', event)">
      <span>🧠</span> Greeks & ML
    </a>
    <a href="#news" class="nav-tab-item" data-tab="news" onclick="switchMainTab('news', event)">
      <span>📰</span> Market News
    </a>
  </nav>

  <main class="gf-main-container">

    <!-- Stand-Down & Shock Alert Banner -->
    <div id="market-status-banner">
      <div style="display:flex; align-items:center; gap:10px;">
        <span style="font-size:20px;">🔴</span>
        <div>
          <div id="market-status-title" style="font-weight:700; font-size:13px; color:var(--gf-red);">NSE MARKET CLOSED (STAND-DOWN)</div>
          <div id="market-status-sub" style="font-size:11px; color:var(--gf-text-secondary);">Trading hours: 09:15 - 15:30 IST. Platform in defensive capital preservation stand-down.</div>
        </div>
      </div>
      <span id="market-status-tag" style="background:var(--gf-red-pill); color:var(--gf-red); font-size:10px; font-weight:700; padding:2px 8px; border-radius:6px;">STAND-DOWN</span>
    </div>

    <!-- Kill Switch Alert Banner -->
    <div id="kill-alert">
      ⚠️ <strong>EMERGENCY KILL SWITCH ENGAGED!</strong> <span id="kill-reason"></span>
      <button onclick="resetKillSwitch()" style="margin-left:10px; padding:3px 8px; background:var(--gf-red); color:#202124; border:none; border-radius:4px; font-weight:700; cursor:pointer;">Reset</button>
    </div>

    <!-- ======================================================== -->
    <!-- TAB 1: GOOGLE FINANCE OVERVIEW & CHART                   -->
    <!-- ======================================================== -->
    <div id="tab-overview" class="tab-section active">

      <!-- Hero Header Card -->
      <div class="gf-hero-card">
        <div class="gf-title-header">
          <div>
            <h1 class="gf-asset-title">NIFTY 50</h1>
            <div class="gf-asset-meta">
              <span>INDEXNSE: NIFTY_50</span>
              <span class="meta-dot">•</span>
              <span style="cursor:pointer;" title="Options Contract Multiplier">Lot Size: 65</span>
            </div>
          </div>
          <button class="gf-follow-btn" onclick="switchMainTab('chain', event)">
            <span>+</span> Follow Strikes
          </button>
        </div>

        <!-- Big Price Display -->
        <div class="gf-price-container">
          <div class="gf-spot-big" id="spot-price">23,329.00</div>
          <div class="gf-pill-row">
            <span class="gf-change-pill down" id="spot-pill">
              <span id="pill-arrow">↓</span> <span id="pill-pct">0.36%</span>
            </span>
            <span class="gf-change-pts down" id="spot-points-text">-85.30 today</span>
          </div>
          <div class="gf-market-timestamp" id="gf-timestamp">
            22 Sept, 3:30 pm IST • INR • INDEXNSE • Disclaimer
          </div>
        </div>

        <!-- Timeframe Selector Pills -->
        <div class="gf-timeframe-row">
          <button class="gf-tf-pill active" data-tf="1D" onclick="setTimeframe('1D')">1D</button>
          <button class="gf-tf-pill" data-tf="5D" onclick="setTimeframe('5D')">5D</button>
          <button class="gf-tf-pill" data-tf="1M" onclick="setTimeframe('1M')">1M</button>
          <button class="gf-tf-pill" data-tf="6M" onclick="setTimeframe('6M')">6M</button>
          <button class="gf-tf-pill" data-tf="YTD" onclick="setTimeframe('YTD')">YTD</button>
          <button class="gf-tf-pill" data-tf="1Y" onclick="setTimeframe('1Y')">1Y</button>
          <button class="gf-tf-pill" data-tf="5Y" onclick="setTimeframe('5Y')">5Y</button>
          <button class="gf-tf-pill" data-tf="Max" onclick="setTimeframe('Max')">Max</button>
        </div>

        <!-- High-DPI Interactive Canvas Chart -->
        <div class="gf-chart-wrap">
          <div id="chart-hover-tooltip" class="chart-hover-pill"></div>
          <canvas id="nifty-chart-canvas"></canvas>
        </div>

        <!-- Key Statistics 6-Item Grid -->
        <div class="gf-stats-grid">
          <div class="gf-stat-item">
            <span class="gf-stat-label">Open</span>
            <span class="gf-stat-value" id="stat-open">23,454.05</span>
          </div>
          <div class="gf-stat-item">
            <span class="gf-stat-label">High</span>
            <span class="gf-stat-value" id="stat-high">23,489.00</span>
          </div>
          <div class="gf-stat-item">
            <span class="gf-stat-label">Low</span>
            <span class="gf-stat-value" id="stat-low">23,285.75</span>
          </div>
          <div class="gf-stat-item">
            <span class="gf-stat-label">Prev close</span>
            <span class="gf-stat-value" id="stat-prev-close">23,414.30</span>
          </div>
          <div class="gf-stat-item">
            <span class="gf-stat-label">52-wk high</span>
            <span class="gf-stat-value">26,373.20</span>
          </div>
          <div class="gf-stat-item">
            <span class="gf-stat-label">52-wk low</span>
            <span class="gf-stat-value">22,182.55</span>
          </div>
        </div>

      </div>

      <!-- Related Markets Card -->
      <div class="gf-related-card">
        <div class="gf-section-title">
          <span>Global Markets & Correlated Assets</span>
          <span style="font-size:11px; color:var(--gf-text-secondary); font-weight:normal;">Live Benchmark</span>
        </div>

        <div class="related-market-row">
          <span class="related-name">Dow Jones</span>
          <div class="related-right">
            <span class="related-price">51,799.24</span>
            <span class="related-pill down">↓ 0.48%</span>
          </div>
        </div>

        <div class="related-market-row">
          <span class="related-name">S&P 500</span>
          <div class="related-right">
            <span class="related-price">7,766.27</span>
            <span class="related-pill up">↑ 0.02%</span>
          </div>
        </div>

        <div class="related-market-row">
          <span class="related-name">Nasdaq</span>
          <div class="related-right">
            <span class="related-price">27,247.65</span>
            <span class="related-pill up">↑ 0.46%</span>
          </div>
        </div>

        <div class="related-market-row">
          <span class="related-name">Russell 2000</span>
          <div class="related-right">
            <span class="related-price">2,905.79</span>
            <span class="related-pill up">↑ 1.06%</span>
          </div>
        </div>

        <div class="related-market-row">
          <span class="related-name">Brent Crude</span>
          <div class="related-right">
            <span class="related-price" id="macro-brent-val">$74.20</span>
            <span class="related-pill down" id="macro-brent-pill">↓ 1.20%</span>
          </div>
        </div>
      </div>

      <!-- "Analyse NIFTY 50 >" Action Banner linking to Option Chain -->
      <button class="gf-analyse-banner" onclick="switchMainTab('chain', event)">
        <div style="display:flex; align-items:center; gap:10px;">
          <span style="font-size: 16px;">⚡</span>
          <span>Analyse NIFTY 50 Options & Arbitrage Chain</span>
        </div>
        <span style="font-size: 18px;">›</span>
      </button>

      <!-- News Preview Card -->
      <div class="gf-news-section">
        <div class="gf-news-header">
          <h2 class="gf-news-title">Market News Highlights</h2>
          <button class="gf-tf-pill" style="background:#303134; color:#fff;" onclick="switchMainTab('news', event)">View All News ›</button>
        </div>
        <div class="gf-news-grid">
          <a href="#news" onclick="switchMainTab('news', event)" class="gf-news-card" style="grid-column: 1 / -1;">
            <div class="gf-news-content">
              <div class="gf-news-source">
                <span class="source-badge-live">LIVE ●</span>
                <span>The Economic Times</span>
              </div>
              <h3 class="gf-news-heading">Sensex Today | Nifty 50 | Stock Market Highlights: Sensex ends 330 pts lower, Nifty below 23,400; Bajaj, RIL lead slide</h3>
              <div class="gf-news-time">3 hours ago • Market Analysis</div>
            </div>
            <div class="gf-news-thumb" style="background:#2a1b1b; color:#ff7788;">📉</div>
          </a>
        </div>
      </div>

    </div>

    <!-- ======================================================== -->
    <!-- TAB 2: TRADING & RISK HUD                                -->
    <!-- ======================================================== -->
    <div id="tab-trading" class="tab-section">

      <!-- Financial Metrics Grid -->
      <div class="trading-stat-grid">
        <div class="trading-metric-box">
          <div class="t-label">VIRTUAL CASH BALANCE</div>
          <div class="t-val" id="cash-val" style="color:var(--gf-green);">₹3,000.00</div>
          <div class="t-sub">Emergency Floor: ₹2,000.00 Invariant</div>
        </div>
        <div class="trading-metric-box">
          <div class="t-label">NET REALIZED P&L</div>
          <div class="t-val" id="net-pnl">₹0.00</div>
          <div class="t-sub" id="pnl-pct">0.00% Return</div>
        </div>
        <div class="trading-metric-box">
          <div class="t-label">REGULATORY FRICTION</div>
          <div class="t-val" id="total-fees" style="color:var(--gf-red);">₹0.00</div>
          <div class="t-sub">STT, GST, SEBI (~₹52/lot round-trip)</div>
        </div>
        <div class="trading-metric-box">
          <div class="t-label">TOTAL PORTFOLIO EQUITY</div>
          <div class="t-val" id="port-val">₹3,000.00</div>
          <div class="t-sub" id="drawdown-val">Drawdown: 0.0%</div>
        </div>
      </div>

      <!-- Action Controls -->
      <div class="btn-row">
        <button class="btn-danger-act" onclick="engageKillSwitch()">
          🛑 EMERGENCY KILL SWITCH
        </button>
        <button class="btn-primary-act" onclick="resetPaperAccount()">
          🔄 RESET TO ₹3,000 CAPITAL
        </button>
      </div>

      <!-- Auto-Pilot Execution Panel -->
      <div class="gf-list-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
          <div>
            <div style="font-size:11px; font-weight:700; color:var(--gf-blue);">AUTONOMOUS EXECUTION</div>
            <h3 style="font-size:16px; font-weight:700;">Single-Leg Breakout Auto-Pilot</h3>
          </div>
          <span id="auto-trade-badge" style="background:var(--gf-green-pill); color:var(--gf-green); font-size:11px; font-weight:700; padding:3px 8px; border-radius:6px;">🟢 AUTO ON</span>
        </div>

        <div id="managed-trade-container" style="background:#292a2d; border-radius:12px; padding:12px; margin-bottom:12px; font-size:12px; color:var(--gf-text-secondary); text-align:center;">
          Scanning orderbooks. Auto-Pilot enters single-leg breakouts when ML conviction ≥ 55% and Net P&L clears the ₹52 statutory hurdle.
        </div>

        <div class="btn-row" style="margin-bottom:0;">
          <button id="btn-toggle-auto" class="btn-primary-act" onclick="toggleAutoPilot()">
            <span>Complete Trade (Auto Active)</span>
          </button>
          <button class="btn-danger-act" onclick="triggerSquareOffAll()">
            🛑 15:15 Square-Off All
          </button>
        </div>
      </div>

      <!-- Champion-Challenger AI Status -->
      <div class="gf-list-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <div>
            <div style="font-size:11px; font-weight:700; color:var(--gf-blue);">SELF-LEARNING GOVERNANCE</div>
            <h3 style="font-size:15px; font-weight:700;" id="champion-model-text">CHAMPION_BASELINE_V1</h3>
          </div>
          <button onclick="evaluateChallengerGate()" style="background:#303134; border:1px solid var(--gf-border); color:#fff; border-radius:12px; padding:6px 12px; font-size:11px; font-weight:700; cursor:pointer;">
            Evaluate Challenger Gate
          </button>
        </div>
      </div>

    </div>

    <!-- ======================================================== -->
    <!-- TAB 3: OPTIONS CHAIN                                     -->
    <!-- ======================================================== -->
    <div id="tab-chain" class="tab-section">
      <div class="gf-list-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px; flex-wrap:wrap; gap:8px;">
          <div>
            <h3 style="font-size:16px; font-weight:700;">NIFTY Options Chain (65 Units / Lot)</h3>
            <div style="font-size:11px; color:var(--gf-text-secondary);">Filtered to ATM & OTM contracts under ₹38.00 premium cap (₹3,000 capital)</div>
          </div>
          <button onclick="hydrateFromREST()" style="background:#303134; border:1px solid var(--gf-border); color:#fff; padding:6px 12px; border-radius:10px; font-size:12px; font-weight:600; cursor:pointer;">
            🔄 Refresh Quotes
          </button>
        </div>

        <div id="quotes-list" style="display:flex; flex-direction:column; gap:8px;">
          <div style="text-align:center; padding:20px; color:var(--gf-text-secondary);">Loading quotes...</div>
        </div>
      </div>
    </div>

    <!-- ======================================================== -->
    <!-- TAB 4: ORDERS & TRADES                                   -->
    <!-- ======================================================== -->
    <div id="tab-orders" class="tab-section">
      <div class="gf-list-card">
        <h3 style="font-size:16px; font-weight:700; margin-bottom:12px;">Active Positions</h3>
        <div id="positions-list">
          <div style="text-align:center; padding:15px; color:var(--gf-text-secondary);">No open positions.</div>
        </div>
      </div>

      <div class="gf-list-card">
        <h3 style="font-size:16px; font-weight:700; margin-bottom:12px;">Recent Executions & Closed Trades</h3>
        <div id="trades-list">
          <div style="text-align:center; padding:15px; color:var(--gf-text-secondary);">Loading trade audit history...</div>
        </div>
      </div>
    </div>

    <!-- ======================================================== -->
    <!-- TAB 5: GREEKS & ML                                       -->
    <!-- ======================================================== -->
    <div id="tab-greeks" class="tab-section">
      <div class="gf-list-card">
        <h3 style="font-size:16px; font-weight:700; margin-bottom:12px;">Black-Scholes Greek Calculator</h3>
        <div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:10px; margin-bottom:12px;">
          <input type="number" id="bs-spot" placeholder="Spot (e.g. 23329)" value="23329" style="background:#303134; border:1px solid var(--gf-border); color:#fff; padding:8px; border-radius:8px;">
          <input type="number" id="bs-strike" placeholder="Strike (e.g. 23350)" value="23350" style="background:#303134; border:1px solid var(--gf-border); color:#fff; padding:8px; border-radius:8px;">
          <input type="number" id="bs-days" placeholder="Days to Expiry (4)" value="4" style="background:#303134; border:1px solid var(--gf-border); color:#fff; padding:8px; border-radius:8px;">
          <select id="bs-type" style="background:#303134; border:1px solid var(--gf-border); color:#fff; padding:8px; border-radius:8px;">
            <option value="CE">CALL (CE)</option>
            <option value="PE">PUT (PE)</option>
          </select>
        </div>
        <button onclick="calculateGreeksUI()" class="btn-primary-act" style="width:100%;">Calculate Greeks</button>
        <div id="greeks-result-box" style="margin-top:12px; font-family:'JetBrains Mono',monospace; font-size:12px;"></div>
      </div>

      <div class="gf-list-card">
        <h3 style="font-size:16px; font-weight:700; margin-bottom:8px;">Adaptive ML Model Drift Guard</h3>
        <p style="font-size:12px; color:var(--gf-text-secondary); margin-bottom:12px;">Monitors consecutive loss sequences to autonomously roll back unviable models to champion weights.</p>
        <div id="drift-guard-status" style="font-size:12px; color:#fff; font-family:'JetBrains Mono',monospace; background:#292a2d; padding:10px; border-radius:8px;">
          Status: Normal · Rollbacks: 0 · Consecutive Losses: 0
        </div>
      </div>
    </div>

    <!-- ======================================================== -->
    <!-- TAB 6: MARKET NEWS & GLOBAL MACRO                        -->
    <!-- ======================================================== -->
    <div id="tab-news" class="tab-section">

      <!-- Macro Indicators Header -->
      <div class="gf-list-card">
        <h3 style="font-size:16px; font-weight:700; margin-bottom:12px;">Global Macro Telemetry</h3>
        <div class="macro-stat-grid">
          <div class="trading-metric-box">
            <div class="t-label">BRENT CRUDE</div>
            <div class="t-val" id="macro-brent-price" style="font-size:18px;">$74.20</div>
            <div class="t-sub" style="color:var(--gf-red);">↓ 1.20%</div>
          </div>
          <div class="trading-metric-box">
            <div class="t-label">DOLLAR INDEX (DXY)</div>
            <div class="t-val" id="macro-dxy-price" style="font-size:18px;">104.15</div>
            <div class="t-sub" style="color:var(--gf-green);">↑ 0.18%</div>
          </div>
          <div class="trading-metric-box">
            <div class="t-label">GIFT NIFTY GAP</div>
            <div class="t-val" id="macro-gift-gap" style="font-size:18px;">-15 pts</div>
            <div class="t-sub">Expected Open Dip</div>
          </div>
          <div class="trading-metric-box">
            <div class="t-label">GEOPOLITICAL FEAR</div>
            <div class="t-val" id="macro-fear-idx" style="font-size:18px;">0.32</div>
            <div class="t-sub" style="color:var(--gf-green);">Low / Stable</div>
          </div>
        </div>
      </div>

      <!-- Financial News Grid -->
      <div class="gf-news-section">
        <div class="gf-news-header">
          <h2 class="gf-news-title">Curated Financial News</h2>
          <span style="font-size:11px; color:var(--gf-text-secondary);">Real-Time RSS Feed</span>
        </div>

        <div class="gf-news-grid" id="gf-news-container">
          <!-- Featured Live Card -->
          <div class="gf-news-card" style="grid-column: 1 / -1;">
            <div class="gf-news-content">
              <div class="gf-news-source">
                <span class="source-badge-live">LIVE ●</span>
                <span>The Economic Times</span>
              </div>
              <h3 class="gf-news-heading">Sensex Today | Nifty 50 | Stock Market Highlights: Sensex ends 330 pts lower, Nifty below 23,400; Bajaj, RIL lead slide</h3>
              <div class="gf-news-time">3 hours ago • Market Analysis</div>
            </div>
            <div class="gf-news-thumb" style="background:#2a1b1b; color:#ff7788;">📉</div>
          </div>

          <!-- Card 2 -->
          <div class="gf-news-card">
            <div class="gf-news-content">
              <div class="gf-news-source">Investing.com India</div>
              <h3 class="gf-news-heading">India shares lower at close of trade; Nifty 50 down 0.36%</h3>
              <div class="gf-news-time">4 hours ago</div>
            </div>
            <div class="gf-news-thumb" style="background:#1b252a; color:#8ab4f8;">🏛️</div>
          </div>

          <!-- Card 3 -->
          <div class="gf-news-card">
            <div class="gf-news-content">
              <div class="gf-news-source">Liquide Blog</div>
              <h3 class="gf-news-heading">Share Market Today: Nifty 50, Bank Nifty | Sep 22, 2026</h3>
              <div class="gf-news-time">3 hours ago</div>
            </div>
            <div class="gf-news-thumb" style="background:#2a1b25; color:#c084fc;">📊</div>
          </div>

          <!-- Card 4 -->
          <div class="gf-news-card">
            <div class="gf-news-content">
              <div class="gf-news-source">BusinessLine</div>
              <h3 class="gf-news-heading">Stock Market Today Highlights: Sensex falls 330 pts, Nifty below 23,400 on crude spike</h3>
              <div class="gf-news-time">4 hours ago</div>
            </div>
            <div class="gf-news-thumb" style="background:#252a1b; color:#81c995;">🛢️</div>
          </div>

          <!-- Card 5 -->
          <div class="gf-news-card">
            <div class="gf-news-content">
              <div class="gf-news-source">Moneycontrol</div>
              <h3 class="gf-news-heading">Live: Nifty below 23,400 on expiry day, Oil below $100, FII outflows stabilize</h3>
              <div class="gf-news-time">4 hours ago</div>
            </div>
            <div class="gf-news-thumb" style="background:#1b252a; color:#8ab4f8;">📺</div>
          </div>
        </div>
      </div>

    </div>

  </main>

  <script>
    // Tab Switching with URL Hash Synchronization and Real Working Links
    function switchMainTab(tabId, event) {
      if (event && event.preventDefault) event.preventDefault();

      const cleanId = tabId.startsWith('tab-') ? tabId : 'tab-' + tabId;
      const slug = cleanId.replace('tab-', '');

      // 1. Activate Section Panel
      document.querySelectorAll('.tab-section').forEach(el => el.classList.remove('active'));
      const target = document.getElementById(cleanId);
      if (target) {
        target.classList.add('active');
      }

      // 2. Activate Corresponding Navigation Link
      document.querySelectorAll('.nav-tab-item').forEach(el => {
        const itemSlug = el.getAttribute('data-tab') || el.getAttribute('href')?.replace('#', '');
        if (itemSlug === slug) {
          el.classList.add('active');
        } else {
          el.classList.remove('active');
        }
      });

      // 3. Update URL Hash
      if (history.pushState) {
        history.pushState(null, null, '#' + slug);
      } else {
        window.location.hash = '#' + slug;
      }

      // 4. Trigger specific data hydration hooks
      if (cleanId === 'tab-chain') hydrateFromREST();
      if (cleanId === 'tab-orders') { loadOrders(); loadTrades(); }
      if (cleanId === 'tab-overview') resizeChart();
      if (cleanId === 'tab-news') loadMacroStatus();
      if (cleanId === 'tab-trading') updatePnL();
    }

    // Handle browser back/forward and direct URL bookmark hashes
    window.addEventListener('hashchange', () => {
      const hash = window.location.hash.replace('#', '');
      if (hash && document.getElementById('tab-' + hash)) {
        switchMainTab(hash);
      }
    });

    // --- Interactive Google Finance Chart Engine ---
    let chartCanvas = null;
    let chartCtx = null;
    let currentTimeframe = '1D';
    let rawChartData = [];
    let prevClosePrice = 23414.30;
    let liveSpotPrice = 23329.00;

    // Generate authentic realistic series matching today's session
    function generateSeriesForTimeframe(tf) {
      const data = [];
      if (tf === '1D') {
        // Intraday from 09:15 to 15:30
        const times = ['09:15', '09:30', '09:45', '10:00', '10:30', '11:00', '11:30', '12:00', '12:30', '13:00', '13:30', '14:00', '14:30', '15:00', '15:30'];
        const values = [23454.05, 23472.10, 23489.00, 23460.50, 23420.25, 23395.10, 23360.80, 23340.20, 23315.40, 23285.75, 23310.20, 23355.60, 23340.10, 23312.30, liveSpotPrice];
        for (let i = 0; i < values.length - 1; i++) {
          const steps = 5;
          for (let s = 0; s < steps; s++) {
            const frac = s / steps;
            const p = values[i] + (values[i+1] - values[i]) * frac + (Math.sin(s * 1.5) * 4.0);
            data.push({ time: times[i] || '11:00', price: round2(p) });
          }
        }
        data.push({ time: '15:30', price: liveSpotPrice });
      } else if (tf === '5D') {
        const days = ['16 Sep', '17 Sep', '18 Sep', '19 Sep', '22 Sep'];
        const vals = [23650.0, 23580.0, 23520.0, 23414.3, liveSpotPrice];
        vals.forEach((v, idx) => data.push({ time: days[idx], price: v }));
      } else if (tf === '1M') {
        const pts = [23800, 23950, 24100, 23900, 23750, 23600, 23414, liveSpotPrice];
        pts.forEach((v, idx) => data.push({ time: `Wk ${idx+1}`, price: v }));
      } else {
        const base = 22000;
        for (let i = 0; i < 20; i++) {
          data.push({ time: `P${i}`, price: base + Math.sin(i * 0.4) * 1500 + i * 80 });
        }
        data.push({ time: 'Now', price: liveSpotPrice });
      }
      return data;
    }

    function round2(v) { return Math.round(v * 100) / 100; }

    function initFinanceChart() {
      chartCanvas = document.getElementById('nifty-chart-canvas');
      if (!chartCanvas) return;
      chartCtx = chartCanvas.getContext('2d');
      rawChartData = generateSeriesForTimeframe('1D');
      setupChartInteractions();
      renderChart();
      window.addEventListener('resize', resizeChart);
    }

    function setTimeframe(tf) {
      currentTimeframe = tf;
      document.querySelectorAll('.gf-tf-pill').forEach(b => {
        b.classList.toggle('active', b.dataset.tf === tf);
      });
      rawChartData = generateSeriesForTimeframe(tf);
      renderChart();
    }

    function resizeChart() {
      if (!chartCanvas) return;
      const rect = chartCanvas.parentElement.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      chartCanvas.width = rect.width * dpr;
      chartCanvas.height = rect.height * dpr;
      chartCtx.resetTransform();
      chartCtx.scale(dpr, dpr);
      renderChart();
    }

    function renderChart(hoverIdx = -1) {
      if (!chartCanvas || !chartCtx || rawChartData.length === 0) return;
      const rect = chartCanvas.parentElement.getBoundingClientRect();
      const W = rect.width;
      const H = rect.height;

      chartCtx.clearRect(0, 0, W, H);

      // Price Extents
      const prices = rawChartData.map(d => d.price);
      let minP = Math.min(...prices, prevClosePrice) - 30;
      let maxP = Math.max(...prices, prevClosePrice) + 30;
      const rangeP = maxP - minP || 1;

      const padTop = 20;
      const padBottom = 26;
      const chartH = H - padTop - padBottom;

      const getY = p => padTop + chartH - ((p - minP) / rangeP) * chartH;
      const getX = idx => (idx / (rawChartData.length - 1)) * W;

      // 1. Dotted Reference Line: Previous Close
      const prevCloseY = getY(prevClosePrice);
      chartCtx.save();
      chartCtx.setLineDash([4, 4]);
      chartCtx.strokeStyle = 'rgba(255, 255, 255, 0.28)';
      chartCtx.lineWidth = 1;
      chartCtx.beginPath();
      chartCtx.moveTo(0, prevCloseY);
      chartCtx.lineTo(W, prevCloseY);
      chartCtx.stroke();

      // Label: Previous close
      chartCtx.fillStyle = 'rgba(255, 255, 255, 0.5)';
      chartCtx.font = '10px "Plus Jakarta Sans", sans-serif';
      chartCtx.textAlign = 'right';
      chartCtx.fillText(`Previous close ${prevClosePrice.toLocaleString('en-IN', {minimumFractionDigits:2})}`, W - 8, prevCloseY - 6);
      chartCtx.restore();

      // 2. Draw Intraday Line & Gradient Fill
      const isDown = (prices[prices.length - 1] < prevClosePrice);
      const lineColor = isDown ? '#f28b82' : '#81c995';

      // Area gradient
      const grad = chartCtx.createLinearGradient(0, padTop, 0, H - padBottom);
      if (isDown) {
        grad.addColorStop(0, 'rgba(242, 139, 130, 0.25)');
        grad.addColorStop(1, 'rgba(242, 139, 130, 0.00)');
      } else {
        grad.addColorStop(0, 'rgba(129, 201, 149, 0.25)');
        grad.addColorStop(1, 'rgba(129, 201, 149, 0.00)');
      }

      chartCtx.beginPath();
      chartCtx.moveTo(getX(0), getY(prices[0]));
      for (let i = 1; i < rawChartData.length; i++) {
        chartCtx.lineTo(getX(i), getY(prices[i]));
      }
      chartCtx.strokeStyle = lineColor;
      chartCtx.lineWidth = 2.2;
      chartCtx.stroke();

      // Close path for fill
      chartCtx.lineTo(W, H - padBottom);
      chartCtx.lineTo(0, H - padBottom);
      chartCtx.closePath();
      chartCtx.fillStyle = grad;
      chartCtx.fill();

      // 3. Time Axis Labels
      chartCtx.fillStyle = 'var(--gf-text-secondary)';
      chartCtx.font = '11px "Plus Jakarta Sans", sans-serif';
      chartCtx.textAlign = 'center';
      if (currentTimeframe === '1D') {
        chartCtx.fillText('11:00 am', W * 0.28, H - 6);
        chartCtx.fillText('1:00 pm', W * 0.58, H - 6);
        chartCtx.fillText('3:00 pm', W * 0.88, H - 6);
      }

      // 4. Interactive Hover Crosshair
      if (hoverIdx >= 0 && hoverIdx < rawChartData.length) {
        const hX = getX(hoverIdx);
        const hY = getY(prices[hoverIdx]);

        chartCtx.save();
        chartCtx.setLineDash([3, 3]);
        chartCtx.strokeStyle = 'rgba(255, 255, 255, 0.6)';
        chartCtx.lineWidth = 1;
        chartCtx.beginPath();
        chartCtx.moveTo(hX, padTop);
        chartCtx.lineTo(hX, H - padBottom);
        chartCtx.stroke();

        // Circle at point
        chartCtx.fillStyle = lineColor;
        chartCtx.beginPath();
        chartCtx.arc(hX, hY, 4.5, 0, Math.PI * 2);
        chartCtx.fill();
        chartCtx.restore();
      }
    }

    function setupChartInteractions() {
      const tooltip = document.getElementById('chart-hover-tooltip');
      const handleMove = (clientX) => {
        if (!chartCanvas || rawChartData.length === 0) return;
        const rect = chartCanvas.getBoundingClientRect();
        const offsetX = Math.max(0, Math.min(rect.width, clientX - rect.left));
        const idx = Math.round((offsetX / rect.width) * (rawChartData.length - 1));
        const pt = rawChartData[idx];

        renderChart(idx);

        if (tooltip && pt) {
          tooltip.style.display = 'block';
          tooltip.style.left = Math.min(rect.width - 110, Math.max(10, offsetX - 50)) + 'px';
          tooltip.innerText = `${pt.time || ''} • ₹${pt.price.toLocaleString('en-IN', {minimumFractionDigits: 2})}`;

          // Live update header spot during scrubbing
          updateSpotHeader(pt.price, false);
        }
      };

      chartCanvas.addEventListener('mousemove', e => handleMove(e.clientX));
      chartCanvas.addEventListener('mouseleave', () => {
        renderChart(-1);
        if (tooltip) tooltip.style.display = 'none';
        updateSpotHeader(liveSpotPrice, true);
      });

      chartCanvas.addEventListener('touchmove', e => {
        if (e.touches.length > 0) handleMove(e.touches[0].clientX);
      }, { passive: true });
      chartCanvas.addEventListener('touchend', () => {
        renderChart(-1);
        if (tooltip) tooltip.style.display = 'none';
        updateSpotHeader(liveSpotPrice, true);
      });
    }

    function updateSpotHeader(price, isCommitted = false) {
      if (isCommitted) liveSpotPrice = price;
      const spEl = document.getElementById('spot-price');
      if (spEl) spEl.innerText = price.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

      const diff = price - prevClosePrice;
      const pct = (diff / prevClosePrice) * 100;
      const isDown = diff < 0;

      const pillEl = document.getElementById('spot-pill');
      const arrowEl = document.getElementById('pill-arrow');
      const pctEl = document.getElementById('pill-pct');
      const ptsEl = document.getElementById('spot-points-text');

      if (pillEl) pillEl.className = 'gf-change-pill ' + (isDown ? 'down' : 'up');
      if (arrowEl) arrowEl.innerText = isDown ? '↓' : '↑';
      if (pctEl) pctEl.innerText = Math.abs(pct).toFixed(2) + '%';
      if (ptsEl) {
        ptsEl.className = 'gf-change-pts ' + (isDown ? 'down' : 'up');
        ptsEl.innerText = `${diff >= 0 ? '+' : ''}${diff.toFixed(2)} today`;
      }
    }

    // --- Authentication & WebSocket Telemetry ---
    function getApiKey() {
      const loc = window.location;
      const urlParams = new URLSearchParams(loc.search);
      const injectedKey = (window.__SERQ_CONFIG__ && window.__SERQ_CONFIG__.apiKey) || '';
      const apiKey = urlParams.get('api_key') || localStorage.getItem('serq_api_key') || injectedKey || '';
      if (apiKey && !localStorage.getItem('serq_api_key')) {
        localStorage.setItem('serq_api_key', apiKey);
      }
      return apiKey;
    }

    function getAuthHeaders(extraHeaders = {}) {
      const apiKey = getApiKey();
      const headers = { 'Content-Type': 'application/json', ...extraHeaders };
      if (apiKey) headers['X-API-Key'] = apiKey;
      return headers;
    }

    let socket = null;
    let pingInterval = null;

    function initWebSocket() {
      const loc = window.location;
      const protocol = (loc.protocol === 'https:') ? 'wss:' : 'ws:';
      const apiKey = getApiKey();
      const wsUrl = `${protocol}//${loc.host}/ws/stream${apiKey ? '?api_key=' + encodeURIComponent(apiKey) : ''}`;

      const statusContainer = document.getElementById('live-status-container');
      const dot = document.getElementById('live-dot');
      const text = document.getElementById('ws-status-text');
      const latencyEl = document.getElementById('ws-latency');

      try {
        socket = new WebSocket(wsUrl);

        socket.onopen = () => {
          if (statusContainer) {
            statusContainer.style.background = 'rgba(129, 201, 149, 0.15)';
            statusContainer.style.color = 'var(--gf-green)';
          }
          if (dot) dot.style.background = 'var(--gf-green)';
          if (text) text.innerText = 'LIVE';

          clearInterval(pingInterval);
          pingInterval = setInterval(() => {
            if (socket.readyState === WebSocket.OPEN) {
              socket.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
            }
          }, 3000);
        };

        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'pong') {
              const rtt = Date.now() - data.timestamp;
              if (latencyEl) latencyEl.innerText = `${rtt}ms`;
              return;
            }
            if (data.type === 'tick') {
              handleLiveTick(data.data);
            }
          } catch (e) {}
        };

        socket.onclose = () => {
          if (statusContainer) {
            statusContainer.style.background = 'rgba(242, 139, 130, 0.15)';
            statusContainer.style.color = 'var(--gf-red)';
          }
          if (dot) dot.style.background = 'var(--gf-red)';
          if (text) text.innerText = 'OFFLINE';
          if (latencyEl) latencyEl.innerText = '';
          clearInterval(pingInterval);
          setTimeout(initWebSocket, 3000);
        };

        socket.onerror = () => { socket.close(); };
      } catch (e) {
        setTimeout(initWebSocket, 3000);
      }
    }

    function handleLiveTick(tick) {
      if (!tick) return;
      if (tick.symbol === 'NIFTY 50' || tick.symbol === 'NIFTY' || tick.symbol.includes('INDEX')) {
        updateSpotHeader(tick.ltp, true);
        if (tick.open) document.getElementById('stat-open').innerText = Number(tick.open).toLocaleString('en-IN', {minimumFractionDigits:2});
        if (tick.high) document.getElementById('stat-high').innerText = Number(tick.high).toLocaleString('en-IN', {minimumFractionDigits:2});
        if (tick.low) document.getElementById('stat-low').innerText = Number(tick.low).toLocaleString('en-IN', {minimumFractionDigits:2});
        if (tick.close) {
          prevClosePrice = Number(tick.close);
          document.getElementById('stat-prev-close').innerText = prevClosePrice.toLocaleString('en-IN', {minimumFractionDigits:2});
        }
      }
    }

    // --- REST Telemetry Fetchers ---
    async function updatePnL() {
      try {
        const res = await fetch('/api/pnl', { headers: getAuthHeaders() });
        if (!res.ok) return;
        const data = await res.json();

        const cashEl = document.getElementById('cash-val');
        const topCashEl = document.getElementById('top-cash-val');
        const pnlEl = document.getElementById('net-pnl');
        const pctEl = document.getElementById('pnl-pct');
        const feesEl = document.getElementById('total-fees');
        const portEl = document.getElementById('port-val');
        const ddEl = document.getElementById('drawdown-val');

        const cashStr = `₹${Number(data.current_cash).toLocaleString('en-IN', {minimumFractionDigits:2, maximumFractionDigits:2})}`;
        if (cashEl) cashEl.innerText = cashStr;
        if (topCashEl) topCashEl.innerText = cashStr;

        if (pnlEl) {
          pnlEl.innerText = `₹${Number(data.net_pnl).toLocaleString('en-IN', {minimumFractionDigits:2})}`;
          pnlEl.style.color = data.net_pnl >= 0 ? 'var(--gf-green)' : 'var(--gf-red)';
        }
        if (pctEl) pctEl.innerText = `${data.net_pnl_percentage >= 0 ? '+' : ''}${data.net_pnl_percentage.toFixed(2)}% Return`;
        if (feesEl) feesEl.innerText = `₹${Number(data.total_friction_inr).toLocaleString('en-IN', {minimumFractionDigits:2})}`;
        if (portEl) portEl.innerText = `₹${Number(data.total_portfolio_value).toLocaleString('en-IN', {minimumFractionDigits:2})}`;
        if (ddEl) ddEl.innerText = `Drawdown: ${data.drawdown_pct.toFixed(2)}% (Max: ${data.max_drawdown_pct.toFixed(2)}%)`;
      } catch (e) {}
    }

    async function checkMarketStatus() {
      try {
        const res = await fetch('/api/scheduler/status', { headers: getAuthHeaders() });
        if (!res.ok) return;
        const data = await res.json();

        const banner = document.getElementById('market-status-banner');
        const title = document.getElementById('market-status-title');
        const sub = document.getElementById('market-status-sub');
        const tag = document.getElementById('market-status-tag');

        if (!data.is_trading_permitted) {
          banner.style.display = 'flex';
          title.innerText = `NSE MARKET CLOSED (${data.current_phase.replace('_', ' ')})`;
          sub.innerText = data.guard_status || 'Platform standing down in capital preservation mode.';
          tag.innerText = 'STAND-DOWN';
        } else {
          banner.style.display = 'none';
        }
      } catch (e) {}
    }

    async function checkKillSwitch() {
      try {
        const res = await fetch('/api/status', { headers: getAuthHeaders() });
        if (!res.ok) return;
        const data = await res.json();

        const alertEl = document.getElementById('kill-alert');
        const reasonEl = document.getElementById('kill-reason');
        if (data.kill_switch && data.kill_switch.engaged) {
          alertEl.style.display = 'block';
          reasonEl.innerText = `(${data.kill_switch.reason})`;
        } else {
          alertEl.style.display = 'none';
        }

        if (data.champion_challenger) {
          const mText = document.getElementById('champion-model-text');
          if (mText) mText.innerText = data.champion_challenger.champion_id || 'CHAMPION_BASELINE_V1';
        }
      } catch (e) {}
    }

    async function hydrateFromREST() {
      try {
        const res = await fetch('/api/quotes', { headers: getAuthHeaders() });
        if (!res.ok) return;
        const quotes = await res.json();

        const list = document.getElementById('quotes-list');
        if (!list) return;

        if (quotes.length === 0) {
          list.innerHTML = '<div style="text-align:center; padding:15px; color:var(--gf-text-secondary);">No active option quotes found under ₹38.00 cap.</div>';
          return;
        }

        let html = '';
        quotes.slice(0, 15).forEach(q => {
          const isCE = q.symbol.includes('_CE');
          const badgeClass = isCE ? 'style="color:var(--gf-green); font-weight:700;"' : 'style="color:var(--gf-red); font-weight:700;"';
          html += `
            <div class="gf-list-item">
              <div>
                <span ${badgeClass}>${isCE ? 'CALL' : 'PUT'}</span>
                <strong style="margin-left:6px; color:#fff;">${q.symbol}</strong>
                <div style="font-size:11px; color:var(--gf-text-secondary); margin-top:2px;">
                  Bid: ₹${Number(q.best_bid || 0).toFixed(2)} | Ask: ₹${Number(q.best_ask || 0).toFixed(2)} | Vol: ${q.volume || 0}
                </div>
              </div>
              <div style="display:flex; align-items:center; gap:10px;">
                <span style="font-family:'JetBrains Mono',monospace; font-size:14px; font-weight:700; color:#fff;">₹${Number(q.ltp).toFixed(2)}</span>
                <button class="btn-buy-chip" onclick="quickBuyOrder('${q.symbol}', ${q.best_ask || q.ltp})">BUY 1 LOT</button>
              </div>
            </div>
          `;
        });
        list.innerHTML = html;
      } catch (e) {}
    }

    async function loadOrders() {
      try {
        const resPos = await fetch('/api/positions', { headers: getAuthHeaders() });
        const posList = document.getElementById('positions-list');
        if (resPos.ok) {
          const positions = await resPos.json();
          if (positions.length === 0) {
            posList.innerHTML = '<div style="text-align:center; padding:15px; color:var(--gf-text-secondary);">No open positions held. 1-Lot capital floor intact.</div>';
          } else {
            let phtml = '';
            positions.forEach(p => {
              const pnlCol = p.unrealized_pnl >= 0 ? 'var(--gf-green)' : 'var(--gf-red)';
              phtml += `
                <div class="gf-list-item">
                  <div>
                    <strong style="color:#fff;">${p.symbol}</strong>
                    <div style="font-size:11px; color:var(--gf-text-secondary);">Qty: ${p.quantity} @ ₹${Number(p.average_price).toFixed(2)} | LTP: ₹${Number(p.current_price).toFixed(2)}</div>
                  </div>
                  <div style="text-align:right;">
                    <div style="font-family:'JetBrains Mono',monospace; font-weight:700; color:${pnlCol};">
                      ${p.unrealized_pnl >= 0 ? '+' : ''}₹${Number(p.unrealized_pnl).toFixed(2)}
                    </div>
                    <button class="btn-danger-act" style="padding:2px 8px; font-size:11px; margin-top:4px;" onclick="triggerSquareOffAll()">Exit</button>
                  </div>
                </div>
              `;
            });
            posList.innerHTML = phtml;
          }
        }

        const resTrd = await fetch('/api/trades', { headers: getAuthHeaders() });
        const trdList = document.getElementById('trades-list');
        if (resTrd.ok) {
          const trades = await resTrd.json();
          if (trades.length === 0) {
            trdList.innerHTML = '<div style="text-align:center; padding:15px; color:var(--gf-text-secondary);">No trade execution records yet.</div>';
          } else {
            let thtml = '';
            trades.slice(0, 10).forEach(t => {
              thtml += `
                <div class="gf-list-item">
                  <div>
                    <span style="font-weight:700; color:${t.side === 'BUY' ? 'var(--gf-green)' : 'var(--gf-red)'};">${t.side}</span>
                    <span style="color:#fff; margin-left:6px;">${t.quantity}x ${t.symbol}</span>
                    <div style="font-size:11px; color:var(--gf-text-secondary);">${new Date(t.timestamp).toLocaleTimeString('en-IN')} • Fees: ₹${Number(t.total_costs).toFixed(2)}</div>
                  </div>
                  <div style="font-family:'JetBrains Mono',monospace; font-weight:700; color:#fff;">
                    ₹${Number(t.price).toFixed(2)}
                  </div>
                </div>
              `;
            });
            trdList.innerHTML = thtml;
          }
        }
      } catch (e) {}
    }

    async function loadMacroStatus() {
      try {
        const res = await fetch('/api/global-macro/status', { headers: getAuthHeaders() });
        if (!res.ok) return;
        const data = await res.json();
        if (data.macro) {
          const bEl = document.getElementById('macro-brent-price');
          const dEl = document.getElementById('macro-dxy-price');
          const gEl = document.getElementById('macro-gift-gap');
          if (bEl) bEl.innerText = `$${Number(data.macro.brent_crude_usd).toFixed(2)}`;
          if (dEl) dEl.innerText = Number(data.macro.dollar_index_dxy).toFixed(2);
          if (gEl) gEl.innerText = `${data.macro.gift_nifty_gap_pts >= 0 ? '+' : ''}${data.macro.gift_nifty_gap_pts} pts`;
        }
        if (data.fusion) {
          const fEl = document.getElementById('macro-fear-idx');
          if (fEl) fEl.innerText = Number(data.fusion.geopolitical_fear_index).toFixed(2);
        }
      } catch (e) {}
    }

    // --- User Actions ---
    async function quickBuyOrder(symbol, price) {
      if (!confirm(`Place paper BUY order for 1 lot (65 units) of ${symbol} @ ~₹${price}?`)) return;
      try {
        const res = await fetch('/api/paper/order', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            symbol: symbol,
            side: 'BUY',
            order_type: 'MARKET',
            quantity: 65,
            price: price
          })
        });
        const data = await res.json();
        if (data.status === 'FILLED') {
          alert(`Order Filled! 65 units @ ₹${data.fill_price}. Friction fee: ₹${data.total_charges_inr}`);
          updatePnL();
          loadOrders();
        } else {
          alert(`Order Rejected: ${data.rejection_reason || 'Check risk limits'}`);
        }
      } catch (e) {
        alert('Execution failed: ' + e.message);
      }
    }

    async function triggerSquareOffAll() {
      if (!confirm('Execute emergency square-off for all open positions at market?')) return;
      try {
        const res = await fetch('/api/auto-trade/square-off', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ reason: 'MANUAL_DASHBOARD_PANIC' })
        });
        const data = await res.json();
        alert(`Square-off triggered: ${JSON.stringify(data)}`);
        updatePnL();
        loadOrders();
      } catch (e) {
        alert('Error: ' + e.message);
      }
    }

    async function engageKillSwitch() {
      const reason = prompt('Enter Kill Switch Engagement Reason:', 'Operator emergency manual halt');
      if (!reason) return;
      try {
        const res = await fetch('/api/kill-switch', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ action: 'ENGAGE', reason: reason })
        });
        const data = await res.json();
        alert('Emergency Kill Switch ENGAGED.');
        checkKillSwitch();
      } catch (e) {
        alert('Error: ' + e.message);
      }
    }

    async function resetKillSwitch() {
      if (!confirm('Disengage Kill Switch and restore trading permissions?')) return;
      try {
        const res = await fetch('/api/kill-switch', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ action: 'DISENGAGE' })
        });
        const data = await res.json();
        alert('Kill Switch Disengaged.');
        checkKillSwitch();
      } catch (e) {
        alert('Error: ' + e.message);
      }
    }

    async function resetPaperAccount() {
      if (!confirm('Reset Paper Account to pristine baseline of ₹3,000.00?')) return;
      try {
        const res = await fetch('/api/paper/reset', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({ initial_capital: 3000.0 })
        });
        const data = await res.json();
        alert('Account reset successfully to ₹3,000 baseline.');
        updatePnL();
        loadOrders();
      } catch (e) {
        alert('Error: ' + e.message);
      }
    }

    async function toggleAutoPilot() {
      try {
        const res = await fetch('/api/auto-trade/toggle', { method: 'POST', headers: getAuthHeaders() });
        const data = await res.json();
        const badge = document.getElementById('auto-trade-badge');
        const btn = document.getElementById('btn-toggle-auto');
        if (data.auto_trading_enabled) {
          badge.innerText = '🟢 AUTO ON';
          badge.style.background = 'var(--gf-green-pill)';
          badge.style.color = 'var(--gf-green)';
          btn.innerText = 'Pause Auto-Pilot';
        } else {
          badge.innerText = '⏸️ PAUSED';
          badge.style.background = 'rgba(255,255,255,0.1)';
          badge.style.color = 'var(--gf-text-secondary)';
          btn.innerText = 'Enable Auto-Pilot';
        }
      } catch (e) {}
    }

    async function evaluateChallengerGate() {
      try {
        const res = await fetch('/api/learning/evaluate-challenger', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({})
        });
        const data = await res.json();
        alert(`Evaluation Outcome: ${data.decision} (Reason: ${data.reason})`);
      } catch (e) {
        alert('Evaluation Error: ' + e.message);
      }
    }

    async function calculateGreeksUI() {
      const spot = parseFloat(document.getElementById('bs-spot').value);
      const strike = parseFloat(document.getElementById('bs-strike').value);
      const days = parseFloat(document.getElementById('bs-days').value);
      const optType = document.getElementById('bs-type').value;

      const box = document.getElementById('greeks-result-box');
      box.innerText = 'Calculating Black-Scholes Greeks...';

      try {
        const res = await fetch('/api/greeks/calculate', {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            spot: spot,
            strike: strike,
            days_to_expiry: days,
            option_type: optType,
            iv: 0.14
          })
        });
        const g = await res.json();
        box.innerHTML = `
          <div style="display:grid; grid-template-columns:repeat(3, 1fr); gap:8px; background:#1f1f1f; padding:10px; border-radius:8px;">
            <div>Delta: <strong style="color:#8ab4f8;">${g.delta}</strong></div>
            <div>Gamma: <strong style="color:#8ab4f8;">${g.gamma}</strong></div>
            <div>Theta: <strong style="color:var(--gf-red);">${g.theta_day}/day</strong></div>
            <div>Vega: <strong style="color:#81c995;">${g.vega}</strong></div>
            <div>Rho: <strong>${g.rho}</strong></div>
            <div>Theo Price: <strong>₹${g.theoretical_price}</strong></div>
          </div>
        `;
      } catch (e) {
        box.innerText = 'Calculation error: ' + e.message;
      }
    }

    // --- Lifecycle Initialization ---
    window.addEventListener('DOMContentLoaded', () => {
      initFinanceChart();
      initWebSocket();

      // Deep linking via URL hash (e.g. /#chain or /#trading)
      const initialHash = window.location.hash.replace('#', '');
      if (initialHash && document.getElementById('tab-' + initialHash)) {
        switchMainTab(initialHash);
      } else {
        switchMainTab('overview');
      }

      // Continuous polling timers
      updatePnL();
      checkMarketStatus();
      checkKillSwitch();
      hydrateFromREST();
      loadOrders();

      setInterval(updatePnL, 4000);
      setInterval(checkMarketStatus, 10000);
      setInterval(checkKillSwitch, 5000);
      setInterval(hydrateFromREST, 15000);
    });
  </script>
</body>
</html>
'''

with open("/root/nifty-options-arbitrage/dashboard/index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("SUCCESS: Modern trading platform dashboard generated with active nav links and no Google search bar.")

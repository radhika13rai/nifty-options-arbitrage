import os

html_content = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>NIFTY 50 - Google Search & Options HUD</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700;800&display=swap" rel="stylesheet">
  <style>
    :root {
      --gf-bg: #1f1f1f;
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

    /* Top Google Search Bar (Matches Screenshot) */
    .google-top-bar {
      background: #202124;
      padding: 10px 14px 4px 14px;
      position: sticky;
      top: 0;
      z-index: 100;
      border-bottom: 1px solid var(--gf-border);
    }

    .search-input-pill {
      display: flex;
      align-items: center;
      background: #303134;
      border-radius: 28px;
      padding: 8px 14px;
      gap: 12px;
      box-shadow: 0 1px 6px rgba(0,0,0,0.28);
    }

    .google-logo-svg {
      flex-shrink: 0;
      width: 22px;
      height: 22px;
    }

    .search-query-text {
      flex: 1;
      font-size: 15px;
      color: #fff;
      font-weight: 500;
      letter-spacing: -0.2px;
    }

    .search-icons-right {
      display: flex;
      align-items: center;
      gap: 12px;
      color: var(--gf-text-secondary);
    }

    .search-icon-btn {
      background: none;
      border: none;
      color: var(--gf-text-secondary);
      font-size: 15px;
      cursor: pointer;
      display: flex;
      align-items: center;
    }

    .search-divider {
      width: 1px;
      height: 18px;
      background: var(--gf-border);
    }

    /* Google Search Category Tabs (Matches Screenshot) */
    .google-nav-tabs {
      display: flex;
      gap: 20px;
      overflow-x: auto;
      padding: 10px 8px 0 8px;
      scrollbar-width: none;
    }
    .google-nav-tabs::-webkit-scrollbar { display: none; }

    .nav-tab-item {
      color: var(--gf-text-secondary);
      font-size: 13px;
      font-weight: 500;
      padding-bottom: 8px;
      white-space: nowrap;
      cursor: pointer;
      border-bottom: 3px solid transparent;
      transition: all 0.2s;
      text-decoration: none;
    }

    .nav-tab-item.active {
      color: #8ab4f8;
      border-bottom-color: #8ab4f8;
      font-weight: 600;
    }

    /* SerQ HUD Mode Bar */
    .hud-subnav {
      background: #171717;
      padding: 8px 14px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--gf-border);
      gap: 10px;
      overflow-x: auto;
    }

    .hud-pills {
      display: flex;
      gap: 8px;
      align-items: center;
    }

    .hud-tab-btn {
      padding: 6px 12px;
      border-radius: 16px;
      border: 1px solid var(--gf-border);
      background: #202124;
      color: var(--gf-text-secondary);
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
      white-space: nowrap;
      transition: all 0.2s;
    }

    .hud-tab-btn.active {
      background: #8ab4f8;
      color: #202124;
      border-color: #8ab4f8;
    }

    .live-status-pill {
      display: flex;
      align-items: center;
      gap: 6px;
      background: rgba(129, 201, 149, 0.15);
      border: 1px solid rgba(129, 201, 149, 0.3);
      color: var(--gf-green);
      padding: 4px 10px;
      border-radius: 14px;
      font-size: 11px;
      font-weight: 700;
      font-family: 'JetBrains Mono', monospace;
      white-space: nowrap;
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

    /* Main Content Wrapper */
    .gf-main-container {
      max-width: 900px;
      margin: 0 auto;
      padding: 16px 14px;
    }

    /* Tab Content Controls */
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

    /* Stand-down & Alert Banner */
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

    /* ======================================================== */
    /* GOOGLE FINANCE HERO SECTION (1:1 with Screenshot)        */
    /* ======================================================== */
    .gf-hero-card {
      background: var(--gf-card);
      border-radius: 20px;
      padding: 16px 18px;
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
      font-size: 26px;
      font-weight: 700;
      color: #fff;
      letter-spacing: -0.3px;
      line-height: 1.2;
    }

    .gf-asset-meta {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: var(--gf-text-secondary);
      margin-top: 2px;
    }

    .gf-follow-btn {
      display: flex;
      align-items: center;
      gap: 6px;
      background: #8ab4f8;
      color: #202124;
      border: none;
      border-radius: 18px;
      padding: 6px 14px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      transition: background 0.2s;
    }
    .gf-follow-btn:hover {
      background: var(--gf-blue-hover);
    }

    /* Spot Price & Change Row */
    .gf-price-container {
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-top: 6px;
      margin-bottom: 12px;
    }

    .gf-spot-big {
      font-size: 34px;
      font-weight: 700;
      font-family: 'JetBrains Mono', monospace;
      color: #fff;
      letter-spacing: -0.5px;
      line-height: 1.1;
    }

    .gf-pill-row {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 14px;
      font-weight: 600;
    }

    .gf-change-pill {
      display: inline-flex;
      align-items: center;
      gap: 3px;
      padding: 3px 8px;
      border-radius: 12px;
      font-size: 13px;
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
      font-family: 'JetBrains Mono', monospace;
      font-size: 13px;
      font-weight: 600;
    }
    .gf-change-pts.down { color: var(--gf-red); }
    .gf-change-pts.up { color: var(--gf-green); }

    .gf-market-timestamp {
      font-size: 12px;
      color: var(--gf-text-secondary);
      margin-top: 2px;
    }

    /* Timeframe Selector Pills (Matches Screenshot) */
    .gf-timeframe-row {
      display: flex;
      gap: 6px;
      overflow-x: auto;
      padding: 8px 0 14px 0;
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

    /* Key Statistics 6-Item Grid (Matches Screenshot) */
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

    /* Related Markets Card (Matches Screenshot) */
    .gf-related-card {
      background: var(--gf-card);
      border: 1px solid var(--gf-border);
      border-radius: 20px;
      padding: 16px 18px;
      margin-bottom: 16px;
    }

    .related-title {
      font-size: 15px;
      font-weight: 700;
      color: #fff;
      margin-bottom: 12px;
    }

    .related-item-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 0;
      border-bottom: 1px solid rgba(255,255,255,0.05);
      font-size: 13px;
    }

    .related-item-row:last-child {
      border-bottom: none;
    }

    .related-name-col {
      display: flex;
      align-items: center;
      gap: 10px;
      color: #fff;
      font-weight: 500;
    }

    .related-icon {
      color: var(--gf-text-secondary);
      font-size: 13px;
    }

    .related-price-col {
      display: flex;
      align-items: center;
      gap: 12px;
    }

    .related-price-val {
      font-family: 'JetBrains Mono', monospace;
      font-weight: 600;
      color: #fff;
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

    /* "Analyse NIFTY 50 >" Full Width Button (Matches Screenshot) */
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

    /* Google Finance Style News Section (Matches Screenshot) */
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

    .gf-customise-btn {
      background: #303134;
      border: 1px solid var(--gf-border);
      color: #fff;
      padding: 4px 12px;
      border-radius: 14px;
      font-size: 12px;
      font-weight: 600;
      cursor: pointer;
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
    }
    .gf-news-card:hover {
      border-color: #5f6368;
    }

    .gf-news-content {
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .gf-news-source {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 11px;
      color: var(--gf-text-secondary);
      margin-bottom: 4px;
    }

    .source-badge-live {
      background: #ea4335;
      color: #fff;
      font-size: 9px;
      font-weight: 800;
      padding: 1px 5px;
      border-radius: 4px;
      text-transform: uppercase;
    }

    .gf-news-heading {
      font-size: 13px;
      font-weight: 600;
      color: #e8eaed;
      line-height: 1.35;
      margin-bottom: 6px;
    }

    .gf-news-time {
      font-size: 11px;
      color: var(--gf-text-secondary);
    }

    .gf-news-thumb {
      width: 72px;
      height: 72px;
      border-radius: 12px;
      background: #303134;
      flex-shrink: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 26px;
      overflow: hidden;
    }

    /* ======================================================== */
    /* TRADING & RISK HUD TAB (Clean Google Dark Styling)       */
    /* ======================================================== */
    .trading-stat-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 12px;
      margin-bottom: 16px;
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
  </style>
</head>
<body>

  <!-- Top Google Search Header (1:1 with Screenshot) -->
  <header class="google-top-bar">
    <div class="search-input-pill">
      <!-- Colorful Google G logo -->
      <svg class="google-logo-svg" viewBox="0 0 24 24">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
      </svg>
      <div class="search-query-text">nifty 50</div>
      <div class="search-icons-right">
        <button class="search-icon-btn" title="Clear">✕</button>
        <span class="search-divider"></span>
        <button class="search-icon-btn" title="Voice Search">🎤</button>
        <button class="search-icon-btn" title="Google Lens">📷</button>
      </div>
    </div>

    <!-- Google Search Category Tabs (Matches Screenshot) -->
    <div class="google-nav-tabs">
      <a href="#overview" class="nav-tab-item active" onclick="switchMainTab('tab-overview')">All</a>
      <a href="#trading" class="nav-tab-item" onclick="switchMainTab('tab-trading')">Finance & HUD</a>
      <a href="#chain" class="nav-tab-item" onclick="switchMainTab('tab-chain')">Option Chain</a>
      <a href="#orders" class="nav-tab-item" onclick="switchMainTab('tab-orders')">Orders & PnL</a>
      <a href="#greeks" class="nav-tab-item" onclick="switchMainTab('tab-greeks')">Greeks & ML</a>
      <span class="nav-tab-item">News</span>
      <span class="nav-tab-item">Videos</span>
      <span class="nav-tab-item">More ▾</span>
    </div>
  </header>

  <!-- SerQ Execution Sub-bar -->
  <div class="hud-subnav">
    <div class="hud-pills">
      <button class="hud-tab-btn active" id="btn-tab-overview" onclick="switchMainTab('tab-overview')">📈 Chart View</button>
      <button class="hud-tab-btn" id="btn-tab-trading" onclick="switchMainTab('tab-trading')">⚡ Trading HUD</button>
      <button class="hud-tab-btn" id="btn-tab-chain" onclick="switchMainTab('tab-chain')">🎯 Option Chain</button>
    </div>
    <div class="live-status-pill" id="live-status-container">
      <div class="pulse-dot" id="live-dot"></div>
      <span id="ws-status-text">LIVE</span>
      <span id="ws-latency" style="opacity: 0.7; font-size: 10px; margin-left: 2px;"></span>
    </div>
  </div>

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
    <div id="kill-alert" style="display:none; background:var(--gf-red-pill); border:1px solid var(--gf-red); color:#fff; border-radius:14px; padding:12px 16px; margin-bottom:16px;">
      ⚠️ <strong>EMERGENCY KILL SWITCH ENGAGED!</strong> <span id="kill-reason"></span>
      <button onclick="resetKillSwitch()" style="margin-left:10px; padding:3px 8px; background:var(--gf-red); color:#202124; border:none; border-radius:4px; font-weight:700; cursor:pointer;">Reset</button>
    </div>

    <!-- ======================================================== -->
    <!-- SECTION 1: GOOGLE FINANCE OVERVIEW (1:1 with Screenshot)  -->
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
              <span style="cursor:pointer;">⋮</span>
            </div>
          </div>
          <button class="gf-follow-btn">
            <span>+</span> Follow
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
            22 Sept, 3:31 pm IST • <span id="market-session-label">NSE Regular Session</span> • Disclaimer
          </div>
        </div>

        <!-- Timeframe Selector (1D, 5D, 1M, 6M, YTD, 1Y, 5Y, Max) -->
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

        <!-- Interactive Line Chart Canvas -->
        <div class="gf-chart-wrap">
          <canvas id="nifty-chart-canvas"></canvas>
          <div class="chart-hover-pill" id="chart-hover-tooltip"></div>
        </div>

        <!-- Key Statistics 6-Item Grid (Matches Screenshot) -->
        <div class="gf-stats-grid">
          <div class="gf-stat-item">
            <span class="gf-stat-label">Open</span>
            <span class="gf-stat-value" id="stat-open">23,454.05</span>
          </div>
          <div class="gf-stat-item">
            <span class="gf-stat-label">Low</span>
            <span class="gf-stat-value" id="stat-low">23,285.75</span>
          </div>
          <div class="gf-stat-item">
            <span class="gf-stat-label">52-wk high</span>
            <span class="gf-stat-value">26,373.20</span>
          </div>
          <div class="gf-stat-item">
            <span class="gf-stat-label">High</span>
            <span class="gf-stat-value" id="stat-high">23,489.00</span>
          </div>
          <div class="gf-stat-item">
            <span class="gf-stat-label">Prev close</span>
            <span class="gf-stat-value" id="stat-prevclose">23,414.30</span>
          </div>
          <div class="gf-stat-item">
            <span class="gf-stat-label">52-wk low</span>
            <span class="gf-stat-value">22,182.55</span>
          </div>
        </div>
      </div>

      <!-- Related Markets Card (Matches Screenshot) -->
      <div class="gf-related-card">
        <div class="related-title">Related markets</div>
        <div class="related-item-row">
          <div class="related-name-col">
            <span class="related-icon">🔍</span>
            <span>Dow Jones Industrial Average</span>
          </div>
          <div class="related-price-col">
            <span class="related-price-val">51,799.24</span>
            <span class="related-pill down">↓ 0.48%</span>
          </div>
        </div>
        <div class="related-item-row">
          <div class="related-name-col">
            <span class="related-icon">🔍</span>
            <span>S&P 500</span>
          </div>
          <div class="related-price-col">
            <span class="related-price-val">7,766.27</span>
            <span class="related-pill up">↑ 0.020%</span>
          </div>
        </div>
        <div class="related-item-row">
          <div class="related-name-col">
            <span class="related-icon">🔍</span>
            <span>Nasdaq Composite</span>
          </div>
          <div class="related-price-col">
            <span class="related-price-val">27,247.65</span>
            <span class="related-pill up">↑ 0.46%</span>
          </div>
        </div>
        <div class="related-item-row">
          <div class="related-name-col">
            <span class="related-icon">🔍</span>
            <span>Russell 2000 Index</span>
          </div>
          <div class="related-price-col">
            <span class="related-price-val">2,905.79</span>
            <span class="related-pill up">↑ 1.06%</span>
          </div>
        </div>
        <div class="related-item-row">
          <div class="related-name-col">
            <span class="related-icon">🔍</span>
            <span>Brent Crude USD</span>
          </div>
          <div class="related-price-col">
            <span class="related-price-val" id="macro-brent-val">$74.20</span>
            <span class="related-pill down" id="macro-brent-pill">↓ 1.20%</span>
          </div>
        </div>
      </div>

      <!-- "Analyse NIFTY 50 >" Action Banner (Matches Screenshot) -->
      <button class="gf-analyse-banner" onclick="switchMainTab('tab-trading')">
        <span>Analyse NIFTY 50 Options & Arbitrage</span>
        <span style="font-size: 18px;">›</span>
      </button>

      <!-- Google Style News Grid (Matches Screenshot) -->
      <div class="gf-news-section">
        <div class="gf-news-header">
          <h2 class="gf-news-title">News</h2>
          <button class="gf-customise-btn">Customise</button>
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

    <!-- ======================================================== -->
    <!-- SECTION 2: TRADING & RISK HUD                           -->
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
    <!-- SECTION 3: OPTIONS CHAIN (65 QTY)                       -->
    <!-- ======================================================== -->
    <div id="tab-chain" class="tab-section">
      <div class="gf-list-card">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
          <div>
            <h3 style="font-size:16px; font-weight:700;">NIFTY Options Chain (65 Units)</h3>
            <div style="font-size:11px; color:var(--gf-text-secondary);">Filtered to ATM & OTM contracts under ₹3,000 capital cap</div>
          </div>
          <button onclick="hydrateFromREST()" style="background:#303134; border:1px solid var(--gf-border); color:#fff; padding:4px 10px; border-radius:10px; font-size:11px; cursor:pointer;">
            🔄 Refresh
          </button>
        </div>

        <div id="quotes-list" style="display:flex; flex-direction:column; gap:8px;">
          <div style="text-align:center; padding:20px; color:var(--gf-text-secondary);">Loading quotes...</div>
        </div>
      </div>
    </div>

    <!-- ======================================================== -->
    <!-- SECTION 4: ORDERS & TRADES                              -->
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
    <!-- SECTION 5: GREEKS & RISK                                -->
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
    </div>

  </main>

  <script>
    // Tab Switching
    function switchMainTab(tabId) {
      document.querySelectorAll('.tab-section').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.nav-tab-item').forEach(el => el.classList.remove('active'));
      document.querySelectorAll('.hud-tab-btn').forEach(el => el.classList.remove('active'));

      const target = document.getElementById(tabId);
      if (target) target.classList.add('active');

      const hudBtn = document.getElementById('btn-' + tabId);
      if (hudBtn) hudBtn.classList.add('active');

      if (tabId === 'tab-chain') hydrateFromREST();
      if (tabId === 'tab-orders') { loadOrders(); loadTrades(); }
      if (tabId === 'tab-overview') resizeChart();
    }

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
        // Intraday from 09:15 to 15:30 (approx 75 points)
        // Opened at 23,454.05, morning high 23,489.00, midday low 23,285.75, closed/traded around 23,329.00
        const times = ['09:15', '09:30', '09:45', '10:00', '10:30', '11:00', '11:30', '12:00', '12:30', '13:00', '13:30', '14:00', '14:30', '15:00', '15:30'];
        const values = [23454.05, 23472.10, 23489.00, 23460.50, 23420.25, 23395.10, 23360.80, 23340.20, 23315.40, 23285.75, 23310.20, 23355.60, 23340.10, 23312.30, liveSpotPrice];
        // Interpolate smooth curve
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

      // 1. Dotted Reference Line: Previous Close (Matches Screenshot)
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

      // 3. Time Axis Labels (Matches Screenshot: 11:00 am, 1:00 pm, 3:00 pm)
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

        // Pulsing circle at point
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

    let ws;
    let lastPing = Date.now();
    let fallbackPollInterval = null;

    function initWebSocket() {
      const loc = window.location;
      const wsProtocol = loc.protocol === 'https:' ? 'wss:' : 'ws:';
      const apiKey = getApiKey();
      let wsUrl = wsProtocol + '//' + loc.host + '/ws/stream';
      if (apiKey) wsUrl += '?api_key=' + encodeURIComponent(apiKey);

      try {
        ws = new WebSocket(wsUrl);
      } catch (e) {
        startFallbackPolling();
        return;
      }

      ws.onopen = () => {
        const dot = document.getElementById('live-dot');
        if (dot) dot.style.background = 'var(--gf-green)';
        const stText = document.getElementById('ws-status-text');
        if (stText) stText.innerText = 'LIVE';
        stopFallbackPolling();
      };

      ws.onmessage = (evt) => {
        const now = Date.now();
        const pingEl = document.getElementById('ws-latency');
        if (pingEl) pingEl.innerText = (now - lastPing) + ' ms';
        lastPing = now;

        try {
          const data = JSON.parse(evt.data);
          updateUI(data);
        } catch (err) {
          console.error("WS Parse error", err);
        }
      };

      ws.onclose = () => {
        const dot = document.getElementById('live-dot');
        if (dot) dot.style.background = 'var(--gf-red)';
        const stText = document.getElementById('ws-status-text');
        if (stText) stText.innerText = 'RECONNECT';
        startFallbackPolling();
        setTimeout(initWebSocket, 2000);
      };

      ws.onerror = () => startFallbackPolling();
    }

    function startFallbackPolling() {
      if (!fallbackPollInterval) fallbackPollInterval = setInterval(hydrateFromREST, 2500);
    }

    function stopFallbackPolling() {
      if (fallbackPollInterval) {
        clearInterval(fallbackPollInterval);
        fallbackPollInterval = null;
      }
    }

    async function hydrateFromREST() {
      try {
        const [statusRes, quotesRes, posRes, intelRes, ccRes, atRes] = await Promise.allSettled([
          fetch('/api/status').then(r => r.ok ? r.json() : null),
          fetch('/api/quotes').then(r => r.ok ? r.json() : null),
          fetch('/api/positions').then(r => r.ok ? r.json() : null),
          fetch('/api/intelligence/snapshot').then(r => r.ok ? r.json() : null),
          fetch('/api/learning/champion').then(r => r.ok ? r.json() : null),
          fetch('/api/auto-trade/status').then(r => r.ok ? r.json() : null),
        ]);

        const statusData = statusRes.status === 'fulfilled' && statusRes.value ? statusRes.value : {};
        const quotesData = quotesRes.status === 'fulfilled' && quotesRes.value ? quotesRes.value : {};
        const posData = posRes.status === 'fulfilled' && posRes.value ? posRes.value : [];
        const intelData = intelRes.status === 'fulfilled' && intelRes.value ? intelRes.value : null;
        const ccData = ccRes.status === 'fulfilled' && ccRes.value ? ccRes.value : null;
        const atData = atRes.status === 'fulfilled' && atRes.value ? atRes.value : null;

        updateUI({
          type: 'STREAM_UPDATE',
          is_market_open: statusData.is_market_open !== undefined ? statusData.is_market_open : true,
          market_phase: statusData.market_phase || 'MORNING_BREAKOUT',
          real_nifty_spot: statusData.real_nifty_spot || 23329.00,
          pnl: statusData.pnl ? {
            cash: statusData.capital ? statusData.capital.current_cash : 2980.72,
            total_val: statusData.capital ? statusData.capital.total_portfolio_value : 2980.72,
            fees: statusData.pnl.total_friction,
            net_pnl: statusData.pnl.net_pnl,
            net_pct: statusData.pnl.net_pnl_pct,
            drawdown_pct: statusData.pnl.drawdown_pct
          } : undefined,
          quotes: quotesData,
          positions: posData,
          auto_trade: atData,
          market_intelligence: intelData,
          champion_challenger: ccData && ccData.champion ? {
            champion_id: ccData.champion.model_id
          } : undefined
        });
      } catch (e) {
        console.warn('Hydration error:', e);
      }
    }

    function updateUI(data) {
      // 1. Spot Price & Chart update
      if (data.real_nifty_spot) {
        updateSpotHeader(data.real_nifty_spot, true);
        if (currentTimeframe === '1D' && rawChartData.length > 0) {
          rawChartData[rawChartData.length - 1].price = data.real_nifty_spot;
          renderChart();
        }
      }

      // 2. Session Banner
      const isMarketOpen = data.is_market_open;
      const banner = document.getElementById('market-status-banner');
      if (banner) {
        banner.style.display = isMarketOpen ? 'none' : 'flex';
      }

      // 3. PnL & Virtual Capital
      if (data.pnl) {
        const cashEl = document.getElementById('cash-val');
        if (cashEl) cashEl.innerText = '₹' + data.pnl.cash.toFixed(2);

        const netEl = document.getElementById('net-pnl');
        if (netEl) {
          netEl.innerText = '₹' + data.pnl.net_pnl.toFixed(2);
          netEl.style.color = data.pnl.net_pnl >= 0 ? 'var(--gf-green)' : 'var(--gf-red)';
        }

        const pctEl = document.getElementById('pnl-pct');
        if (pctEl) pctEl.innerText = data.pnl.net_pct.toFixed(2) + '% Return';

        const feeEl = document.getElementById('total-fees');
        if (feeEl) feeEl.innerText = '₹' + data.pnl.fees.toFixed(2);

        const portEl = document.getElementById('port-val');
        if (portEl) portEl.innerText = '₹' + data.pnl.total_val.toFixed(2);
      }

      // 4. ML Champion Model
      if (data.champion_challenger) {
        const champEl = document.getElementById('champion-model-text');
        if (champEl) champEl.innerText = data.champion_challenger.champion_id;
      }

      // 5. Option Chain Quotes
      if (data.quotes) {
        renderQuotes(data.quotes);
      }

      // 6. Active Auto Trade
      if (data.auto_trade) {
        const mtContainer = document.getElementById('managed-trade-container');
        if (mtContainer) {
          if (data.auto_trade.active_trades && data.auto_trade.active_trades.length > 0) {
            const t = data.auto_trade.active_trades[0];
            mtContainer.innerHTML = `<div style="font-weight:700; color:#fff;">${t.symbol} (65 Qty)</div>
              <div>Entry: ₹${t.entry_price} | LTP: ₹${t.current_price} | Stop: ₹${t.stop_price} | Target: ₹${t.target_price}</div>
              <div style="color:${t.delta_pts >= 0 ? 'var(--gf-green)' : 'var(--gf-red)'}; font-weight:700;">Move: ${t.delta_pts.toFixed(2)} pts</div>`;
          } else {
            mtContainer.innerHTML = 'Scanning orderbooks. Auto-Pilot enters single-leg breakouts when ML conviction ≥ 55% and Net P&L clears the ₹52 statutory hurdle.';
          }
        }
      }
    }

    function renderQuotes(quotesData) {
      const qList = document.getElementById('quotes-list');
      if (!qList) return;

      const items = Object.entries(quotesData).filter(([sym]) => sym !== 'NIFTY_SPOT').slice(0, 16);
      if (items.length === 0) {
        qList.innerHTML = '<div style="text-align:center; padding:15px; color:var(--gf-text-secondary);">No active quotes.</div>';
        return;
      }

      let html = '';
      for (const [sym, q] of items) {
        const ask = q.ask ?? q.best_ask ?? 0;
        const bid = q.bid ?? q.best_bid ?? 0;
        const outlay = ask * 65;
        const isSafe = ask <= 38.0;

        html += `<div class="gf-list-item">
          <div>
            <div style="font-weight:700; color:#fff; font-family:'JetBrains Mono',monospace;">${sym}</div>
            <div style="font-size:11px; color:var(--gf-text-secondary);">Bid: ₹${bid.toFixed(2)} | Ask: ₹${ask.toFixed(2)} | Outlay: ₹${Math.round(outlay)}</div>
          </div>
          <div style="display:flex; align-items:center; gap:8px;">
            <span style="font-size:10px; font-weight:700; color:${isSafe ? 'var(--gf-green)' : 'var(--gf-red)'};">${isSafe ? 'SAFE OUTLAY' : '>₹38 CAP'}</span>
            <button class="btn-buy-chip" onclick="orderOption('${sym}', 'BUY', ${ask})">BUY 65</button>
          </div>
        </div>`;
      }
      qList.innerHTML = html;
    }

    // --- Trading Controls ---
    async function engageKillSwitch() {
      if (!confirm("Engage Emergency Kill Switch?")) return;
      await fetch('/api/kill-switch', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ action: 'engage', reason: 'Operator engaged from HUD' })
      });
    }

    async function resetKillSwitch() {
      const token = prompt("Enter operator authorization reset token:");
      if (!token) return;
      const resp = await fetch('/api/kill-switch', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ action: 'reset', token: token.trim() })
      });
      if (resp.ok) alert("Kill switch reset successfully.");
      else alert("Reset rejected.");
    }

    async function resetPaperAccount() {
      if (!confirm("Reset paper account virtual balance to ₹3,000 baseline?")) return;
      await fetch('/api/paper/reset', { method: 'POST', headers: getAuthHeaders() });
      await hydrateFromREST();
    }

    async function toggleAutoPilot() {
      const resp = await fetch('/api/auto-trade/status');
      const st = await resp.json();
      await fetch('/api/auto-trade/toggle', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ enabled: !st.is_enabled })
      });
      await hydrateFromREST();
    }

    async function triggerSquareOffAll() {
      if (!confirm("Execute square-off for all open positions immediately?")) return;
      await fetch('/api/auto-trade/square-off', { method: 'POST', headers: getAuthHeaders() });
      await hydrateFromREST();
    }

    async function evaluateChallengerGate() {
      const resp = await fetch('/api/learning/evaluate-challenger', { method: 'POST', headers: getAuthHeaders() });
      const data = await resp.json();
      if (data.report && data.report.promoted) {
        alert("🎉 CHALLENGER PROMOTED TO CHAMPION!\n\nNew Model ID: " + data.report.champion.model_id);
      } else {
        alert("Challenger Evaluation: " + (data.report ? data.report.reason : "No active candidate qualified."));
      }
    }

    async function orderOption(symbol, side, price) {
      const resp = await fetch('/api/paper/order', {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ symbol, side, price, quantity: 65 })
      });
      const res = await resp.json();
      if (res.error) alert(res.error);
      else if (res.status === 'REJECTED') alert("Rejected by Risk Kernel: " + res.rejection_reason);
      else alert("Order filled: " + symbol + " @ ₹" + res.fill_price);
      await hydrateFromREST();
    }

    async function loadOrders() {
      const resp = await fetch('/api/orders');
      const orders = await resp.json();
      const oList = document.getElementById('orders-list');
      if (oList && orders) {
        let html = '';
        orders.slice(0, 10).forEach(o => {
          html += `<div class="gf-list-item">
            <div>
              <div style="font-weight:700; color:#fff;">${o.side} ${o.quantity}x ${o.symbol}</div>
              <div style="font-size:11px; color:var(--gf-text-secondary);">Status: ${o.status} | Price: ₹${o.fill_price || o.requested_price}</div>
            </div>
            <div style="font-size:11px; color:var(--gf-red);">Fees: ₹${o.total_costs.toFixed(2)}</div>
          </div>`;
        });
        oList.innerHTML = html || '<div style="text-align:center; padding:15px; color:var(--gf-text-secondary);">No orders recorded.</div>';
      }
    }

    async function loadTrades() {
      const resp = await fetch('/api/trades');
      const trades = await resp.json();
      const tList = document.getElementById('trades-list');
      if (tList && trades) {
        let html = '';
        trades.slice(0, 10).forEach(t => {
          html += `<div class="gf-list-item">
            <div>
              <div style="font-weight:700; color:#fff;">${t.side} ${t.quantity}x ${t.symbol}</div>
              <div style="font-size:11px; color:var(--gf-text-secondary);">Fill: ₹${t.price.toFixed(2)} | Turnover: ₹${t.turnover.toFixed(2)}</div>
            </div>
            <div style="font-size:11px; color:var(--gf-red);">Friction: ₹${t.total_costs.toFixed(2)}</div>
          </div>`;
        });
        tList.innerHTML = html || '<div style="text-align:center; padding:15px; color:var(--gf-text-secondary);">No trades executed.</div>';
      }
    }

    async function calculateGreeksUI() {
      const spot = parseFloat(document.getElementById('bs-spot')?.value) || 23329;
      const strike = parseFloat(document.getElementById('bs-strike')?.value) || 23350;
      const days = parseFloat(document.getElementById('bs-days')?.value) || 4;
      const optType = document.getElementById('bs-type')?.value || 'CE';
      const res = await fetch('/api/greeks/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ spot, strike, days_to_expiry: days, iv: 0.145, option_type: optType })
      });
      const data = await res.json();
      const box = document.getElementById('greeks-result-box');
      if (box && data.greeks) {
        const g = data.greeks;
        box.innerHTML = `<div style="padding:10px; background:#303134; border-radius:8px;">
          <div>Price: ₹${g.theoretical_price.toFixed(2)} | Outlay: ₹${Math.round(g.theoretical_price*65)}</div>
          <div>Delta: ${g.delta.toFixed(4)} | Gamma: ${g.gamma.toFixed(5)}</div>
          <div>Theta: ${g.theta.toFixed(2)} pts/day | Vega: ${g.vega.toFixed(2)}</div>
        </div>`;
      }
    }

    // Init on DOMContentLoaded
    window.addEventListener('DOMContentLoaded', () => {
      initFinanceChart();
      hydrateFromREST();
      initWebSocket();
    });
  </script>
</body>
</html>
'''

with open("/root/nifty-options-arbitrage/dashboard/index.html", "w", encoding="utf-8") as f:
    f.write(html_content)

print("SUCCESS: Google Finance aesthetic dashboard built.")

import os

html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <title>CODEQUERY SerQ — NIFTY Options Algo & Research HUD</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg-space: #06090e;
      --bg-stage: radial-gradient(circle at 65% 35%, rgba(0, 230, 118, 0.10) 0%, rgba(6, 9, 14, 0) 65%), #06090e;
      --bg-card: rgba(12, 17, 25, 0.92);
      --bg-card-inner: #090e15;
      --emerald: #00e676;
      --emerald-dark: #00b050;
      --emerald-dim: rgba(0, 230, 118, 0.12);
      --emerald-border: rgba(0, 230, 118, 0.32);
      --emerald-glow: rgba(0, 230, 118, 0.45);
      --text-white: #ffffff;
      --text-soft: #cbd5e1;
      --text-muted: #64748b;
      --card-border: #182232;
      --accent-red: #ff3366;
      --accent-amber: #ffb300;
    }

    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
      -webkit-tap-highlight-color: transparent;
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    body {
      background: var(--bg-stage);
      color: var(--text-white);
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
      position: relative;
    }

    .ambient-glow-mesh {
      position: fixed;
      top: 0;
      left: 0;
      width: 100vw;
      height: 100vh;
      pointer-events: none;
      z-index: 0;
      background: 
        radial-gradient(circle at 75% 35%, rgba(0, 230, 118, 0.09) 0%, transparent 50%),
        radial-gradient(circle at 20% 80%, rgba(0, 230, 118, 0.04) 0%, transparent 60%);
    }

    /* Top Navigation Header */
    .app-topbar {
      padding: 16px 28px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      position: sticky;
      top: 0;
      z-index: 100;
      background: rgba(6, 9, 14, 0.88);
      backdrop-filter: blur(20px);
      -webkit-backdrop-filter: blur(20px);
      border-bottom: 1px solid rgba(24, 34, 50, 0.7);
    }

    .brand-group {
      display: flex;
      align-items: center;
      gap: 14px;
      text-decoration: none;
    }

    .brand-back-btn {
      color: #cbd5e1;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: transform 0.2s ease;
    }
    .brand-back-btn:hover {
      transform: translateX(-2px);
      color: #fff;
    }

    .brand-hex-logo {
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .brand-text-col {
      display: flex;
      flex-direction: column;
      line-height: 1.1;
    }

    .brand-company {
      font-size: 10px;
      font-weight: 800;
      color: #64748b;
      letter-spacing: 1.5px;
      text-transform: uppercase;
    }

    .brand-name {
      font-size: 20px;
      font-weight: 800;
      letter-spacing: -0.5px;
      color: #ffffff;
    }

    .brand-name span {
      color: var(--emerald);
    }

    .topbar-right {
      display: flex;
      align-items: center;
      gap: 14px;
    }

    .ws-pill {
      display: flex;
      align-items: center;
      gap: 8px;
      background: rgba(0, 230, 118, 0.10);
      border: 1px solid var(--emerald-border);
      padding: 5px 12px;
      border-radius: 20px;
      font-size: 11px;
      font-weight: 700;
      color: var(--emerald);
    }

    .ws-dot {
      width: 7px;
      height: 7px;
      border-radius: 50%;
      background: var(--emerald);
      box-shadow: 0 0 10px var(--emerald);
      animation: pulseDot 2s infinite ease-in-out;
    }

    @keyframes pulseDot {
      0%, 100% { opacity: 0.3; transform: scale(0.9); }
      50% { opacity: 1; transform: scale(1.1); }
    }

    .btn-kill-hdr {
      background: rgba(255, 51, 102, 0.12);
      color: var(--accent-red);
      border: 1px solid rgba(255, 51, 102, 0.4);
      padding: 5px 12px;
      border-radius: 8px;
      font-size: 11px;
      font-weight: 800;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-kill-hdr:hover {
      background: var(--accent-red);
      color: #fff;
    }

    /* Mobile Responsive Viewport Switcher */
    .mobile-tab-pills {
      display: none;
      gap: 8px;
      padding: 12px 16px;
      overflow-x: auto;
      z-index: 10;
    }
    @media (max-width: 1024px) {
      .mobile-tab-pills {
        display: flex;
      }
    }
    .pill-tab {
      padding: 8px 16px;
      border-radius: 24px;
      background: #0b1017;
      color: var(--text-muted);
      border: 1px solid var(--card-border);
      font-size: 12px;
      font-weight: 700;
      white-space: nowrap;
      cursor: pointer;
      transition: all 0.2s;
    }
    .pill-tab.active {
      background: rgba(0, 230, 118, 0.14);
      color: var(--emerald);
      border-color: var(--emerald);
      box-shadow: 0 0 14px rgba(0, 230, 118, 0.25);
    }

    /* Main Showcase Container */
    .showcase-stage {
      position: relative;
      z-index: 1;
      max-width: 1320px;
      width: 100%;
      margin: 0 auto;
      padding: 40px 32px 60px;
      display: grid;
      grid-template-columns: 360px 1fr;
      gap: 50px;
      align-items: start;
    }

    @media (max-width: 1024px) {
      .showcase-stage {
        grid-template-columns: 1fr;
        padding: 20px 16px;
        gap: 28px;
      }
    }

    /* Left Rail: Progressive Stepper */
    .stepper-rail-col {
      display: flex;
      flex-direction: column;
    }

    .hero-heading-wrap {
      margin-bottom: 36px;
    }

    .hero-heading {
      font-size: 42px;
      font-weight: 800;
      line-height: 1.1;
      letter-spacing: -1px;
      color: #ffffff;
      margin-bottom: 12px;
    }

    .hero-heading .emerald-word {
      color: var(--emerald);
      text-shadow: 0 0 30px rgba(0, 230, 118, 0.4);
    }

    .hero-subtext {
      font-size: 15px;
      color: #718096;
      line-height: 1.5;
      max-width: 320px;
    }

    /* Vertical Timeline Rail */
    .timeline-container {
      position: relative;
      display: flex;
      flex-direction: column;
      gap: 32px;
      padding-left: 6px;
      margin-bottom: 40px;
    }

    .timeline-track-line {
      position: absolute;
      left: 25px;
      top: 24px;
      bottom: 24px;
      width: 2px;
      background: repeating-linear-gradient(
        to bottom,
        rgba(0, 230, 118, 0.4) 0,
        rgba(0, 230, 118, 0.4) 4px,
        transparent 4px,
        transparent 8px
      );
      z-index: 1;
    }

    .timeline-step-row {
      display: flex;
      align-items: center;
      gap: 16px;
      position: relative;
      z-index: 2;
      cursor: pointer;
      padding: 6px 12px;
      border-radius: 14px;
      transition: all 0.25s ease;
    }
    .timeline-step-row:hover {
      background: rgba(255, 255, 255, 0.03);
    }
    .timeline-step-row.active {
      background: rgba(0, 230, 118, 0.06);
    }

    .step-circle-icon {
      width: 40px;
      height: 40px;
      border-radius: 50%;
      background: #080d14;
      border: 1.5px solid rgba(255, 255, 255, 0.25);
      display: flex;
      align-items: center;
      justify-content: center;
      color: #a0aec0;
      flex-shrink: 0;
      transition: all 0.25s;
    }

    .timeline-step-row.active .step-circle-icon {
      border-color: var(--emerald);
      color: var(--emerald);
      box-shadow: 0 0 16px rgba(0, 230, 118, 0.5);
      background: rgba(0, 230, 118, 0.12);
    }

    .step-meta-col {
      display: flex;
      flex-direction: column;
      line-height: 1.25;
    }

    .step-idx-num {
      font-size: 13px;
      font-weight: 800;
      color: var(--emerald);
      margin-bottom: 2px;
    }

    .step-label-title {
      font-size: 15px;
      font-weight: 700;
      color: #ffffff;
    }

    .step-label-desc {
      font-size: 12px;
      color: #64748b;
      margin-top: 2px;
    }

    /* Bottom Left Brand Pill & Hardware Puck */
    .technician-brand-pill {
      display: flex;
      align-items: center;
      gap: 12px;
      border-left: 2px solid var(--emerald);
      padding-left: 12px;
      margin-top: 10px;
      margin-bottom: 24px;
    }

    .tech-text-title {
      font-size: 12px;
      font-weight: 700;
      color: #94a3b8;
    }

    .tech-text-sub {
      font-size: 12px;
      font-weight: 600;
      color: #475569;
    }

    /* 3D Hardware Sensor Puck from Screenshot */
    .hardware-puck-preview {
      width: 80px;
      height: 70px;
      background: linear-gradient(135deg, #131b26 0%, #080d14 100%);
      border-radius: 20px;
      border: 1.5px solid #233044;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 
        0 15px 30px rgba(0, 0, 0, 0.8),
        0 0 25px rgba(0, 230, 118, 0.15),
        inset 0 1px 2px rgba(255, 255, 255, 0.15);
      position: relative;
    }

    .puck-inner-logo {
      width: 28px;
      height: 28px;
      color: var(--emerald);
      filter: drop-shadow(0 0 6px var(--emerald));
    }

    /* Live Mini Telemetry Card */
    .mini-pnl-card {
      background: #090e16;
      border: 1px solid var(--card-border);
      border-radius: 16px;
      padding: 16px;
      margin-top: 24px;
    }

    .mini-pnl-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: 10px;
    }

    .mini-metric-pill {
      background: #0d1420;
      border: 1px solid #1a2536;
      border-radius: 10px;
      padding: 8px 12px;
    }

    .mini-metric-label {
      font-size: 9px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
    }

    .mini-metric-num {
      font-size: 15px;
      font-weight: 800;
      font-family: 'JetBrains Mono', monospace;
      margin-top: 2px;
    }

    /* Right Column: 3D Cascading Smartphone Deck */
    .cascade-stage-wrap {
      position: relative;
      width: 100%;
      min-height: 820px;
    }

    @media (max-width: 1024px) {
      .cascade-stage-wrap {
        min-height: auto;
      }
    }

    .phone-mockup {
      background: var(--bg-card);
      border: 1px solid var(--emerald-border);
      border-radius: 34px;
      padding: 20px 22px 26px;
      backdrop-filter: blur(25px);
      -webkit-backdrop-filter: blur(25px);
      box-shadow: 
        0 25px 60px rgba(0, 0, 0, 0.9),
        0 0 35px rgba(0, 230, 118, 0.10);
      position: relative;
      transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
    }

    @media (min-width: 1025px) {
      .cascade-stage-wrap {
        perspective: 1200px;
      }

      .phone-mockup {
        position: absolute;
        width: 380px;
        cursor: pointer;
      }

      #phone-card-1 {
        top: 0px;
        left: 20px;
        z-index: 10;
        opacity: 0.88;
        transform: scale(0.92) translateZ(-40px);
        filter: brightness(0.85);
      }

      #phone-card-2 {
        top: 65px;
        left: 175px;
        z-index: 20;
        opacity: 0.94;
        transform: scale(0.96) translateZ(-20px);
        filter: brightness(0.92);
      }

      #phone-card-3 {
        top: 130px;
        left: 330px;
        z-index: 30;
        opacity: 1;
        transform: scale(1) translateZ(0);
        box-shadow: 
          -30px 30px 90px rgba(0, 230, 118, 0.40),
          0 30px 70px rgba(0, 0, 0, 0.95),
          inset 0 0 20px rgba(0, 230, 118, 0.08);
      }

      .cascade-stage-wrap.focus-1 #phone-card-1 {
        z-index: 50;
        opacity: 1;
        filter: brightness(1);
        transform: scale(1.02) translateZ(50px);
        box-shadow: 0 0 60px rgba(0, 230, 118, 0.4), 0 30px 70px rgba(0, 0, 0, 0.95);
      }
      .cascade-stage-wrap.focus-1 #phone-card-2 {
        transform: scale(0.92) translateZ(-30px);
        opacity: 0.75;
      }
      .cascade-stage-wrap.focus-1 #phone-card-3 {
        transform: scale(0.88) translateZ(-60px);
        opacity: 0.65;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8);
      }

      .cascade-stage-wrap.focus-2 #phone-card-2 {
        z-index: 50;
        opacity: 1;
        filter: brightness(1);
        transform: scale(1.02) translateZ(50px);
        box-shadow: 0 0 60px rgba(0, 230, 118, 0.4), 0 30px 70px rgba(0, 0, 0, 0.95);
      }
      .cascade-stage-wrap.focus-2 #phone-card-1 {
        transform: scale(0.88) translateZ(-60px);
        opacity: 0.65;
      }
      .cascade-stage-wrap.focus-2 #phone-card-3 {
        transform: scale(0.92) translateZ(-30px);
        opacity: 0.75;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.8);
      }

      .cascade-stage-wrap.focus-3 #phone-card-3 {
        z-index: 50;
        opacity: 1;
        filter: brightness(1);
        transform: scale(1.02) translateZ(50px);
        box-shadow: 
          -35px 35px 100px rgba(0, 230, 118, 0.48),
          0 30px 70px rgba(0, 0, 0, 0.95),
          inset 0 0 20px rgba(0, 230, 118, 0.08);
      }
      .cascade-stage-wrap.focus-3 #phone-card-1 {
        transform: scale(0.92) translateZ(-40px);
        opacity: 0.85;
      }
      .cascade-stage-wrap.focus-3 #phone-card-2 {
        transform: scale(0.96) translateZ(-20px);
        opacity: 0.92;
      }
    }

    @media (max-width: 1024px) {
      .phone-mockup {
        display: none;
        width: 100%;
        max-width: 440px;
        margin: 0 auto;
      }
      .phone-mockup.active-mobile {
        display: block;
        animation: mobileCardFade 0.3s ease-out;
      }
    }

    @keyframes mobileCardFade {
      from { opacity: 0; transform: translateY(10px); }
      to { opacity: 1; transform: translateY(0); }
    }

    .mockup-statusbar {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 11px;
      font-weight: 700;
      color: var(--text-muted);
      margin-bottom: 16px;
      padding: 0 4px;
    }

    .statusbar-meta-icons {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .mockup-app-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }

    .app-header-btn {
      background: none;
      border: none;
      color: #cbd5e1;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 15px;
    }

    .app-header-title {
      font-size: 14px;
      font-weight: 700;
      color: var(--text-soft);
    }

    .hero-squircle-group {
      display: flex;
      gap: 16px;
      align-items: center;
      margin-bottom: 18px;
    }

    .squircle-badge {
      width: 50px;
      height: 50px;
      border-radius: 16px;
      background: rgba(0, 230, 118, 0.12);
      border: 1.5px solid var(--emerald-border);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--emerald);
      box-shadow: 0 0 20px rgba(0, 230, 118, 0.25);
      flex-shrink: 0;
    }

    .squircle-texts h2 {
      font-size: 20px;
      font-weight: 800;
      color: #ffffff;
      line-height: 1.2;
    }

    .squircle-texts p {
      font-size: 12px;
      color: var(--text-muted);
      margin-top: 3px;
    }

    .squircle-tag {
      font-size: 10px;
      font-weight: 800;
      color: var(--emerald);
      letter-spacing: 0.5px;
      margin-bottom: 2px;
    }

    .progress-section {
      margin-bottom: 16px;
    }

    .progress-labels-row {
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      font-weight: 600;
      color: var(--text-muted);
      margin-bottom: 6px;
    }

    .progress-track-bg {
      height: 4px;
      background: #141c28;
      border-radius: 2px;
      overflow: hidden;
    }

    .progress-fill-emerald {
      height: 100%;
      background: var(--emerald);
      box-shadow: 0 0 12px var(--emerald);
      transition: width 0.4s ease;
    }

    .checklist-rows-wrap {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 18px;
    }

    .chk-item-card {
      background: #090e15;
      border: 1px solid var(--card-border);
      border-radius: 12px;
      padding: 10px 14px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      transition: border-color 0.2s;
    }
    .chk-item-card:hover {
      border-color: rgba(0, 230, 118, 0.35);
    }

    .chk-left-info {
      display: flex;
      flex-direction: column;
    }

    .chk-main-title {
      font-size: 13px;
      font-weight: 700;
      color: #f1f5f9;
    }

    .chk-state-text {
      font-size: 10px;
      color: var(--text-muted);
      margin-top: 2px;
    }

    .status-glyph {
      width: 20px;
      height: 20px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .status-glyph.completed {
      background: var(--emerald);
      color: #06090e;
      font-size: 11px;
      font-weight: 900;
    }

    .status-glyph.in-progress {
      border: 2px solid var(--emerald);
      box-shadow: 0 0 10px var(--emerald);
      animation: spinGlyph 2.5s linear infinite;
    }

    .status-glyph.pending {
      border: 2px solid #233044;
    }

    @keyframes spinGlyph {
      0% { transform: rotate(0deg); }
      100% { transform: rotate(360deg); }
    }

    .trade-active-panel {
      background: #0d1522;
      border: 1px solid var(--emerald-border);
      border-radius: 14px;
      padding: 12px 14px;
      margin-bottom: 16px;
    }

    .trade-panel-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }

    .trade-panel-title {
      font-size: 13px;
      font-weight: 800;
      color: #ffffff;
    }

    .trade-panel-badge {
      font-size: 9px;
      font-weight: 800;
      padding: 2px 8px;
      border-radius: 4px;
      background: rgba(0, 230, 118, 0.15);
      color: var(--emerald);
      border: 1px solid var(--emerald);
    }

    .trade-stats-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 6px;
      font-size: 10px;
      font-family: 'JetBrains Mono', monospace;
      margin-bottom: 8px;
    }

    .btn-complete-emerald {
      background: linear-gradient(135deg, #00e676 0%, #00b050 100%);
      color: #050d08;
      font-weight: 800;
      font-size: 14px;
      border: none;
      border-radius: 14px;
      padding: 14px 20px;
      width: 100%;
      display: flex;
      justify-content: space-between;
      align-items: center;
      cursor: pointer;
      box-shadow: 0 4px 25px rgba(0, 230, 118, 0.45);
      transition: all 0.2s;
    }
    .btn-complete-emerald:hover {
      transform: translateY(-1px);
      box-shadow: 0 6px 32px rgba(0, 230, 118, 0.65);
    }
    .btn-complete-emerald:active {
      transform: translateY(1px);
    }

    .btn-add-note-glass {
      background: rgba(14, 21, 31, 0.7);
      color: #cbd5e1;
      font-weight: 700;
      font-size: 13px;
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 12px 20px;
      width: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 8px;
      margin-top: 10px;
      cursor: pointer;
      transition: all 0.2s;
    }
    .btn-add-note-glass:hover {
      background: #151f2e;
      color: #ffffff;
      border-color: rgba(255, 255, 255, 0.2);
    }

    .floating-refresh-btn {
      position: fixed;
      bottom: 24px;
      right: 24px;
      width: 48px;
      height: 48px;
      border-radius: 50%;
      background: rgba(13, 19, 28, 0.85);
      border: 1px solid rgba(255, 255, 255, 0.15);
      color: #ffffff;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.8);
      z-index: 99;
      transition: all 0.2s;
      backdrop-filter: blur(12px);
    }
    .floating-refresh-btn:hover {
      border-color: var(--emerald);
      color: var(--emerald);
      transform: rotate(45deg);
    }

    .tactical-map-viewport {
      height: 145px;
      background: #080d15;
      border: 1px solid var(--card-border);
      border-radius: 14px;
      position: relative;
      overflow: hidden;
      margin-bottom: 14px;
    }
    .route-canvas-el {
      width: 100%;
      height: 100%;
      display: block;
    }
    .map-badge-pin {
      position: absolute;
      bottom: 10px;
      left: 10px;
      background: rgba(6, 9, 14, 0.85);
      border: 1px solid var(--emerald-border);
      padding: 3px 8px;
      border-radius: 6px;
      font-size: 10px;
      color: var(--emerald);
      font-weight: 700;
    }

    .eta-dist-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-bottom: 14px;
    }

    .eta-pill-box {
      background: #090e15;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 8px 12px;
    }

    .eta-lbl {
      font-size: 9px;
      font-weight: 700;
      color: var(--text-muted);
      text-transform: uppercase;
    }

    .eta-val {
      font-size: 15px;
      font-weight: 800;
      color: #fff;
      font-family: 'JetBrains Mono', monospace;
      margin-top: 2px;
    }

    .quotes-scroll-area {
      max-height: 180px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 6px;
      margin-bottom: 14px;
    }

    .quote-item-row {
      background: #090e15;
      border: 1px solid #16202e;
      border-radius: 8px;
      padding: 8px 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .btn-quick-buy {
      padding: 4px 10px;
      background: rgba(0, 230, 118, 0.14);
      border: 1px solid var(--emerald);
      color: var(--emerald);
      border-radius: 6px;
      font-size: 10px;
      font-weight: 800;
      cursor: pointer;
    }

    .macro-quad-box {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 14px;
    }

    .macro-data-cell {
      background: #090e15;
      border: 1px solid var(--card-border);
      border-radius: 10px;
      padding: 10px;
    }

    .macro-val-mono {
      font-size: 15px;
      font-weight: 800;
      font-family: 'JetBrains Mono', monospace;
      margin-top: 2px;
    }
  </style>
</head>
<body>

  <div class="ambient-glow-mesh"></div>

  <!-- Top Navigation Bar -->
  <header class="app-topbar">
    <div class="brand-group">
      <div class="brand-back-btn" onclick="selectStep(1)" title="Go to Step 1">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
      </div>
      <div class="brand-hex-logo">
        <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--emerald)" stroke-width="2">
          <polygon points="12 2 21 7 21 17 12 22 3 17 3 7 12 2"></polygon>
          <circle cx="12" cy="12" r="3" fill="var(--emerald)"></circle>
        </svg>
      </div>
      <div class="brand-text-col">
        <span class="brand-company">CODEQUERY</span>
        <span class="brand-name">Ser<span>Q</span></span>
      </div>
    </div>

    <div class="topbar-right">
      <div class="ws-pill">
        <div class="ws-dot"></div>
        <span id="top-ws-ping">24 ms</span>
      </div>
      <button class="btn-kill-hdr" onclick="engageKillSwitch()">
        🛑 Emergency Kill
      </button>
    </div>
  </header>

  <!-- Mobile Step Tab Switcher -->
  <nav class="mobile-tab-pills">
    <button class="pill-tab" onclick="selectStep(1)" id="mtab-1">1. Job Assigned</button>
    <button class="pill-tab" onclick="selectStep(2)" id="mtab-2">2. Navigation Details</button>
    <button class="pill-tab active" onclick="selectStep(3)" id="mtab-3">3. Service Checklist</button>
  </nav>

  <!-- Main Showcase Grid -->
  <main class="showcase-stage">

    <!-- Left Rail: Progressive Disclosure Stepper -->
    <aside class="stepper-rail-col">
      <div class="hero-heading-wrap">
        <h1 class="hero-heading">
          Field Service.<br>
          <span class="emerald-word">Simplified.</span>
        </h1>
        <p class="hero-subtext">
          Progressive disclosure in action—one step at a time.
        </p>
      </div>

      <!-- Vertical Timeline Rail -->
      <div class="timeline-container">
        <div class="timeline-track-line"></div>

        <!-- Step 1 -->
        <div class="timeline-step-row" id="rail-step-1" onclick="selectStep(1)">
          <div class="step-circle-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
              <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
            </svg>
          </div>
          <div class="step-meta-col">
            <span class="step-idx-num">1</span>
            <span class="step-label-title">Job Assigned</span>
            <span class="step-label-desc">Global Macro Posture & Oil</span>
          </div>
        </div>

        <!-- Step 2 -->
        <div class="timeline-step-row" id="rail-step-2" onclick="selectStep(2)">
          <div class="step-circle-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="3 11 22 2 13 21 11 13 3 11"></polygon>
            </svg>
          </div>
          <div class="step-meta-col">
            <span class="step-idx-num">2</span>
            <span class="step-label-title">Navigation Details</span>
            <span class="step-label-desc">Route & Orderbook Depth</span>
          </div>
        </div>

        <!-- Step 3 (Active) -->
        <div class="timeline-step-row active" id="rail-step-3" onclick="selectStep(3)">
          <div class="step-circle-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 11l3 3L22 4"></path>
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
            </svg>
          </div>
          <div class="step-meta-col">
            <span class="step-idx-num">3</span>
            <span class="step-label-title">Service Checklist</span>
            <span class="step-label-desc">Execution & Trailing Ratchet</span>
          </div>
        </div>
      </div>

      <!-- Technician Credit & Hardware Puck from Screenshot -->
      <div class="technician-brand-pill">
        <div>
          <div class="tech-text-title">Built for Technicians.</div>
          <div class="tech-text-sub">Backed by CodeQuery.</div>
        </div>
      </div>

      <!-- Glowing Hardware Sensor Puck from Screenshot -->
      <div class="hardware-puck-preview" title="SerQ Telemetry Node">
        <svg class="puck-inner-logo" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polygon points="12 2 21 7 21 17 12 22 3 17 3 7 12 2"></polygon>
          <circle cx="12" cy="12" r="2.5" fill="currentColor"></circle>
        </svg>
      </div>

      <!-- Mini Live Financial Telemetry -->
      <div class="mini-pnl-card">
        <div style="font-size: 10px; font-weight: 800; color: #64748b; text-transform: uppercase;">
          Live Account Telemetry
        </div>
        <div class="mini-pnl-grid">
          <div class="mini-metric-pill">
            <div class="mini-metric-label">VIRTUAL CAPITAL</div>
            <div class="mini-metric-num" id="live-cash-disp" style="color: var(--emerald);">₹3,000.00</div>
          </div>
          <div class="mini-metric-pill">
            <div class="mini-metric-label">NET REALIZED</div>
            <div class="mini-metric-num" id="live-pnl-disp">₹0.00</div>
          </div>
        </div>
        <div style="margin-top: 10px; font-size: 11px; color: #64748b; display: flex; justify-content: space-between;">
          <span>Friction: <strong id="live-fees-disp" style="color: #fda4af;">₹0.00</strong></span>
          <span id="live-time-disp" style="font-family: monospace;">15:15 IST</span>
        </div>
      </div>
    </aside>

    <!-- Right Stage: 3D Cascading Smartphone Mockups -->
    <section class="cascade-stage-wrap focus-3" id="cascadeDeck">

      <!-- ============================================== -->
      <!-- CARD 1: JOB ASSIGNED (UPPER-LEFT BACK PHONE)   -->
      <!-- ============================================== -->
      <div class="phone-mockup" id="phone-card-1" onclick="selectStep(1)">
        <!-- Statusbar -->
        <div class="mockup-statusbar">
          <span>9:41</span>
          <div class="statusbar-meta-icons">
            <span>●●●</span>
            <span>5G</span>
            <span>100%</span>
          </div>
        </div>

        <!-- In-app Header -->
        <div class="mockup-app-header">
          <button class="app-header-btn">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
          </button>
          <span class="app-header-title">My Jobs</span>
          <button class="app-header-btn">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
          </button>
        </div>

        <!-- Squircle Header (New Assignment) -->
        <div class="hero-squircle-group">
          <div class="squircle-badge">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="7" width="20" height="14" rx="2" ry="2"></rect>
              <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"></path>
            </svg>
          </div>
          <div class="squircle-texts">
            <div class="squircle-tag">[New Assignment]</div>
            <h2>Assigned</h2>
            <p id="c1-synthesis">Hydraulic Pump Inspection & Repair</p>
          </div>
        </div>

        <!-- Meta Bar -->
        <div style="display: flex; justify-content: space-between; align-items: center; background: #080d14; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--card-border); margin-bottom: 12px; font-size: 11px;">
          <div><span style="color: var(--text-muted);">Job ID:</span> <strong>#CQ-7843</strong></div>
          <div><span style="color: var(--text-muted);">Priority:</span> <span style="color: var(--accent-red); font-weight: 800;">● High</span></div>
          <div><span style="color: var(--text-muted);">Lot:</span> <strong>65 Units</strong></div>
        </div>

        <!-- Macro Metrics Quad Grid -->
        <div class="macro-quad-box">
          <div class="macro-data-cell">
            <div style="font-size: 9px; color: var(--text-muted); font-weight: 700;">BRENT CRUDE</div>
            <div class="macro-val-mono" id="c1-brent">$103.55</div>
            <div style="font-size: 9px; color: var(--accent-red);" id="c1-brent-chg">-3.7%</div>
          </div>
          <div class="macro-data-cell">
            <div style="font-size: 9px; color: var(--text-muted); font-weight: 700;">DOLLAR INDEX (DXY)</div>
            <div class="macro-val-mono" id="c1-dxy">99.16</div>
            <div style="font-size: 9px; color: var(--text-muted);">Index Level</div>
          </div>
          <div class="macro-data-cell">
            <div style="font-size: 9px; color: var(--text-muted); font-weight: 700;">EST. OPEN GAP</div>
            <div class="macro-val-mono" id="c1-gap" style="color: var(--emerald);">+76.8</div>
            <div style="font-size: 9px; color: var(--text-muted);">GIFT NIFTY Pts</div>
          </div>
          <div class="macro-data-cell">
            <div style="font-size: 9px; color: var(--text-muted); font-weight: 700;">GEOPOLITICAL FEAR</div>
            <div class="macro-val-mono" id="c1-fear" style="color: var(--accent-amber);">0.30</div>
            <div style="font-size: 9px; color: var(--text-muted);">Normal / Moderate</div>
          </div>
        </div>

        <!-- Scenario Controls -->
        <div style="display: flex; gap: 8px; margin-bottom: 14px;">
          <select id="macro-scenario-select" onchange="onScenarioSelect(this.value)" style="flex: 2; background: #0e1520; color: #fff; border: 1px solid var(--card-border); padding: 8px 10px; border-radius: 10px; font-size: 11px;">
            <option value="NEUTRAL">🌐 Neutral Baseline</option>
            <option value="MIDDLE_EAST_WAR_CRISIS">💥 Middle East Shock</option>
            <option value="GLOBAL_DEESCALATION_RELIEF">🕊️ Peace Relief Rally</option>
            <option value="US_FED_HAWKISH_SURPRISE">🦅 Fed Hawkish Shock</option>
          </select>
          <button onclick="triggerMacroPoll()" style="flex: 1; padding: 8px; background: rgba(0, 230, 118, 0.15); border: 1px solid var(--emerald); color: var(--emerald); border-radius: 10px; font-size: 11px; font-weight: 700; cursor: pointer;">
            🔄 Poll
          </button>
        </div>

        <button class="btn-complete-emerald" onclick="event.stopPropagation(); selectStep(2)">
          <span>Proceed to Navigation</span>
          <span>→</span>
        </button>
      </div>


      <!-- ============================================== -->
      <!-- CARD 2: NAVIGATION DETAILS (MIDDLE PHONE)      -->
      <!-- ============================================== -->
      <div class="phone-mockup" id="phone-card-2" onclick="selectStep(2)">
        <!-- Statusbar -->
        <div class="mockup-statusbar">
          <span>9:41</span>
          <div class="statusbar-meta-icons">
            <span>●●●</span>
            <span>5G</span>
            <span>100%</span>
          </div>
        </div>

        <!-- In-app Header -->
        <div class="mockup-app-header">
          <button class="app-header-btn" onclick="event.stopPropagation(); selectStep(1)">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"></polyline></svg>
          </button>
          <span class="app-header-title">Job Details</span>
          <span style="font-size: 10px; color: var(--emerald); font-weight: 700;">Live Route</span>
        </div>

        <!-- Squircle Header -->
        <div class="hero-squircle-group">
          <div class="squircle-badge">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="3 11 22 2 13 21 11 13 3 11"></polygon>
            </svg>
          </div>
          <div class="squircle-texts">
            <h2>Navigation Details</h2>
            <p>Acme Industries Ltd. • 128 Industrial Way</p>
          </div>
        </div>

        <!-- ETA & Distance Pills from Screenshot -->
        <div class="eta-dist-grid">
          <div class="eta-pill-box">
            <div class="eta-lbl">ETA</div>
            <div class="eta-val" id="c2-eta">24 min</div>
          </div>
          <div class="eta-pill-box">
            <div class="eta-lbl">DISTANCE</div>
            <div class="eta-val" id="c2-spot" style="color: var(--emerald);">11.3 mi</div>
          </div>
        </div>

        <!-- Tactical Dark Route Map Canvas with Glowing Emerald Polyline -->
        <div class="tactical-map-viewport">
          <canvas id="routeCanvas" class="route-canvas-el" width="400" height="145"></canvas>
          <div class="map-badge-pin">● Route Waypoint: NIFTY 24600 CE</div>
        </div>

        <!-- Strike Quotes Depth List -->
        <div style="font-size: 11px; font-weight: 700; color: var(--text-muted); margin-bottom: 6px;">
          ORDERBOOK DEPTH (MAX OUTLAY ≤ ₹2,470)
        </div>
        <div class="quotes-scroll-area" id="c2-quotes-list">
          <!-- Dynamically populated -->
        </div>

        <button class="btn-complete-emerald" onclick="event.stopPropagation(); selectStep(3)">
          <span>Proceed to Checklist</span>
          <span>→</span>
        </button>
      </div>


      <!-- ============================================== -->
      <!-- CARD 3: SERVICE CHECKLIST (HERO FOREGROUND)   -->
      <!-- ============================================== -->
      <div class="phone-mockup active-mobile" id="phone-card-3" onclick="selectStep(3)">
        <!-- Statusbar -->
        <div class="mockup-statusbar">
          <span>9:41</span>
          <div class="statusbar-meta-icons">
            <span>●●●</span>
            <span>5G</span>
            <span>100%</span>
          </div>
        </div>

        <!-- In-app Header -->
        <div class="mockup-app-header">
          <button class="app-header-btn" onclick="event.stopPropagation(); selectStep(2)">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"></polyline></svg>
          </button>
          <span class="app-header-title">Service Checklist</span>
          <span id="auto-status-pill" style="font-size: 10px; color: var(--emerald); font-weight: 800; background: rgba(0, 230, 118, 0.15); padding: 2px 7px; border-radius: 4px; border: 1px solid var(--emerald);">AUTO ON</span>
        </div>

        <!-- Squircle Header from Screenshot -->
        <div class="hero-squircle-group">
          <div class="squircle-badge">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 11l3 3L22 4"></path>
              <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
            </svg>
          </div>
          <div class="squircle-texts">
            <h2>Service Checklist</h2>
            <p>Hydraulic Pump Inspection & Repair</p>
          </div>
        </div>

        <!-- Progress Bar from Screenshot -->
        <div class="progress-section">
          <div class="progress-labels-row">
            <span>Hydraulic Pump Inspection & Repair</span>
            <span id="c3-progress-count" style="color: #e2e8f0; font-weight: 700;">3 of 6 completed</span>
          </div>
          <div class="progress-track-bg">
            <div class="progress-fill-emerald" id="c3-progress-fill" style="width: 50%;"></div>
          </div>
        </div>

        <!-- 6 Checklist Items Matching Screenshot Exactly -->
        <div class="checklist-rows-wrap">
          <!-- 1. Safety Inspection -->
          <div class="chk-item-card">
            <div class="chk-left-info">
              <span class="chk-main-title">1. Safety Inspection</span>
              <span class="chk-state-text" id="chk1-label">Completed (09:15 Open Window Valid)</span>
            </div>
            <div class="status-glyph completed" id="chk1-glyph">✓</div>
          </div>

          <!-- 2. Visual Inspection -->
          <div class="chk-item-card">
            <div class="chk-left-info">
              <span class="chk-main-title">2. Visual Inspection</span>
              <span class="chk-state-text" id="chk2-label">Completed (Macro Posture & GIFT Gap Aligned)</span>
            </div>
            <div class="status-glyph completed" id="chk2-glyph">✓</div>
          </div>

          <!-- 3. Pressure Test -->
          <div class="chk-item-card">
            <div class="chk-left-info">
              <span class="chk-main-title">3. Pressure Test</span>
              <span class="chk-state-text" id="chk3-label">In Progress (ML Imbalance & ₹52 Tax Hurdle)</span>
            </div>
            <div class="status-glyph in-progress" id="chk3-glyph"></div>
          </div>

          <!-- 4. Seal Replacement -->
          <div class="chk-item-card">
            <div class="chk-left-info">
              <span class="chk-main-title">4. Seal Replacement</span>
              <span class="chk-state-text" id="chk4-label">Pending (Dynamic Trailing Stop Ratchet)</span>
            </div>
            <div class="status-glyph pending" id="chk4-glyph"></div>
          </div>

          <!-- 5. Fluid Level Check -->
          <div class="chk-item-card">
            <div class="chk-left-info">
              <span class="chk-main-title">5. Fluid Level Check</span>
              <span class="chk-state-text" id="chk5-label">Pending (Single Leg Margin ≤ ₹2,470)</span>
            </div>
            <div class="status-glyph pending" id="chk5-glyph"></div>
          </div>

          <!-- 6. Final Report -->
          <div class="chk-item-card">
            <div class="chk-left-info">
              <span class="chk-main-title">6. Final Report</span>
              <span class="chk-state-text" id="chk6-label">Pending (15:15 Square-Off & Audit Log)</span>
            </div>
            <div class="status-glyph pending" id="chk6-glyph"></div>
          </div>
        </div>

        <!-- Active Managed Trade Dynamic Box -->
        <div id="live-trade-wrap" style="display: none;">
          <div class="trade-active-panel">
            <div class="trade-panel-head">
              <span class="trade-panel-title" id="t-sym-title">NIFTY 24600 CE (65 Qty)</span>
              <span class="trade-panel-badge" id="t-ratchet-badge">TIER 1 BREAKEVEN</span>
            </div>
            <div class="trade-stats-grid">
              <div><span style="color: var(--text-muted);">ENTRY:</span> <span id="t-entry">₹28.10</span></div>
              <div><span style="color: var(--text-muted);">LTP:</span> <span id="t-ltp">₹31.30</span></div>
              <div><span style="color: var(--accent-red);">STOP:</span> <span id="t-stop">₹28.90</span></div>
              <div><span style="color: var(--emerald);">TARGET:</span> <span id="t-target">₹35.00</span></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 700;">
              <span id="t-move-pnl" style="color: var(--emerald);">Move: +3.20 pts (+₹208.00)</span>
              <span style="color: var(--text-muted);">15m Theta Stop Active</span>
            </div>
          </div>
        </div>

        <!-- Bottom Action Buttons Exactly as Screenshot -->
        <button class="btn-complete-emerald" id="btn-complete-action" onclick="event.stopPropagation(); toggleAutoPilot()">
          <span id="btn-action-label">Complete Job</span>
          <span>→</span>
        </button>

        <button class="btn-add-note-glass" onclick="event.stopPropagation(); triggerSquareOffAll()">
          <span>Add Note (15:15 Square-Off Guard)</span>
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
            <polyline points="14 2 14 8 20 8"></polyline>
            <line x1="16" y1="13" x2="8" y2="13"></line>
            <line x1="16" y1="17" x2="8" y2="17"></line>
          </svg>
        </button>
      </div>

    </section>

  </main>

  <!-- Floating Refresh Icon Button from Screenshot -->
  <button class="floating-refresh-btn" onclick="manualRefresh()" title="Refresh HUD">
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <polyline points="23 4 23 10 17 10"></polyline>
      <polyline points="1 20 1 14 7 14"></polyline>
      <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
    </svg>
  </button>

  <script>
    let activeStep = 3;
    let ws;
    let lastPing = Date.now();

    function selectStep(step) {
      activeStep = step;

      // Update Stepper Rail on left
      document.querySelectorAll('.timeline-step-row').forEach((el, idx) => {
        el.classList.toggle('active', (idx + 1) === step);
      });

      // Update Mobile Switcher Pills
      document.querySelectorAll('.pill-tab').forEach((el, idx) => {
        el.classList.toggle('active', (idx + 1) === step);
      });

      // Update 3D Stage Deck focus class
      const deck = document.getElementById('cascadeDeck');
      if (deck) {
        deck.className = 'cascade-stage-wrap focus-' + step;
      }

      // Update mobile cards visibility
      document.querySelectorAll('.phone-mockup').forEach((el, idx) => {
        el.classList.toggle('active-mobile', (idx + 1) === step);
      });

      if (step === 2) {
        drawRouteMap();
      }
    }

    // Canvas Route Map (Drawing the glowing emerald polyline path from screenshot)
    function drawRouteMap() {
      const canvas = document.getElementById('routeCanvas');
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      const w = canvas.width;
      const h = canvas.height;

      ctx.clearRect(0, 0, w, h);

      // Dark city grid / streets background
      ctx.strokeStyle = '#101722';
      ctx.lineWidth = 1;
      for (let x = 0; x < w; x += 35) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, h);
        ctx.stroke();
      }
      for (let y = 0; y < h; y += 28) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(w, y);
        ctx.stroke();
      }

      // Glowing route polyline
      ctx.shadowColor = '#00e676';
      ctx.shadowBlur = 18;
      ctx.strokeStyle = '#00e676';
      ctx.lineWidth = 4;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      ctx.beginPath();
      ctx.moveTo(40, 115);
      ctx.lineTo(85, 90);
      ctx.lineTo(135, 100);
      ctx.lineTo(185, 55);
      ctx.lineTo(240, 75);
      ctx.lineTo(295, 40);
      ctx.lineTo(355, 30);
      ctx.stroke();

      // Start waypoint dot
      ctx.shadowBlur = 10;
      ctx.fillStyle = '#00e676';
      ctx.beginPath();
      ctx.arc(40, 115, 5, 0, Math.PI * 2);
      ctx.fill();

      // End Destination Pin with pulsing radar ring
      ctx.shadowBlur = 24;
      ctx.strokeStyle = 'rgba(0, 230, 118, 0.4)';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(355, 30, 14, 0, Math.PI * 2);
      ctx.stroke();

      ctx.fillStyle = '#00e676';
      ctx.beginPath();
      ctx.arc(355, 30, 7, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = '#06090e';
      ctx.beginPath();
      ctx.arc(355, 30, 3, 0, Math.PI * 2);
      ctx.fill();
    }

    // WebSocket Stream Connection
    function initWebSocket() {
      const loc = window.location;
      const wsProtocol = loc.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = wsProtocol + '//' + loc.host + '/ws/stream';

      ws = new WebSocket(wsUrl);

      ws.onopen = () => {
        console.log("SerQ WebSocket connected.");
      };

      ws.onmessage = (evt) => {
        const now = Date.now();
        document.getElementById('top-ws-ping').innerText = (now - lastPing) + ' ms';
        lastPing = now;

        const data = JSON.parse(evt.data);
        renderSerQData(data);
      };

      ws.onclose = () => {
        setTimeout(initWebSocket, 2000);
      };
    }

    function renderSerQData(data) {
      // 1. Account Telemetry
      if (data.pnl) {
        document.getElementById('live-cash-disp').innerText = '₹' + data.pnl.cash.toFixed(2);
        const netEl = document.getElementById('live-pnl-disp');
        netEl.innerText = '₹' + data.pnl.net_pnl.toFixed(2);
        netEl.style.color = data.pnl.net_pnl >= 0 ? 'var(--emerald)' : 'var(--accent-red)';
        document.getElementById('live-fees-disp').innerText = '₹' + data.pnl.fees.toFixed(2);
      }

      // 2. Scheduler
      if (data.scheduler) {
        document.getElementById('live-time-disp').innerText = data.scheduler.ist_time;
        document.getElementById('c2-eta').innerText = data.scheduler.current_phase.replace(/_/g, ' ');
        const chk1 = document.getElementById('chk1-label');
        if (chk1) chk1.innerText = 'Completed (' + data.scheduler.current_phase + ' • Window Valid)';
      }

      // 3. Card 1 Macro
      if (data.global_macro) {
        const gm = data.global_macro;
        document.getElementById('c1-brent').innerText = '$' + gm.crude.toFixed(2);
        document.getElementById('c1-brent-chg').innerText = (gm.crude_chg >= 0 ? '+' : '') + gm.crude_chg.toFixed(1) + '%';
        document.getElementById('c1-dxy').innerText = gm.dxy.toFixed(2);
        document.getElementById('c1-gap').innerText = (gm.gift_nifty_gap >= 0 ? '+' : '') + gm.gift_nifty_gap.toFixed(1);
        document.getElementById('c1-fear').innerText = gm.fear_index.toFixed(2);
        document.getElementById('c1-synthesis').innerText = 'Posture: ' + gm.posture + ' • Crude: $' + gm.crude.toFixed(2);
        document.getElementById('chk2-label').innerText = 'Completed (' + gm.posture + ' Posture Valid)';
      }

      // 4. Card 2 Spot & Orderbook
      if (data.quotes && data.quotes['NIFTY_SPOT']) {
        const spot = data.quotes['NIFTY_SPOT'];
        document.getElementById('c2-spot').innerText = spot.mid.toFixed(2) + ' Spot';
      }

      if (data.quotes) {
        const qList = document.getElementById('c2-quotes-list');
        let html = '';
        for (const [sym, q] of Object.entries(data.quotes)) {
          if (sym === 'NIFTY_SPOT') continue;
          const isCall = sym.endsWith('_CE');
          html += '<div class="quote-item-row">' +
            '<div>' +
              '<div style="font-weight:700; font-size:11px; color:' + (isCall ? 'var(--emerald)' : '#c084fc') + '">' + sym + '</div>' +
              '<div style="font-size:9px; color:var(--text-muted);">Bid: ₹' + q.bid.toFixed(2) + ' | Ask: ₹' + q.ask.toFixed(2) + '</div>' +
            '</div>' +
            '<div style="display:flex; align-items:center; gap:8px;">' +
              '<span style="font-family:\'JetBrains Mono\',monospace; font-weight:800; font-size:12px;">₹' + q.mid.toFixed(2) + '</span>' +
              '<button class="btn-quick-buy" onclick="event.stopPropagation(); orderOption(\'' + sym + '\', \'BUY\', ' + q.ask + ')">BUY 65</button>' +
            '</div>' +
          '</div>';
        }
        qList.innerHTML = html;
      }

      // 5. Card 3 Active Trade & Auto-Pilot
      if (data.auto_trade) {
        const at = data.auto_trade;
        const autoPill = document.getElementById('auto-status-pill');
        const btnAction = document.getElementById('btn-action-label');

        if (autoPill) {
          autoPill.innerText = at.is_enabled ? 'AUTO ON' : 'PAUSED';
          autoPill.style.color = at.is_enabled ? 'var(--emerald)' : 'var(--accent-amber)';
        }
        if (btnAction) {
          btnAction.innerText = at.is_enabled ? 'Complete Job (Auto Active)' : 'Resume Auto-Pilot';
        }

        const tradePanel = document.getElementById('live-trade-wrap');
        if (at.active_trades && at.active_trades.length > 0) {
          const t = at.active_trades[0];
          document.getElementById('t-sym-title').innerText = t.symbol + ' (' + t.quantity + ' Qty)';
          document.getElementById('t-ratchet-badge').innerText = t.state.replace('STATE_', '');
          document.getElementById('t-entry').innerText = '₹' + t.entry_price.toFixed(2);
          document.getElementById('t-ltp').innerText = '₹' + t.current_price.toFixed(2);
          document.getElementById('t-stop').innerText = '₹' + t.stop_price.toFixed(2);
          document.getElementById('t-target').innerText = '₹' + t.target_price.toFixed(2);

          const grossInr = t.delta_pts * t.quantity;
          const isProfit = t.delta_pts >= 0;
          document.getElementById('t-move-pnl').innerText = 'Move: ' + (isProfit ? '+' : '') + t.delta_pts.toFixed(2) + ' pts (' + (isProfit ? '+' : '') + '₹' + grossInr.toFixed(2) + ')';
          document.getElementById('t-move-pnl').style.color = isProfit ? 'var(--emerald)' : 'var(--accent-red)';
          tradePanel.style.display = 'block';

          // Progress bar updates
          document.getElementById('c3-progress-count').innerText = '6 of 6 completed';
          document.getElementById('c3-progress-fill').style.width = '100%';
          document.getElementById('chk3-glyph').className = 'status-glyph completed';
          document.getElementById('chk3-glyph').innerText = '✓';
          document.getElementById('chk4-glyph').className = 'status-glyph in-progress';
        } else {
          tradePanel.style.display = 'none';
          document.getElementById('c3-progress-count').innerText = '3 of 6 completed';
          document.getElementById('c3-progress-fill').style.width = '50%';
          document.getElementById('chk3-glyph').className = 'status-glyph in-progress';
          document.getElementById('chk3-glyph').innerText = '';
          document.getElementById('chk4-glyph').className = 'status-glyph pending';
        }
      }
    }

    // Actions
    async function toggleAutoPilot() {
      const resp = await fetch('/api/auto-trade/status');
      const st = await resp.json();
      const nextState = !st.is_enabled;
      await fetch('/api/auto-trade/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: nextState })
      });
    }

    async function triggerSquareOffAll() {
      if (!confirm("Execute emergency 15:15 square-off for all open positions immediately?")) return;
      const resp = await fetch('/api/auto-trade/square-off', { method: 'POST' });
      const data = await resp.json();
      if (data.success) {
        alert("Squared off " + data.closed_trades.length + " positions.");
      }
    }

    async function engageKillSwitch() {
      if (!confirm("ENGAGE EMERGENCY KILL SWITCH? All orders will be rejected.")) return;
      await fetch('/api/kill-switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'engage', reason: 'Operator engaged from SerQ HUD' })
      });
    }

    async function triggerMacroPoll() {
      const resp = await fetch('/api/global-macro/poll', { method: 'POST' });
      const data = await resp.json();
      if (data.status === 'SUCCESS') {
        alert("Synced Live World Cues!\nBrent: $" + data.brent + " | DXY: " + data.dxy + "\nEst Gap: " + data.gap_pts + " pts");
      }
    }

    async function onScenarioSelect(sc) {
      await fetch('/api/global-macro/scenario', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario: sc })
      });
    }

    async function orderOption(symbol, side, price) {
      const resp = await fetch('/api/paper/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol, side, price, quantity: 65 })
      });
      const res = await resp.json();
      if (res.error) alert(res.error);
      else if (res.status === 'REJECTED') alert("Risk Rejection: " + res.rejection_reason);
    }

    function manualRefresh() {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: 'PING' }));
      }
      drawRouteMap();
    }

    window.addEventListener('DOMContentLoaded', () => {
      initWebSocket();
      drawRouteMap();
    });
  </script>
</body>
</html>
"""

target_path = '/root/nifty-options-arbitrage/dashboard/index.html'
with open(target_path, 'w', encoding='utf-8') as f:
    f.write(html_content)
print(f"Written {len(html_content)} bytes cleanly to {target_path}")

# BROKER REQUIREMENTS: DHANHQ API AUDIT

**Author:** Agent 1 — Regulatory & Compliance Lead  
**Broker Analyzed:** Dhan (Moneylicious Securities Pvt. Ltd.)  
**API Version:** DhanHQ API v2  
**Date:** 2026-09-11

---

## 1. AUTHENTICATION & ACCESS LIFECYCLE

* **Credentials:** Requires `client_id` (Dhan User ID) and `access_token` (JWT).
* **Token Lifetime:** Maximum 24 hours. Tokens expire daily at 06:00 AM IST or upon revocation.
* **Generation Flow:** Manual generation via web console or programmatic generation via TOTP multi-factor authentication flow.
* **Storage Constraint:** Never stored in frontend, git repositories, or client-side Android web views. Must reside in protected server-side `.env` files.

---

## 2. NETWORK & STATIC IP WHITELISTING

* **Order API Whitelisting:** Mandatory for all write actions:
  - `POST /v2/orders` (Order Placement)
  - `PUT /v2/orders/{order-id}` (Order Modification)
  - `DELETE /v2/orders/{order-id}` (Order Cancellation)
* **IP Configuration:**
  - Dhan allows one Primary Static IP and one Secondary Static IP.
  - Set programmatically via `POST /v2/ip/setIP` or web console.
  - **7-Day Freeze:** Once an IP is configured, it cannot be modified for 7 consecutive days.
* **Data APIs Exemption:** Market Quotes, Historical Candles, Option Chain snapshots, and WebSockets do NOT mandate static IP whitelisting.
* **Architectural Implication:** In V1 (Paper Trading), no static IP registration is needed. For future live stages, trading server must be hosted on a fixed VPS (e.g. AWS EC2 / DigitalOcean) with elastic static IP.

---

## 3. RATE LIMITS & CONSTRAINTS

| Service | Limit | Burst Threshold | Error Code on Breach |
| :--- | :--- | :--- | :--- |
| **Order Placement** | 10 requests / sec | 25 requests / 5 sec | `429 Too Many Requests` |
| **Data REST Quotes** | 20 requests / sec | 50 requests / 5 sec | `429 Too Many Requests` |
| **WebSocket Ticks** | 1 connection | 1,000 instruments / conn | Disconnect / Error `4100` |
| **Static IP Check** | Whitelisted only | Exact match | `DH-905 Invalid IP` |

---

## 4. ERROR CODE MATRIX

* `DH-901`: Token Expired / Invalid Authentication.
* `DH-905`: IP Address Not Whitelisted.
* `DH-912`: Order rejected by Broker RMS (Margin Insufficient / Price out of Circuit Limits).
* `DH-920`: Rate Limit Exceeded.

**CONFIDENCE LEVEL: CONFIRMED.**

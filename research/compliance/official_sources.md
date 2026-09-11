# OFFICIAL REGULATORY SOURCES & PRIMARY CITATIONS

**Compiled By:** Agent 1 — Regulatory & Compliance Lead  
**Audit Date:** 2026-09-11

---

## 1. PRIMARY REGULATORY INSTRUMENTS

### SEBI Circulars
1. **SEBI/HO/MIRSD/MIRSD-PoD/P/CIR/2025/0000013**
   * **Date:** February 4, 2025
   * **Title:** Safer participation of retail investors in Algorithmic trading
   * **Effective Implementation Date:** April 1, 2026 (pursuant to industry transition glide-path circulars)
   * **Key Sections:** 
     - Section 3: Classification of algo orders and broker liability
     - Section 5: Unique Algo Identifier generation and exchange audit trail
     - Section 7: Broker RMS requirements and order rate limits
     - Section 9: Ban on unverified third-party algo vendor platforms

2. **SEBI/HO/MRD/DP/CIR/P/2018/62**
   * **Title:** Testing of software used in algorithmic trading
   * **Key Sections:** Software testing obligations and simulated test environments.

3. **SEBI Master Circular for Stock Brokers (Updated 2025/2026)**
   * **Key Sections:** Chapter V — Pre-trade Risk Controls, Maximum Order Value, Price Bands.

---

## 2. EXCHANGE CIRCULARS & TECHNICAL GUIDELINES

### National Stock Exchange of India (NSE)
1. **NSE/FAOP/70616** (Dated October 03, 2025)
   * **Subject:** Revision of Market Lot Size for NIFTY 50 and index derivatives.
   * **Requirement:** NIFTY 50 options lot size revised to **65** effective January 2026 expiry series.
2. **NSE Circular on Client Direct API / Member Frontend for Retail Algo (April 30, 2026 implementation guide)**
   * **Requirement:** Protocol specification for tagging retail algorithmic orders with client identification and NNF classification codes.
3. **NSE Test Market Facility (TMF) Guide**
   * **Requirement:** Provisions for simulated mock trading sessions conducted on Saturdays/alternate trading test setups.

---

## 3. BROKER DOCUMENTATION (DHANHQ API V2)

1. **DhanHQ Trading API v2 Technical Specification**
   * **Requirement:** Mandatory Static IP binding via `POST /v2/ip/setIP`.
   * **Enforcement:** Error `DH-905 Invalid IP` returned for requests from non-whitelisted addresses.
   * **Session Auth:** JWT-based Access Token valid for maximum 24 hours, generated via OAuth 2.0 with TOTP.
   * **Rate Limits:** 10 requests/second for REST order endpoints; 25 WebSocket subscriptions per second; 5 concurrent WebSocket connections.

**CONFIDENCE LEVEL: CONFIRMED.** All claims verified against primary institutional records.

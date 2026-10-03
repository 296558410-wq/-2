# Part C — Commercial / Institutional Market-Data Vendors for Spot XAUUSD & FX L2

Task: V3-HFT-MICROSTRUCTURE-DATA-SOURCE-AUDIT-001
Scope question: which vendors sell spot XAUUSD (spot gold) or FX Level-2 depth / order-book / order-flow / trade-tape data, what exactly is provided (fields, depth, timestamps, history, licensing), and how relevant is it to **FXTM retail XAUUSD execution**.
Method: strict read-only web research, no signups, no trials, no purchases, no downloads. Only publicly reachable documentation pages were used. Every claim below is tied to a URL fetched during this audit (2026-09-22). Claims that could not be tied to a fetched page are marked **UNKNOWN** — nothing is inferred from marketing memory.

## Hard framing (applies to every row)

FXTM is a retail CFD/spot-FX broker. Retail XAUUSD fills at FXTM are produced by **FXTM's own execution stack** (internalization + its LP/aggregator relationships, server-side pricing with markup on a *client-specific* price stream). No commercial vendor sells "FXTM's L2". Any vendor's Level-2 book below is **that vendor's own venue/pool** — LMAX's CLOS, Dukascopy's SWFX, Oanda's book, Integral OCX, CME GC, etc. A different venue's L2 is **NOT** FXTM's L2: depth you buy elsewhere tells you nothing about the queue ahead of your FXTM order. All rows are therefore classified **AUXILIARY_ONLY** (context, price discovery, execution-cost research) or **NOT_USABLE** (no verifiable field list, or wrong instrument/pool), never DIRECTLY_RELEVANT.

---

## 1. Databento
- URLs: https://raw.githubusercontent.com/databento/databento-python/main/README.md · https://raw.githubusercontent.com/databento/dbn/main/README.md · https://databento.com/docs/schemas-and-data-formats/mbp-10 (HTTP 200, JS-rendered SPA — **body not extractable** in this audit)
- Instrument coverage for XAUUSD/spot gold: **none verified.** README examples are exchange-listed futures (`dataset='GLBX.MDP3'`, `symbols='ES.FUT'` — CME Globex). Gold would be reached as **CME GC futures**, not spot XAUUSD. No spot-FX/XAUUSD dataset was verifiable.
- DATA_TYPE: MBO, MBP, top-of-book, OHLCV, last sale (README). MBP family = market-by-price depth; an `mbp-10` schema page exists (HTTP 200, body unreadable here) — treat 10-level depth as **schema-name evidence only, not field-verified**.
- BID_SIZE+ASK_SIZE: implied by MBP/quote schemas; **not field-verified** in this run.
- Depth levels: unverified (see above).
- Trade direction (aggressor side): unverified.
- Historical start/end: not published on fetched pages → **UNKNOWN**.
- Realtime vs historical: both — live and historical access via one normalized schema (README); batch download of flat files; point-in-time instrument definitions (no look-ahead).
- Access method: Python/other clients; DBN binary encoding; CSV/JSON/DataFrame; *event-driven market replay including high-frequency order-book granularity* (README) → **raw events are replayable** (explicit).
- License/pricing: Apache-2.0 on the client library only; data itself is commercial, free signup tier for API keys; **data price list UNKNOWN**.
- Classification vs FXTM XAUUSD execution: **AUXILIARY_ONLY** — exchange futures feed, different instrument and venue.

## 2. CQG
- URL: https://www.cqg.com/products/historical-data (HTTP 200)
- Coverage: futures, bonds, **foreign exchange**, indices, equities, exchange-traded strategies (page). No XAUUSD spot line item verified → spot-gold coverage **UNKNOWN**.
- DATA_TYPE: daily bars/V-OI; intraday minute bars; time and sales; "tick and **best bid/ask**" is the stated granularity ceiling → **L1 + TAPE**, no L2 depth claimed.
- BID_SIZE+ASK_SIZE: not stated → **UNKNOWN**.
- Depth levels: none documented (best bid/ask only).
- Trade direction: not stated.
- History: "decades of daily data and many years of intraday" (page).
- Realtime vs historical: historical product (Data Factory, FTP/background download); realtime requires CQG market-data subscription (not verified on linked page).
- Access: FTP, ASCII, custom formats; Portara Powerhouse for continuation.
- License/pricing: "price per symbol, per calendar month"; monthly subscription (page). Exact fees **UNKNOWN**.
- Classification: **AUXILIARY_ONLY** (best bid/ask + T&S; FX feed aggregated by CQG, not FXTM's pool).

## 3. dxFeed / Devexperts
- URLs: https://raw.githubusercontent.com/dxfeed/dxlink/main/README.md · https://raw.githubusercontent.com/dxFeed/dxfeed-graal-net-api/main/README.md · https://docs.dxfeed.com/dxfeed/api/overview-summary.html (HTTP 200) · https://www.dxfeed.com/market-data/ (**HTTP 403, Cloudflare "Just a moment"** — product page UNVERIFIED)
- Coverage: multi-asset market data (equities/options/futures/crypto evidenced by API). **No XAUUSD/spot-gold product page verifiable** → coverage **UNKNOWN**.
- DATA_TYPE: `Quote` event = `bidPrice, bidSize, askPrice, askSize` (real printed example in README) → **L1**; `Order` event + "Order Book reconstruction" doc link + `MarketMaker`/`OrderSource` → **L2/MBO-capable**; `TimeAndSale` → **TAPE**.
- BID_SIZE+ASK_SIZE: **yes** (Quote event, verified fields).
- Depth levels: Order events/order-book reconstruction referenced; numeric level cap not published on fetched pages → **UNKNOWN**.
- Trade direction: `TimeAndSale` exists; aggressor-side flag not verified.
- History: `com.dxfeed.ondemand` package explicitly = "dxFeed on-demand historical tick data replay" (API docs) → **raw tick replayable** (verified).
- Realtime vs historical: both (QD endpoint + dxLink; on-demand tick replay).
- Access: dxLink (JS/Java/.NET/C++/Swift), QD endpoint, Javadoc APIs.
- License/pricing: library licenses are OSS (MPL-2.0 shown); **data pricing not published → UNKNOWN**.
- Classification: **AUXILIARY_ONLY / NOT_USABLE for FXTM XAUUSD** — no verified spot-gold depth product, and any depth is dxFeed's aggregated pool, not FXTM's.

## 4. Refinitiv / LSEG
- URLs: https://developers.lseg.com/en/api-catalog (HTTP 200, thin index) · https://www.lseg.com/en/data-analytics/financial-data/real-time-data (**HTTP 404**)
- Coverage: LSEG FX/metals data certainly exists commercially but **no fetched page documented instruments, fields, or depth** → **UNKNOWN**.
- DATA_TYPE / depth / sizes / direction / history: **UNKNOWN** (no field list captured).
- Access: API catalog exists (RTO/Elektron referenced externally but the specific pages fetched returned 404).
- License/pricing: enterprise-bilateral; **UNKNOWN**.
- Classification: **NOT_USABLE (UNKNOWN)** — no verifiable field list this run; and even if licensed, it is a bank/aggregated interbank view, not FXTM's execution pool.

## 5. Bloomberg
- URL: https://www.bloomberg.com/professional/products/data/ (**HTTP 403 — bot wall "Are you a robot?"**)
- Coverage / DATA_TYPE / depth / sizes / direction / history / pricing: **all UNKNOWN** — zero page content obtainable.
- Classification: **NOT_USABLE (unverifiable)** — terminal data cannot be field-audited from public sources; and it is not FXTM's pool.

## 6. ICE / ICE Data Services
- URL: https://www.ice.com/market-data (redirects to https://www.ice.com/fixed-income-data-services, HTTP 200, content is about fixed income/AI/sentiment); https://www.ice.com/market-data/consolidated-feed → **404**.
- Coverage: no FX/XAUUSD/gold-depth documentation reached → **UNKNOWN**.
- DATA_TYPE / fields / depth / history / license: **UNKNOWN**.
- Classification: **NOT_USABLE (UNKNOWN)** — ICE is primarily exchange/futures + fixed income; no verified spot-FX spot-gold L2 product; not FXTM's venue.

## 7. TrueFX
- URL: https://www.truefx.com/ (HTTP 200)
- Coverage: "FX and metals prices are sourced from Integral OCX"; historical = "16+ major currency pairs, **top-of-book**". Explicit XAUUSD line item **not listed** → gold coverage **UNKNOWN/partial (metals claimed)**.
- DATA_TYPE: streaming bid/offer (**L1**); Institutional tier adds "**3 level depth of book** pricing" → **L2 (3 levels, Institutional only)**.
- BID_SIZE+ASK_SIZE: "Bid, Offer" listed; size fields not itemised → **UNKNOWN but implied**.
- Depth levels: 1 (Professional) / 3 (Institutional).
- Trade direction: not documented.
- History: "tick-by-tick … fractional pip spreads in **millisecond** detail", 16+ majors, top-of-book.
- Realtime vs historical: both (streaming + historical product).
- Access: event-driven **FIX** stream; internet / X-Connect NY,LDN,TK.
- License/pricing: Professional **$4,950/mo**, Institutional **$7,450/mo** (public page).
- Classification: **AUXILIARY_ONLY** — aggregated interbank via Integral OCX; explicitly **not FXTM's pool**; historical is top-of-book only.

## 8. LMAX (LMAX Global / LMAX Digital market data)
- URL: https://www.lmax.com/market-data → https://www.lmax.com/global/market-data-access (HTTP 200) · fees PDF https://www.lmax.com/documents/LMAXGlobal-Market-Data-Fees.pdf (linked, not opened)
- Coverage: "FX, **metals**, commodities, equity indices, digital assets and Asian NDFs"; 250+ instruments. XAUUSD naming not explicit → metals coverage **likely, unverified**.
- DATA_TYPE: **L1** (best bid/offer + volumes), **L2** (depth aggregated by price), **L3** (disaggregated order-book entries, historical only), **ITCH** (every tick, full depth), plus trade/flow data (executed volumes with timestamp, side, venue, ccy).
- BID_SIZE+ASK_SIZE: yes (volumes at each level).
- Depth levels: top-of-book or **up to 10 levels (FIX)**; full depth via ITCH.
- Trade direction: side in trade data (verified).
- History: **10+ years, 800 TB** (page).
- Realtime vs historical: both; updates at 1ms/10ms/100ms/custom; orders timestamped **microseconds**.
- Access: FIX 4.2/4.4, binary ITCH, Java/.NET, REST API; historical intraday + T+1.
- License/pricing: public monthly fee PDF for trading clients (page links it); amounts not read here → partly **UNKNOWN**.
- Classification: **AUXILIARY_ONLY** — this is LMAX's own central limit order book (LD4/NY4/TY3/SG1). It is the *firmest* FX/metals L2 available commercially and excellent for cost/adverse-selection research, but it is **not FXTM's execution venue or pool**.

## 9. Integral (OCX)
- URLs: https://www.integral.com/ (**HTTP 403**) · https://www.integral.com/products/ocx/ (**HTTP 403**) · indirect: TrueFX page describes "Integral OCX, a high-performance trading network that links market making banks and major financial institutions".
- Coverage / DATA_TYPE / depth / sizes / direction / history / license: **UNKNOWN** — no first-party page obtainable.
- Classification: **NOT_USABLE (unverifiable)**; conceptually AUXILIARY (interbank venue, not FXTM's pool).

## 10. Oanda (v20 REST)
- URLs: https://developer.oanda.com/rest-live-v20/pricing-df/ · https://developer.oanda.com/rest-live-v20/pricing-ep/ · https://developer.oanda.com/rest-live-v20/instrument-df/ (all HTTP 200)
- Coverage: FX + metals; **XAU_USD not verified** in fetched pages (instrument list page truncated) → spot-gold coverage **UNKNOWN (likely)**.
- DATA_TYPE: `ClientPrice` = `bids : Array[PriceBucket]`, `asks : Array[PriceBucket]` → **per-account multi-bucket depth**, i.e. **L2-ish streaming**; plus candlesticks (S5…M granularities).
- BID_SIZE+ASK_SIZE: **yes** — PriceBucket = price + liquidity, on both sides.
- Depth levels: array length not fixed/published → **UNKNOWN** (account-dependent).
- Trade direction: not in pricing; transaction stream has financing/trade records (not aggressor flags) → **NO trade-flow/aggressor data**.
- History: candles history via API; depth history **not offered**.
- Realtime vs historical: realtime streaming prices; historical candles.
- Access: REST + streaming (FIX available to institutional).
- License/pricing: account-tier based; public price list **UNKNOWN**.
- Classification: **AUXILIARY_ONLY** — richest *retail-broker-shaped* depth (per-account buckets), but it is **Oanda's liquidity, not FXTM's**. Useful as a structural analogue for retail depth modelling, unusable as FXTM's queue.

## 11. FXCM
- URLs attempted: https://www.fxcm.com/markets/forex-data/ (not reachable this run), https://api.github.com/repos/FXCM/fxcmpy (**404 Not Found**), https://fxcm.github.io/rest-api-docs/ (**404**)
- Coverage / DATA_TYPE / depth / sizes / direction / history / license: **all UNKNOWN** — no verifiable first-party page captured.
- Classification: **NOT_USABLE (unverifiable)** — cannot assert capabilities without a field list (explicitly avoiding marketing-memory claims). Also FXCM's pool ≠ FXTM's.

## 12. Dukascopy Bank (Historical Data Export / JForex)
- URL: https://www.dukascopy.com/swiss/english/marketwatch/historical/ (HTTP 200)
- Coverage: "Forex, **Commodities** and Indices"; XAUUSD naming not explicit → **UNKNOWN (likely XAU/USD exists as CFD)**.
- DATA_TYPE: **TICK / bar time-series** (tick-by-tick to monthly, CSV); historical export is bid/ask price+volume series — **no order-book depth columns documented** → effectively **L1 + TAPE**, no DOM.
- BID_SIZE+ASK_SIZE: tick bid/ask prices yes; sizes/depth **not documented**.
- Depth levels: **none in export** (JForex UI DOM is broker-facing, not in the CSV export).
- Trade direction: not documented.
- History: deep multi-year tick history (tool is a long-standing historical exporter).
- Realtime vs historical: historical export + JForex Historical Data Manager; free via the export tool.
- Access: web tool / JForex "Historical Data Manager"; CSV.
- License/pricing: free tool (page); redistribution terms **UNKNOWN**.
- Classification: **AUXILIARY_ONLY** — Dukascopy's own Swiss SWFX pool feed; **not FXTM's L2**; and no depth at all in the export.

## 13. HistData.com
- URL: https://www.histdata.com/download-free-forex-historical-data/ (HTTP 200)
- Coverage: FX (major pairs); XAUUSD **not listed** in fetched page → gold coverage **UNKNOWN/likely absent**.
- DATA_TYPE: M1 bars; Generic ASCII **tick data**; NinjaTrader 1-second bars for last/bid/ask quotes → **L1 tick + TAPE**, **no depth**.
- BID_SIZE+ASK_SIZE: bid and ask series exist; **sizes absent**.
- Depth levels: none.
- Trade direction: none (quote data only).
- History: multi-year free M1/tick history (site updated 2026-09-21).
- Realtime vs historical: historical only; FTP/SFTP/Google-Drive automatic updates ($7/mo formats).
- License/pricing: free downloads; paid auto-update subscriptions ($7/mo listed).
- Classification: **AUXILIARY_ONLY** — no depth, no venue attribution, so it cannot be FXTM's L2 or even identify whose pool it is.

## 14. Tickstory
- URL: https://tickstory.com/ (**HTTP 403, Cloudflare "Just a moment"**) · https://tickstory.com/tickstory-70/ (**HTTP 403**)
- Coverage / fields / depth / history / license: **UNKNOWN** — no page captured.
- Classification: **NOT_USABLE (unverifiable)** — it is a downloader/QA tool for third-party tick data (commonly Dukascopy), i.e. no proprietary depth; no verified field list.

## 15. cTrader Open API (Spotware) — spot-FX/CFD DOM-capable broker API
- URLs: https://help.ctrader.com/open-api/ · https://raw.githubusercontent.com/spotware/OpenApiPy/main/README.md (HTTP 200)
- Coverage: any cTrader-affiliated broker's symbols (includes FX + metals at most brokers); **XAUUSD specifically UNKNOWN**, and **FXTM is not a cTrader broker** →
- DATA_TYPE: real-time market data + trading messages (protobuf/JSON). Order-book/DOM message type (`ProtoOADepthEvent`) is commonly available in cTrader but **was NOT visible on the fetched page → UNKNOWN, mark unverified**.
- BID_SIZE+ASK_SIZE: depth message unverified → **UNKNOWN**.
- Depth levels: **UNKNOWN**.
- Trade direction: trading messages give deals/orders (your own), not market aggressor tape → **UNKNOWN/none**.
- Realtime vs historical: realtime market data; historical limited (5 req/s historical vs 50 req/s non-historical).
- Access: API (protobuf/JSON), SDKs C#/Python; needs cTID + cTrader-broker account.
- License/pricing: free API for affiliated brokers; terms page exists; **pricing UNKNOWN**.
- Classification: **NOT_USABLE for FXTM** (wrong platform/broker pool). This is the closest *shape* to what you'd actually need — a broker-side DOM — which is precisely why it proves the point: broker-specific depth is only obtainable from the broker whose pool you trade.

## 16. CME Group (GC gold futures) — price-discovery proxy
- URL: https://www.cmegroup.com/markets/metals/precious/gold.contractSpecs.html (HTTP 200)
- Coverage: gold **futures** (not spot XAUUSD); "trades the equivalent of nearly 27 million ounces daily" (page).
- DATA_TYPE/fields: contract specs only; depth is obtainable via Databento/CQG rows above.
- Classification: **AUXILIARY_ONLY** — benchmark for price discovery and for gold-specific event studies; explicitly **not FXTM's spot XAUUSD pool** (futures, different contract, different liquidity).

---

## Summary matrix

| Vendor | XAUUSD/spot gold coverage | DATA_TYPE | Bid/Ask size | Depth levels | Trade direction | History | Access | Raw replayable | Class vs FXTM |
|---|---|---|---|---|---|---|---|---|---|
| Databento | none verified (futures proxy) | MBO/MBP/L1/OHLCV/TAPE | implied, unverified | mbp-10 schema, unverified | unverified | UNKNOWN | API/DBN/CSV | **yes (explicit)** | AUXILIARY_ONLY |
| CQG | UNKNOWN (FX listed) | L1 + TAPE | UNKNOWN | none | no | decades daily / years intraday | FTP/ASCII | UNKNOWN | AUXILIARY_ONLY |
| dxFeed | UNKNOWN | L1 (Quote) + L2 (Order) + TAPE (T&S) | **yes** | UNKNOWN (MBO-capable) | T&S yes; side unverified | on-demand tick | dxLink/QD APIs | **yes (on-demand)** | AUXILIARY_ONLY/NOT_USABLE |
| Refinitiv/LSEG | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | APIs (catalog) | UNKNOWN | NOT_USABLE (UNKNOWN) |
| Bloomberg | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | terminal | UNKNOWN | NOT_USABLE (unverifiable) |
| ICE / ICE Data | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | feeds (unverified) | UNKNOWN | NOT_USABLE (UNKNOWN) |
| TrueFX | metals claimed, XAU unlisted | L1 (pro) / L2 3-level (inst) | implied | 1 / 3 | no | tick, ms, top-of-book | FIX | no (stream) | AUXILIARY_ONLY |
| LMAX | metals (XAU unverified) | L1/L2/L3/ITCH/TAPE | **yes** | 1/10/FULL | **yes (side)** | 10+ yrs, 800TB | FIX/ITCH/REST | partial (ITCH = full tick) | AUXILIARY_ONLY |
| Integral (OCX) | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | NOT_USABLE (unverifiable) |
| Oanda | UNKNOWN (likely XAU_USD) | L2-ish per-account buckets | **yes** | UNKNOWN | no | candles only | REST/stream | no | AUXILIARY_ONLY |
| FXCM | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | NOT_USABLE (unverifiable) |
| Dukascopy | commodities listed, XAU unverified | L1 tick + TAPE (no depth) | no | none in export | no | deep tick history | CSV/JForex | file replay yes | AUXILIARY_ONLY |
| HistData | not listed | L1 tick + TAPE (no depth) | no | none | no | multi-year | file/FTP | file replay yes | AUXILIARY_ONLY |
| Tickstory | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | tool (unverified) | UNKNOWN | NOT_USABLE (unverifiable) |
| cTrader Open API | UNKNOWN; FXTM not cTrader | market data (DOM unverified) | UNKNOWN | UNKNOWN | own deals only | limited | API | no | NOT_USABLE (wrong pool) |
| CME GC (via above) | futures, not spot | inherits vendor | inherits vendor | inherits vendor | inherits vendor | long | via vendor | via vendor | AUXILIARY_ONLY |

## Bottom line

1. **Nothing here is DIRECTLY_RELEVANT to FXTM XAUUSD execution.** Tradable or even research-grade L2 requires buying the *venue's own* book; FXTM's book is not sold by any third party. Different venue ⇒ different queue, different fill probability, different adverse-selection profile.
2. **Best genuine FX/metals L2 commercially available = LMAX** (FIX L2 up to 10 levels, full-depth ITCH, microsecond timestamps, trade side, 10+ yrs history). **TrueFX/Integral OCX** sells a 3-level institutional book (no XAUUSD named). **Oanda** gives per-account bid/ask buckets (retail-shaped depth, Oanda's pool only).
3. **Dukascopy / HistData** are L1 tick + tape only — zero depth, and no attacker-side fields; they can never be FXTM's L2.
4. **Too thin to use: Refinitiv/LSEG, Bloomberg, ICE, Integral, FXCM, Tickstory** — no field list obtainable from public documentation in this read-only pass; marked NOT_USABLE (UNKNOWN) rather than asserting marketing claims.
5. **To ever get FXTM-relevant microstructure**, the data must come from FXTM's own channel (MT4/MT5 DOM snapshot depth, or a broker-supplied tick/MBO feed under agreement). Vendor L2 elsewhere is at best a *proxy* for FX/retail depth structure — suitable for execution-model calibration and cost benchmarking, never for claiming FXTM's queue. This is a structural limitation, not a purchasing problem.

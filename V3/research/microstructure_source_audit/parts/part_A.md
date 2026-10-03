# Part A — Order-book / size / trade-flow data for XAUUSD: FXTM (ForexTime) + MetaTrader 5 ecosystem

Task: V3-HFT-MICROSTRUCTURE-DATA-SOURCE-AUDIT-001
Method: read-only web research. No purchases, signups, dataset downloads, or code changes.
Date of research: 2026-09-22 (Asia/Shanghai).
Evidence rule followed: every claim carries a URL + quote/paraphrase; unverifiable items are marked UNKNOWN.

Fetch caveats (important for how to read the labels below):
- `www.mql5.com` (canonical MQL5 reference) returned HTTP 403 to this tool (bot wall). Its content was read from `www.fxbook.net`, a page-for-page mirror of the MQL5 reference ("Last updated on 2026-07-24"), and the canonical mql5.com URLs are cited alongside.
- `www.fxtm.com` pages are client-side rendered: fetching returned only the HTML `<title>` (body empty). FXTM *page bodies* therefore could not be quoted. FXTM structural evidence is taken from FXTM's own public URL index (`/sitemap.xml`) plus page titles.
- `web_search` was unavailable; search used DuckDuckGo HTML/Bing result pages.

---

## A) MetaTrader 5 platform: what the API supports

### A1. DOM / Market Depth read API — **EXISTS (platform API)**
- `MarketBookAdd(symbol)` — "Provides opening of Depth of Market for a selected symbol, and subscribes for receiving notifications of the DOM changes." Returns `true` on success.
  - Canonical: https://www.mql5.com/en/docs/marketinformation/marketbookadd
  - Read via mirror: https://www.fxbook.net/docs/mql5-reference/market-info/marketbookadd/
- `MarketBookGet(symbol, book[])` — "Returns a structure array MqlBookInfo containing records of the Depth of Market of a specified symbol." Documented failure path: `Print("Could not get contents of the symbol DOM",Symbol());`
  - Canonical: https://www.mql5.com/en/docs/marketinformation/marketbookget
  - Read via mirror: http://mql5.web.fc2.com/mql5j_p/marketbookget.htm (also https://www.fxbook.net/docs/mql5-reference/market-info/marketbookget/)
- `OnBookEvent(symbol)` — called in EAs/indicators "when the BookEvent event occurs… meant for handling Depth of Market changes"; requires a prior `MarketBookAdd` subscription. BookEvents are queued and "never skipped".
  - Canonical: https://www.mql5.com/en/docs/event_handlers/onbookevent
  - Read via mirror: https://www.fxbook.net/docs/mql5-reference/event-handling/onbookevent/
- `MarketBookRelease(symbol)` — unsubscribes (documented in the same OnBookEvent note).

### A2. DOM payload structure — **EXISTS, but explicitly symbol/broker-dependent**
`MqlBookInfo`:
```
struct MqlBookInfo {
  ENUM_BOOK_TYPE type;   // Order type from ENUM_BOOK_TYPE enumeration
  double price;          // Price
  long   volume;         // Volume
  double volume_real;    // Volume with greater accuracy
};
```
- Note verbatim: **"The DOM is available only for some symbols."**
  - https://www.fxbook.net/docs/mql5-reference/constants-enumerations-and-structures/data-structures/order-book-structure/
  - Canonical: https://www.mql5.com/en/docs/constants/structures/mqlbookinfo

### A3. Tick fields (size / last / flags) — **EXISTS (platform API)**
`MqlTick` (current form):
```
datetime time;      double bid;    double ask;    double last;
ulong    volume;    long time_msc; uint flags;    double volume_real;
```
Tick flags (what changed, and trade direction): `TICK_FLAG_BID`, `TICK_FLAG_ASK`, `TICK_FLAG_LAST`, `TICK_FLAG_VOLUME`, `TICK_FLAG_BUY`, `TICK_FLAG_SELL`.
- Note: "The parameters of each tick are filled in regardless of whether there are changes compared to the previous tick."
  - https://www.fxbook.net/docs/mql5-reference/constants-enumerations-and-structures/data-structures/price-data-structure/
  - Canonical: https://www.mql5.com/en/docs/constants/structures/mqltick
- `SymbolInfoTick()` returns bid/ask/last/volume/time_msc/flags/volume_real. The mirror's own printed example for an OTC FX symbol (EURUSD) is: `[last] 0.0000  [volume] 0  [flags] 6  [volume_real] 0.00000` — i.e. zero Last/size is a **normal, documented outcome for an OTC symbol**, not evidence of a feed fault.
  - https://www.fxbook.net/docs/mql5-reference/market-info/symbolinfotick/

### A4. Tick history API — **EXISTS (platform API)**
- `CopyTicks(symbol, array, flags, from, count)` with `COPY_TICKS_INFO` (Bid/Ask changes), `COPY_TICKS_TRADE` (Last + Volume changes), `COPY_TICKS_ALL`. Default cap: "all available recent ticks (but not more than 2000)".
  - Sync behaviour: "If the local database does not provide all the requested ticks, then missing ticks will be automatically downloaded from the trade server." Cache note: "4096 last ticks for each instrument (65,536 ticks for symbols with a running Market Depth)".
  - **Directly relevant to our zero-fields question** — verbatim: "If a tick has zero values of the Bid and Ask prices, and the flags show that these data have changed (flags=TICK_FLAG_BID|TICK_FLAG_ASK), this means that **the order book (Market Depth) is empty**. In other words, there are no buy and sell orders."
  - https://www.fxbook.net/docs/mql5-reference/timeseries-and-indicators-access/copyticks/
  - Canonical: https://www.mql5.com/en/docs/series/copyticks
- `CopyTicksRange(symbol, array, flags, from_msc, to_msc)` — ticks strictly within a date range.
  - https://www.fxbook.net/docs/mql5-reference/timeseries-and-indicators-access/copyticksrange/
  - Canonical: https://www.mql5.com/en/docs/series/copyticksrange

### A5. What is broker-dependent (the decisive part) — **EXISTS (documented)**
From MetaQuotes' own MT5 Help:
- "If an instrument is traded in the over-the-counter (OTC) market, the Depth of Market can be formed based on the quotes of the broker, who may provide different prices depending on the buy or sell volume. **If the broker does not provide volumes, the DOM window functions as a scalping tool**… the Depth of Market displays price levels calculated based on the Bid and Ask prices using the price change step."
- "The number of bids and offers displayed in the DOM is determined by the symbol parameters **set by the broker**."
- "The availability of the Depth of Market feature for exchange instruments is **not guaranteed and depends on your broker**."
- Time & Sales (real trade tape, "volume of the trade") is documented only for "exchange instruments with real transaction prices".
  - https://www.metatrader5.com/en/terminal/help/trading/depth_of_market
- Price Data page: exchange mode → "A Market Depth option featuring real orders of market participants"; OTC mode → "**Only Bid and Ask stream quotes are used in OTC market trading, without data on actual executed deals.**" OTC-with-DOM mode → "no Last prices are available in this mode."
  - https://www.metatrader5.com/en/terminal/help/trading_advanced/price_data

**A-summary label: EXISTS at API level; broker-dependent at runtime. The platform can transport a DOM, but nothing obliges any FX/CFD broker to publish one, and for OTC symbols the DOM is broker-quoted indicative depth, not a venue order book.**

---

## B) FXTM (forextime.com / fxtm.com) specifically

### B1. Does FXTM publish Market Depth / Level-2 / bid-ask sizes / trade tape for XAUUSD?
**NOT_FOUND.** No FXTM page advertises Market Depth, Level 2, order book, bid/ask sizes, or a trade tape.
Evidence:
- FXTM's public URL index `https://www.fxtm.com/sitemap.xml` (fetched, full `<urlset>`) was scanned for `depth|level|order book|tick|data|api|fix|liquidity|institu`. **No** market-depth / Level-2 / order-book / tick-data / API / FIX page exists in it. The nearest items are: `…/help/trading-platform/pro-trading-tools/` (chart indicators: currency strength, Donchian, gravity, high-low, pivot, session map, **spread recorder**, order history, symbol info, Trading Central) and `…/trading/tools/` (pip/profit calculators, economic calendar, currency converter, advanced charts).
- `https://www.fxtm.com/en/trading/markets/metals/` — title only: "Spot Metals | Trade Metals with FXTM"; search snippet: "…Super-low commission and spreads as low as zero for Gold/US Dollar (XAUUSD)." → XAUUSD is offered as a **spread-quoted OTC spot-metal CFD**. (Page body JS-rendered; only `<title>` retrievable.)
- FXTM's trading education page `https://www.fxtm.com/en/help/markets-and-trading/trading-education/what-are-the-order-execution-types/` (title: "What are the order execution types?") and `https://www.fxtm.com/en/about/execution/` (title: "Trade with execution under <100ms | FXTM") concern execution speed/order types, not published depth.
- No third-party source found claiming FXTM publishes L2/DOM for XAUUSD.
**Caveat:** because FXTM body text is client-rendered, this is absence-of-evidence in FXTM's own index + absence of any third-party claim, not a quoted denial. A live `MarketBookAdd("XAUUSD")` call on an FXTM account (not permitted in this task) would be the definitive test.

### B2. Historical tick-data product
**NOT_FOUND.** No FXTM page offers a downloadable/sellable historical tick or order-book dataset (absent from `sitemap.xml`). The only tick history is the MT5 platform's own `CopyTicks`/`CopyTicksRange`, which pulls from the broker's trade server and is **broker-dependent in depth/retention** (see A4). That is platform-provided, not an FXTM data product.

### B3. FIX / institutional feed
**NOT_FOUND / UNKNOWN.** No FIX, API, DMA, liquidity-bridge, or institutional-feed page appears in FXTM's public URL index (`sitemap.xml`); Bing/DuckDuckGo queries for an FXTM FIX/institutional feed returned only generic FXTM marketing pages. FXTM's publicly documented access routes are its desktop/mobile/platform pages (`…/trading/platforms/{metatrader-4,metatrader-5,desktop-trading,mobile-trading-app}/`) only.
**Label:** NOT_FOUND on public documentation; UNKNOWN whether an unadvertised institutional FIX feed exists behind an onboarding gate.

### B4. Account-level / instrument-level restrictions on data
**PARTIAL / UNKNOWN.** FXTM's help index contains account-type, leverage, margin-call/stop-out and swap-free pages (e.g. `…/help/trading-account/account-types-and-conditions/…`), confirming data/feature availability is tied to account type, but no page states which account types (if any) receive a DOM. **UNKNOWN.**

---

## C) MT5 "tick volume" meaning: real traded size or tick count?

**Both exist; they are different fields — and for OTC symbols the real-size field is typically absent.**
- Bar-level (MetaQuotes MT5 Help, Price Data):
  - "**Tick volume**, which shows the number of ticks received during bar formation"
  - "**Volume**, i.e. the real volume of deals performed during bar formation (**may be not available for OTC markets**)"
  - https://www.metatrader5.com/en/terminal/help/trading_advanced/price_data
- Tick-level (`MqlTick`):
  - `volume` = "Volume for the current Last price"; `volume_real` = "Volume for the current Last price with greater accuracy".
  - https://www.fxbook.net/docs/mql5-reference/constants-enumerations-and-structures/data-structures/price-data-structure/
- Consequence for the V3 FXTM feed: `volume = 0`, `volume_real = 0`, `last = 0` is exactly the documented signature of an **OTC-quoted symbol where the broker supplies no executed-deal volume** (compare the mirror's own EURUSD `SymbolInfoTick` sample: `last 0.0000, volume 0, volume_real 0.00000`). It does **not** mean size data exists and is being dropped by our collector.
- Corollary: any "tick volume" computed from these streams is a **tick/arrival count proxy**, usable as an activity proxy, **never** as traded size or net order flow. (Bid/Ask-change `COPY_TICKS_INFO` ticks are quote updates, not trades; only `TICK_FLAG_BUY/SELL` — absent when `last=0` — would indicate executed deals.)

**Label: EXISTS (documented distinction); for FXTM XAUUSD the real-size variant is expected ABSENT (UNKNOWN only in the sense that we cannot probe a live FXTM account in this task).**

---

## Direct relevance to FXTM retail execution

**Label: NOT_USABLE (primary) — with a PARTIAL/AUXILIARY fallback.**
Evidence:
1. No FXTM-published XAUUSD L2/DOM/size/trade-flow source exists in FXTM's own public URL index (B1) → there is no FXTM data product to be "relevant" in the first place.
2. Even via the MT5 API, for an OTC symbol the DOM is "formed based on the quotes of the broker", and if the broker supplies no volumes the DOM degenerates to Bid/Ask + price-step levels (A5). So even a broker-quoted DOM would describe **FXTM's own quoted ladder**, not the pool that fills the order.
3. The tape/size layer (Last + Volume, Time & Sales) is documented as an **exchange** feature; in OTC mode "no Last prices are available" and executed-deal data is absent (A5). XAUUSD at FXTM is a spot-metal **CFD** (B1), i.e. OTC by construction.
4. Therefore the pool that executes an FXTM retail XAUUSD order (FXTM's internalisation / its LP aggregate) is **not observable** through any MT5-surfaced stream. What MT5 does give is Bid/Ask quote ticks + a tick-count proxy — **AUXILIARY** for latency/spread/volatility modelling only, **never** for order-flow, queue position, market impact, or adverse-selection attribution.
5. Residual gap: whether an FXTM account even exposes a (broker-quoted) XAUUSD DOM is UNKNOWN and testable only by a live `MarketBookAdd("XAUUSD")` probe outside this read-only task.

---

## Item-by-item status table

| # | Item | Label | Key URL |
|---|------|-------|---------|
| A1 | MT5 DOM read/subscribe API (`MarketBookAdd/Get`, `OnBookEvent`, `MarketBookRelease`) | EXISTS (API) | https://www.mql5.com/en/docs/marketinformation/marketbookadd |
| A2 | DOM payload `MqlBookInfo` (price/volume/volume_real/type) | EXISTS, "available only for some symbols" | https://www.mql5.com/en/docs/constants/structures/mqlbookinfo |
| A3 | Tick fields `MqlTick` (bid/ask/last/volume/volume_real/flags) | EXISTS (API) | https://www.mql5.com/en/docs/constants/structures/mqltick |
| A4 | Tick history `CopyTicks` / `CopyTicksRange` (broker-server sourced) | EXISTS (API) | https://www.mql5.com/en/docs/series/copyticks |
| A5 | Broker-dependence of DOM/tape; OTC = no real deal data | EXISTS (documented) | https://www.metatrader5.com/en/terminal/help/trading/depth_of_market · https://www.metatrader5.com/en/terminal/help/trading_advanced/price_data |
| B1 | FXTM-published XAUUSD L2/DOM/sizes/trade tape | NOT_FOUND | https://www.fxtm.com/sitemap.xml (full index; no such page) |
| B2 | FXTM historical tick-data product | NOT_FOUND | https://www.fxtm.com/sitemap.xml |
| B3 | FXTM FIX / institutional feed / public API | NOT_FOUND (public) / UNKNOWN (unadvertised) | https://www.fxtm.com/sitemap.xml |
| B4 | Account/instrument data restrictions | PARTIAL (account types exist) / UNKNOWN (no DOM statement) | https://www.fxtm.com/en/help/ |
| C | "tick volume" vs real size | EXISTS (distinct fields); real size expected ABSENT for FXTM XAUUSD | https://www.metatrader5.com/en/terminal/help/trading_advanced/price_data |
| — | FXTM XAUUSD L2/DOM/size/flow for reconstructing retail execution | **NOT_USABLE** primary; Bid/Ask+tick-count = PARTIAL/AUXILIARY | see A5 + B1 |

## Explicit distinction: "API theoretically supports" vs "FXTM actually provides"

| Capability | MT5 API theoretically supports | FXTM actually provides (public evidence) |
|---|---|---|
| Level-2 / DOM on XAUUSD | Yes, `MarketBookAdd`/`MarketBookGet`/`OnBookEvent` | NOT_FOUND — no public FXTM statement or page; UNKNOWN at runtime (needs live probe) |
| Per-level bid/ask sizes | Yes, `MqlBookInfo.volume`/`volume_real` (if broker publishes) | NOT_FOUND |
| Trade tape (Last + trade size, buy/sell flags) | Yes, `MqlTick.last/volume`, `TICK_FLAG_BUY/SELL`, `COPY_TICKS_TRADE` | NOT_FOUND; observed `last/volume/volume_real = 0` on the V3 FXTM feed |
| Historical ticks | Yes, `CopyTicks`/`CopyTicksRange` from broker server | Not as a product; only inside MT5, depth broker-dependent (UNKNOWN for FXTM) |
| FIX / institutional feed | n/a (not an MT5 API surface) | NOT_FOUND (public) / UNKNOWN (private) |

## Open items (UNKNOWN, require action outside this read-only task)
1. Does an FXTM MT5 XAUUSD symbol accept `MarketBookAdd()` (i.e. is any DOM published)? → live account probe.
2. Does FXTM expose an institutional FIX/API feed not indexed publicly? → direct FXTM institutional inquiry.
3. FXTM tick-history retention window per symbol. → live `CopyTicksRange` probe.

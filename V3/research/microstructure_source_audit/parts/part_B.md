# Part B — CME / LBMA (and FX L2 venues) Source Audit
Task: V3-HFT-MICROSTRUCTURE-DATA-SOURCE-AUDIT-001
Scope: read-only web research. No purchases, no signups, no downloads.
Constraint honored: this document does NOT claim CME GC == FXTM XAUUSD. No source found that
establishes FXTM's execution pool as CME or LBMA. Every label below is backed by a fetched URL;
anything not verifiable is UNKNOWN.

Legend: EXISTS | NOT_FOUND | UNKNOWN ; DIRECTLY_RELEVANT | PARTIALLY_RELEVANT | AUXILIARY_ONLY | NOT_USABLE

---

## A) CME Group — GC (Gold futures) & MGC (Micro Gold)

**A1. Instruments EXIST.**
- GC (Gold futures): ~27M oz/day equivalent, near 24-hour electronic access.
  https://www.cmegroup.com/markets/metals/precious/gold.html
- MGC (Micro Gold) is a CME product family member; MGC-specific page not fetched in this pass ⇒
  MGC MBO-specific verification is UNKNOWN, but MGC trades on the same Globex/MDP 3.0
  infrastructure as GC (see A2/A3).

**A2. Full order-book depth / MBO-style data EXISTS for CME Globex (incl. metals).**
Licensed vendor Databento, CME Globex MDP 3.0 dataset page states:
- "Tick-by-tick with full order book depth — All buy and sell orders at every price level.
  Get each trade, every tick, and order queue composition at all prices."
- "Nanosecond, PTP-synchronized timestamps" (up to four timestamps per event).
- Same API used for real-time and historical replay.
  https://databento.com/datasets/GLBX.MDP3

**A3. Databento is a CME-listed technology vendor and explicitly supports MBO.** CME vendor
profile lists supported functionality: **Market by Order (MBO)**, Market by Price (MBP),
Trade Summary Order Details, Implied Prices/Quantities; Market Data Level Supported: Real-Time,
Delayed, End-of-Day; datacenters incl. Aurora, IL (CME Co-Location).
https://www.cmegroup.com/solutions/market-tech-and-data-services/technology-vendor-services/databento.html

**A4. CME DataMine = CME's own historical source; licensing required.** 50+ datasets, 5,000+
products, earliest dataset 1972; includes futures/options and cash markets (BrokerTec, EBS);
workflow requires "Request a data license" + "Complete the required license agreements".
https://www.cmegroup.com/datamine.html
- Whether a *standalone CME DataMine MBO (order-by-order) product for GC/MGC* is separately
  purchasable as a named SKU was NOT verified here (catalog is JS-rendered) ⇒ **UNKNOWN** for
  that specific SKU claim. MBO availability itself is verified via A2/A3.

**A5. Real-time vs historical.** Both verified present (A2: "Same API for real-time and historical
data"; A3: Real-Time/Delayed/End-of-Day; A4: DataMine historical + CME real-time feeds).

**A — Classifications**
- CME GC trade tape / depth / queue (real-time + historical, via licensed vendors like Databento
  and CME DataMine): **EXISTS** — **AUXILIARY_ONLY**. Justification: genuine microsecond/nanosecond
  L2/MBO exists, but it is a *different venue and instrument* (US futures) from FXTM's OTC
  XAUUSD CFD; it can inform cross-venue price discovery but is not FXTM's execution venue.
- Claim "CME GC == FXTM XAUUSD": **NOT_SUPPORTED / UNKNOWN** — no source equates the two.

---

## B) LBMA — London OTC gold market

**B1. LBMA Trade Data (formerly LBMA-i) = AGGREGATE only.**
- LBMA page: daily reporting on T+1 basis for traded and open volume; weekly reports; service
  "provided and managed by Nasdaq" using data "reported electronically by LBMA members";
  "**Client specific data is not included, only the aggregated amounts. 28 fields** have been
  agreed as being reportable however not all fields are mandatory for every instrument."
  https://www.lbma.org.uk/prices-and-data/lbma-daily-trade-reporting-data
- Nasdaq (sole disseminator): "**anonymous and aggregated** trade information from LBMA members…
  a daily snapshot of the LBMA membership's share of the Loco London and Loco Zurich OTC market";
  delivered via Bloomberg Terminal / Refinitiv Eikon / B-PIPE.
  https://www.nasdaq.com/products/data/lbma-trade-data

**B2. LBMA benchmark prices are auction outcomes, not L2.** The LBMA Gold/Silver/Platinum/
Palladium Price benchmarks are administered by ICE Benchmark Administration; a licence is
required to obtain/use/redistribute real-time or historical benchmark data.
https://www.lbma.org.uk/prices-and-data/lbma-precious-metal-prices

**B3. Per-trade bid/ask size, order depth, trade direction for the public:** **NOT_FOUND.**
No public LBMA source provides per-trade bid/ask sizes, order-book depth, or per-trade direction.
Available public/paid LBMA data is turnover/open-volume statistics aggregated by product group
(spot, swap/forward, options, loan/lease/deposit). LBMA-i/Trade Data is aggregate-only by design.

**B — Classifications**
- LBMA aggregate turnover / open-volume statistics: **EXISTS** — **AUXILIARY_ONLY**. Justification:
  useful for sizing/context of the London OTC market; no order book, T+1, aggregated, and it
  covers the London *spot/loco* market, not FXTM's counterparty feed.
- LBMA public per-trade L2 / order flow / trade direction: **NOT_FOUND** — **NOT_USABLE**.

---

## C) Lead/lag and price-discovery literature

**C1. EXISTS — peer-reviewed, concrete finding.**
Hauptfleisch, M., Putniņš, T. J., & Lucey, B. M. (2016). "Who Sets the Price of Gold?
London or New York." *Journal of Futures Markets*, 36(6), 564–586. DOI 10.1002/fut.21775.
- Abstract findings (retrieved verbatim via OpenAlex record W2343583846): using intraday data
  over a 17-year period, "although **both markets contribute to price discovery, New York
  futures play a larger role on average**… This is striking given [London spot] volume traded is
  less than a tenth of [futures] volume, and illustrates the importance of market structure in
  the price discovery process." Discovery shares vary considerably across years; variation is
  related to liquidity, "daylight hours", and macroeconomic announcements; a major trading-platform
  upgrade reduces relative noise contribution but "does not greatly increase speed with which
  information is reflected in prices."
- DOI: https://doi.org/10.1002/fut.21775
- Open-access full text (UTS OPUS): https://opus.lib.uts.edu.au/bitstream/10453/41414/4/GoldILS%20JFutMkt%20Forthcoming.pdf
- Metadata record: https://api.openalex.org/works/W2343583846

**C2. Microsecond-level / FXTM-specific lead-lag:** **UNKNOWN.** No study found that measures
lead/lag between **FXTM's XAUUSD quote stream** and CME GC or LBMA prints. The C1 result is
intraday (aggregated/1-min-scale) and about London spot vs NY futures, not FXTM execution.

**C — Classification**
- Published CME-gold-futures-lead-spot evidence (C1): **EXISTS** — **PARTIALLY_RELEVANT**.
  Justification: direct, citable evidence that NY futures lead London spot at intraday horizons
  supports the *hypothesis* that CME data is informative about spot XAUUSD, but it is not
  FXTM-specific and not tick-level, so it cannot make CME data DIRECTLY_RELEVANT.
- FXTM-specific lead/lag: **UNKNOWN** — **NOT_USABLE** (no evidence).

---

## D) Venues publishing real spot FX / XAUUSD L2

**D1. LMAX Exchange — spot FX L2 EXISTS (exchange-quality).**
"central limit order book with streaming, firm limit order liquidity"; "**Real-time, streaming
full order book market data**"; "All orders time-stamped in μs (receipt to execution)";
"Strict price/time priority order matching"; "no 'last look'"; connectivity incl. **ITCH
(market data)** and FIX 4.2/4.4; FCA-regulated MTF and MAS-regulated RMO; matching engines
LD4/NY4/TY3/SG1.
https://www.lmax.com/exchange/spot-fx ; https://www.lmax.com/exchange
- XAU/USD specifically listed on LMAX Exchange: **UNKNOWN** (not verified in this pass).

**D2. CME EBS — FX only (no gold verified).** CME market-data page describes the "EBS Premium FX
Feed" as a high-frequency direct feed of "over 700 currency pairs" sourced from the EBS venue ⇒
currency pairs, not bullion. https://www.cmegroup.com/market-data.html
- EBS gold/XAUUSD: **UNKNOWN**.

**D3. Integral — UNKNOWN.** https://www.integral.com/ returned HTTP 403 (blocked to this client);
product/instrument coverage not verifiable here ⇒ **UNKNOWN**.

**D4. Does FXTM route to any of these?** **UNKNOWN / NO PUBLIC EVIDENCE.** No public disclosure
found stating FXTM's XAUUSD is sourced from LMAX, EBS, Integral, CME, or LBMA. Retail XAUUSD is
typically an OTC CFD price from the broker's liquidity providers; that pool is not publicly
enumerated. Verifying it would require FXTM's own disclosure/agreement (out of scope: read-only).

**D — Classifications**
- LMAX Exchange spot-FX full order book (real-time streaming L2 + ITCH): **EXISTS** —
  **PARTIALLY_RELEVANT**. Justification: proves an FX venue *does* publish genuine L2 to
  participants, but it is an institutional FX MTF and XAU/USD availability and FXTM routing
  are unverified.
- EBS FX feed: **EXISTS (FX-only)** — **AUXILIARY_ONLY** (currency pairs, no verified gold).
- Integral: **UNKNOWN** — **NOT_USABLE** (unverifiable here).
- Any venue proven to be FXTM's actual XAUUSD pool: **NOT_FOUND** — **NOT_USABLE**.

---

## Bottom line

- **DIRECTLY_RELEVANT: NONE.** No public source establishes L2/order-flow/trade-tape data that is
  the *same liquidity pool FXTM executes against*. CME GC/MGC MBO and LBMA statistics are
  different venues/instruments.
- CME GC/MGC MBO + trade tape: **EXISTS** (real-time + historical, via licensed vendors:
  Databento, CME DataMine) → **AUXILIARY_ONLY**.
- LBMA: aggregate turnover/open-volume only, **per-trade L2 NOT_FOUND** → **AUXILIARY_ONLY**.
- Lead/lag literature (C1): **EXISTS**, NY futures lead London spot intraday → **PARTIALLY_RELEVANT**
  as context, not FXTM-specific, not tick-level.
- Spot FX L2 venues: LMAX CLOB **EXISTS**; XAUUSD availability and FXTM routing **UNKNOWN**.
- Guardrail: **CME GC ≠ FXTM XAUUSD** (no source says otherwise).

## Method / limitations
- `web_search` was DISABLED for this run; all findings come from direct `web_fetch` of listed URLs
  (plus OpenAlex/Crossref APIs for bibliographic verification). Bing/DuckDuckGo were unusable
  (captcha/noise), so discovery was limited to known-official URLs.
- Databento and CME DataMine *catalog* pages are JS-rendered and returned no body; the concrete
  MBO/nanosecond claims are taken from Databento's dataset page and CME's own vendor profile.
- Not verified (⇒ UNKNOWN, not denied): exact CME DataMine MBO SKU for GC/MGC; MGC product page;
  LMAX XAU/USD listing; Integral coverage; EBS gold; FXTM's liquidity sources.

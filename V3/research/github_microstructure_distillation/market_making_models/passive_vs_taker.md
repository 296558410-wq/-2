# Passive vs Taker — spread capture and adverse selection (route D)

The open question (§七/§二十二): can the trader move from **paying** the spread to **capturing** it
without giving it all back to adverse selection?

## The trade-off, stated exactly

```text
TAKER     : pay spread + commission + slippage ; get immediacy ; P(fill) ~ 1 ; edge must exceed cost
PASSIVE   : capture spread ; accept P(fill) < 1 ; carry ADVERSE SELECTION and INVENTORY risk
```

Break-even for a passive quote (no inventory, no impact):

```text
E[net] = P(fill) * (spread_captured - E[adverse_move | fill]) - costs
```
The passive strategy earns only when `spread_captured > E[adverse_move | fill]`, i.e. when fills are
**not** systematically toxic.

## The mechanisms that decide it

```text
fill probability        P(fill | queue position, quote distance, spread, volatility, latency, cancel rate)
queue position          where your order sits in the FIFO/price-time queue (needs REAL book)
quote distance          how far inside the touch you sit (more edge vs fewer fills)
adverse selection       post-fill mid drift against you (markout)
toxic flow              whether incoming flow predicts continuation against you (needs signed flow)
inventory               your net position constrains how long you can keep quoting
reservation price       inventory-skewed fair value (Avellaneda-Stoikov style)
dynamic spread          widen when toxic / narrow when benign
```

## FXTM feasibility (measured)

| input | FXTM XAUUSD | consequence |
|---|---|---|
| spread const | AVAILABLE | can be captured in principle |
| markout / adverse selection | PARTIAL (L1) | measurable post-hoc |
| fill probability | **DATA_GAP** | no real queue → cannot model P(fill) |
| queue position | **DATA_GAP** | FXTM DOM is SYNTHETIC/aggregated |
| signed trade flow / toxic flow | **DATA_GAP** | volume/last identically 0 |
| inventory / reservation price | AVAILABLE (account) | modelable |
| order placement (limit) | AVAILABLE (platform) | executable in demo |

## Verdict

```text
PASSIVE / MARKET-MAKING MECHANISMS = C DATA-DEPENDENT
  - the *logic* (inventory skew, reservation price, dynamic spread, markout accounting) is
    B METHOD_TRANSFERABLE
  - the *core inputs* (P(fill), real queue, signed flow) are DATA_GAP on FXTM
  => PARK until FXTM supplies real depth/queue/trade data, or until a proxy P(fill) is validated
     ON FXTM's own execution (which requires real fills = a separate, authorised experiment)
```

**Do not assume** that spread capture is free: with a synthetic DOM and no queue model, any claimed
"passive edge" would be an untested assumption, not a mechanism. **Cost reversal is a hypothesis
here, not a result** (§二十二).

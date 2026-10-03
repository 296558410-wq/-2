# 数据缺口报告（修正版）

`ts_utc = 2026-09-25T02:11:46.868703+00:00`

| 优先级 | 缺口 | 状态 |
|---|---|---|
| P0 | 现货黄金(XAU)历史日线 | **已解决（市场价层，PIT_CONDITIONAL）** SINA XAU 5186 行 2006-09-25→2026-09-25 |
| P0 | 宏观 PIT + publication_time | **未解决** |
| P1 | 宏观 vintage/revision | **未解决** |
| P1 | 新闻 PIT | **未解决** |
| P1 | 经济日历 PIT | **未解决** |
| P2 | 高质量跨市场历史 | 部分 |

## 状态分布
```json
{"ACCESS_BLOCKED": 4, "PIT_CONDITIONAL": 8, "NOT_AVAILABLE": 1, "PIT_FAIL": 2, "AUTOMATION_FAILED": 2}
```

## 逐源事实
```text
NBS_API          TCP/TLS_FAIL hist=False ACCESS_BLOCKED      URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] 
NBS_SITE         TCP/TLS_FAIL hist=False PIT_CONDITIONAL     reachable HTTP 200 with default TLS (first-pass SSL error 
PBOC_SITE        TCP/TLS_FAIL hist=False PIT_CONDITIONAL     reachable HTTP 200; gold-reserve pages are documents, no A
SAFE_SITE        TCP/TLS_FAIL hist=False PIT_CONDITIONAL     reachable HTTP 200; monthly reserve documents, no API/publ
CHINABOND        TCP/TLS_FAIL hist=False PIT_CONDITIONAL     reachable HTTP 200; CNY yield curves exist but no API/publ
SGE_SITE         TCP/TLS_FAIL hist=False PIT_CONDITIONAL     reachable HTTP 200; daily quotes exist; no API/publication
SGE_QUOTES       TCP/TLS_FAIL hist=False ACCESS_BLOCKED      URLError: <urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] 
SHFE_DAILY       HTTP_404     hist=False NOT_AVAILABLE       HTTP 404
SHFE_SITE        DNS_OK       hist=True  PIT_CONDITIONAL     market/page data reachable, but no publication_time and no
CFFEX            TCP/TLS_FAIL hist=False ACCESS_BLOCKED      timed out on repeat (kept BLOCKED)
CHINAMONEY       DNS_OK       hist=True  PIT_CONDITIONAL     market/page data reachable, but no publication_time and no
SINA_QUOTE       DNS_OK       hist=False PIT_FAIL            reachable but no historical series in payload (quote/page 
SINA_KLINE       DNS_OK       hist=True  PIT_CONDITIONAL     verified: 2,262 daily rows since 2006-09-25 for spot XAU; 
EM_KLINE_XAU     DNS_OK       hist=True  AUTOMATION_FAILED   connection closed without response on verification; not co
EM_KLINE_GC      DNS_OK       hist=True  AUTOMATION_FAILED   connection closed without response on verification; not co
TX_KLINE         TCP/TLS_FAIL hist=False ACCESS_BLOCKED      DNS resolution failed for web.ifzq.gtimg.cn
TX_QUOTE         DNS_OK       hist=False PIT_FAIL            reachable but no historical series in payload (quote/page 
```
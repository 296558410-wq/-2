# V2 RUNTIME PROCESS / NETWORK AUDIT — 20260919 (P1 residual 3.3)

- window: 15s, samples: 3
- remote endpoints (ESTABLISHED): 30
- **model/API/Gateway endpoint hits: []**
- market-data endpoint hits: []
- python processes: 16

## remote endpoints
```
116.162.169.116:443
127.0.0.1:18789
127.0.0.1:49888
127.0.0.1:49889
127.0.0.1:50811
127.0.0.1:50813
127.0.0.1:52851
127.0.0.1:53356
127.0.0.1:55192
127.0.0.1:56865
127.0.0.1:57226
127.0.0.1:59583
127.0.0.1:60357
127.0.0.1:61929
127.0.0.1:61930
127.0.0.1:61956
127.0.0.1:61957
127.0.0.1:64149
127.0.0.1:64334
127.0.0.1:8748
127.0.0.1:8788
140.205.70.178:443
172.253.117.188:5228
20.43.185.14:443
202.89.233.101:443
203.119.174.242:443
203.119.245.36:443
4.145.79.81:443
47.93.150.172:1964
[2408:871a:3001:3000::8]:443
```

## python processes
```
"python.exe","42524","Console","1","4,036 K"
"python.exe","38924","Console","1","50,700 K"
"python.exe","30524","Console","1","4,040 K"
"python.exe","43396","Console","1","18,372 K"
"python.exe","33232","Console","1","1,172 K"
"python.exe","4044","Console","1","8,324 K"
"python.exe","22096","Console","1","1,180 K"
"python.exe","42140","Console","1","34,004 K"
"python.exe","43444","Console","1","4,032 K"
"python.exe","42344","Console","1","31,136 K"
"python.exe","54728","Console","1","1,316 K"
"python.exe","41704","Console","1","18,172 K"
"python.exe","59412","Console","1","4,264 K"
"python.exe","18228","Console","1","15,348 K"
"python.exe","54880","Console","1","4,296 K"
"python.exe","6516","Console","1","100,564 K"
```

## 结论
- MODEL/GATEWAY 端点命中数: 0  → PASS(无)
- 说明: 本审计在当前锁定状态（无 run 运行）采集；Shadow 阶段应附于每次 cycle。BROKER_ORDER_SENT=FALSE。

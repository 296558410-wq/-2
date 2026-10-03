# STRATEGY_BRAIN_REPORT

中位 horizon = 20 bars。决策类别：ENTER_LONG / ENTER_SHORT / WAIT / WAIT_DATA_GAP。
支持：策略一致 / 策略冲突 / 策略缺席 / 数据不足 → WAIT；从不强迫交易。

- **discovery**：decisions=10466 enter=6586 n_eff=6586 expectancy=-0.1423 total=-937.0650
- **validation**：decisions=6506 enter=4070 n_eff=4070 expectancy=-0.4832 total=-1966.7450
- **oos**：decisions=8018 enter=4861 n_eff=4861 expectancy=-0.3204 total=-1557.5600

冲突分布：
```
{
  "ABSENT": {
    "discovery": 3192,
    "oos": 2656,
    "validation": 2014
  },
  "AGREEMENT": {
    "discovery": 4548,
    "oos": 3436,
    "validation": 2742
  },
  "CONFLICT": {
    "discovery": 2726,
    "oos": 1926,
    "validation": 1750
  }
}
```
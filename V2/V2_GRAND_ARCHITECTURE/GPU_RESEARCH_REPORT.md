# GPU_RESEARCH_REPORT

真机 GPU 计算（非「GPU 存在」）。设备信息与实测：

- device: NVIDIA RTX A2000 Laptop GPU
- capability: [8, 6]
- torch: 2.14.0+cu126 / CUDA 12.6
- total VRAM: 4095.6 MB
- workload: {'n_bars': 26220, 'horizon': 20, 'bootstrap_resamples': 60000}
- 组合数 (batch grid): 13296
- **GPU runtime**: 2.1793 s；**CPU runtime**: 14.5518 s；**speedup**: 6.68×
- **peak VRAM**: 1223.2 MB（29.9%）
- GPU utilization: {'max': 43.0, 'mean': 27.541666666666668, 'samples': 24}
- GPU memory used: {'max': 2035.0}
- bootstrap resamples: 60000

GPU 承担：特征矩阵、rolling window、批量策略评估、bootstrap、permutation、多窗口 walk-forward、regime 条件分析。
用 chunk/streaming 控显存以适配 4 GB。

## 大规模搜索
- searched_hypotheses = 3830
- eligible(样本足够) = 3606
- selected_top_k = 60

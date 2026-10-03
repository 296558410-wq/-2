"""test_gpu.py — GPU 真实测试（CUDA 可用性 + 基本张量运算）。"""
import numpy as np
import pytest

torch = pytest.importorskip("torch")


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_cuda_available():
    assert torch.cuda.is_available()


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_device_props():
    p = torch.cuda.get_device_properties(0)
    assert p.major >= 7  # CC >= 7.0
    assert p.total_memory > 3.5e9  # ~4GB


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_gpu_matmul_matches_cpu():
    a = np.random.default_rng(0).standard_normal((512, 512)).astype(np.float32)
    cpu = a @ a
    gpu = (torch.as_tensor(a, device="cuda") @ torch.as_tensor(a, device="cuda")).cpu().numpy()
    np.testing.assert_allclose(cpu, gpu, rtol=1e-3, atol=1e-2)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_fp16_bf16_supported():
    for dt in (torch.float16, torch.bfloat16):
        t = torch.ones((64, 64), device="cuda", dtype=dt)
        r = (t @ t).float().cpu()
        assert torch.allclose(r, torch.full((64, 64), 64.0), atol=0.5)

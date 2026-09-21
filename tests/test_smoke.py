# -*- coding: utf-8 -*-
"""
tests/test_smoke.py —— 断言式冒烟测试（README 规划项 #3 的固化实现）
=====================================================================

以 run_day.run_one_day()（seed=2024 固定）为被测对象，把全天快进仿真的
关键结果固化为断言，让"逐位可复现"成为可执行保证：

  - 总能耗：节能关 354.18 kWh / 节能开 224.00 kWh（与 README、运行日报一致）
  - 水箱进水阀动作 51 次（回差充放水循环的极限环，两种策略相同）
  - 报警 2 次、联锁 1 次、机组完整启动 2 次（两种策略相同）
  - 15:00 防火阀联锁窗口（900~911 分钟）三房间 AO 全部为 0
    （联锁立即停风机/水泵/关新风阀的硬证据）

运行：python -m pytest tests -q
（首次运行约需十几秒：两次 1440 分钟快进仿真）

说明：本测试为仿真验证口径（虚拟 RC 热网络模型 + 虚拟 DDC），
断言值与 docs/运行日报.md 同源，改被控对象参数会如实失败——这正是目的。
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_day import run_one_day  # noqa: E402

# 断言基准（seed=2024，与 README「断言式冒烟测试」条目同一口径）
EXPECTED = {
    "total_kwh": {"off": 354.18, "on": 224.00},
    "valve_toggle": 51,
    "alarm_count": 2,
    "interlock_count": 1,
    "startup_count": 2,
    "interlock_window": (900, 912),  # [900, 912) 分钟 = 15:00~15:12
}


@pytest.fixture(scope="module")
def results():
    """两次全天仿真跑一次、整个模块共用（fixture 提速）。"""
    return {"off": run_one_day(energy_saving=False),
            "on": run_one_day(energy_saving=True)}


class TestSmokeDayRun:
    def test_total_energy_matches_baseline(self, results):
        assert round(results["off"].energy.total_kwh, 2) == EXPECTED["total_kwh"]["off"]
        assert round(results["on"].energy.total_kwh, 2) == EXPECTED["total_kwh"]["on"]

    def test_valve_toggle_count(self, results):
        for key in ("off", "on"):
            assert results[key].valve_toggle_count == EXPECTED["valve_toggle"]

    def test_alarm_interlock_startup_counts(self, results):
        for key in ("off", "on"):
            r = results[key]
            assert r.alarm_count == EXPECTED["alarm_count"]
            assert r.interlock_count == EXPECTED["interlock_count"]
            assert r.startup_count == EXPECTED["startup_count"]

    def test_interlock_window_ao_zero(self, results):
        lo, hi = EXPECTED["interlock_window"]
        for key in ("off", "on"):
            for room in range(3):
                window = results[key].history["op"][room][lo:hi]
                assert all(v == 0.0 for v in window), (
                    f"{key} 策略房间{room + 1} 联锁窗口 AO 未全部归零：{window}")

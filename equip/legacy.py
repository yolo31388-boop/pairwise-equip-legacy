"""装备传承与升级系统

规则:
1. 传承有成功率, 传承等级越高成功率越低, 失败时原装备降级。
2. 传承材料按部位(slot)和目标等级(基础/稀有)区分。
3. 传承等级有上限, 超过上限不能继续传承。
4. 传承成功后原装备被消耗(移除), 失败则原装备降级, 无法无限复用。
5. 传承属性按比例继承, 带固定损耗与随机波动; 传承附加属性随等级成长。
6. 传承有冷却时间与每日次数限制。
"""
import random
import time
from dataclasses import dataclass, field


@dataclass
class Equipment:
    eid: str
    name: str
    legacy_level: int = 0
    slot: str = "weapon"
    stats: dict = field(default_factory=dict)


class LegacySystem:
    MAX_LEGACY_LEVEL = 20
    COOLDOWN_SECONDS = 30.0
    DAILY_LIMIT = 5
    DAY_SECONDS = 86400

    RARE_MATERIAL_LEVEL = 10

    BASE_SUCCESS_RATE = 1.0
    SUCCESS_RATE_DECAY = 0.03
    MIN_SUCCESS_RATE = 0.05

    STAT_BASE = {"atk": 10, "def": 5, "hp": 50}
    STAT_GROWTH = 0.12

    LEVEL_INHERIT_RATIO = 0.9
    STATS_INHERIT_RATIO = 0.85
    RANDOM_FLUCTUATION = 0.05

    def __init__(self, seed=42):
        self.rng = random.Random(seed)
        self.equipment: dict[str, Equipment] = {}
        self.legacy_cd: dict[str, float] = {}
        self.daily_counts: dict[str, dict[int, int]] = {}

    def get_success_rate(self, level: int) -> float:
        """等级越高成功率越低, 最低不低于 MIN_SUCCESS_RATE。"""
        rate = self.BASE_SUCCESS_RATE - self.SUCCESS_RATE_DECAY * max(0, level)
        return round(max(self.MIN_SUCCESS_RATE, rate), 4)

    def get_fail_penalty(self, level: int) -> int:
        """失败降级惩罚: 基础降1级, 高等级额外降 level//10 级。"""
        return 1 + max(0, level) // 10

    def get_material_type(self, slot: str, level: int) -> str:
        """材料按部位区分, 高级传承(>=RARE_MATERIAL_LEVEL)需稀有材料。"""
        grade = "rare" if level >= self.RARE_MATERIAL_LEVEL else "basic"
        return f"{grade}_{slot}_legacy_stone"

    def get_max_level(self) -> int:
        return self.MAX_LEGACY_LEVEL

    def get_legacy_stats(self, level: int) -> dict:
        """传承附加属性随传承等级线性成长。"""
        multiplier = 1.0 + self.STAT_GROWTH * max(0, level)
        return {key: round(value * multiplier) for key, value in self.STAT_BASE.items()}

    def can_legacy_again(self, eid: str, current_time: float | None = None) -> bool:
        """冷却中或当日次数用尽时不可传承。"""
        if current_time is None:
            current_time = time.time()
        if self.legacy_cd.get(eid, 0.0) > current_time:
            return False
        day = int(current_time // self.DAY_SECONDS)
        if self.daily_counts.get(eid, {}).get(day, 0) >= self.DAILY_LIMIT:
            return False
        return True

    def _record_attempt(self, eid: str, current_time: float) -> None:
        self.legacy_cd[eid] = current_time + self.COOLDOWN_SECONDS
        day = int(current_time // self.DAY_SECONDS)
        self.daily_counts.setdefault(eid, {})
        self.daily_counts[eid][day] = self.daily_counts[eid].get(day, 0) + 1

    def _inherited_level(self, level: int) -> int:
        ratio = self.LEVEL_INHERIT_RATIO + self.rng.uniform(
            -self.RANDOM_FLUCTUATION, self.RANDOM_FLUCTUATION
        )
        return max(0, round(level * ratio))

    def _inherited_stats(self, stats: dict) -> dict:
        ratio = self.STATS_INHERIT_RATIO * self.rng.uniform(
            1.0 - self.RANDOM_FLUCTUATION, 1.0 + self.RANDOM_FLUCTUATION
        )
        return {key: round(value * ratio) for key, value in stats.items()}

    def legacy_transfer(
        self, src: str, dst: str, current_time: float | None = None
    ) -> tuple[bool, str]:
        if current_time is None:
            current_time = time.time()

        src_equip = self.equipment.get(src)
        dst_equip = self.equipment.get(dst)
        if src_equip is None or dst_equip is None:
            return False, "equipment_not_found"
        if src_equip.slot != dst_equip.slot:
            return False, "slot_mismatch"
        if src_equip.legacy_level <= 0:
            return False, "source_level_too_low"
        if dst_equip.legacy_level >= self.MAX_LEGACY_LEVEL:
            return False, "max_level_reached"
        if not self.can_legacy_again(src, current_time) or not self.can_legacy_again(
            dst, current_time
        ):
            return False, "cooldown_or_daily_limit"

        success = self.rng.random() < self.get_success_rate(src_equip.legacy_level)
        self._record_attempt(src, current_time)
        self._record_attempt(dst, current_time)

        if not success:
            penalty = self.get_fail_penalty(src_equip.legacy_level)
            src_equip.legacy_level = max(0, src_equip.legacy_level - penalty)
            return False, "transfer_failed_source_downgraded"

        new_level = min(
            self.MAX_LEGACY_LEVEL,
            max(dst_equip.legacy_level, self._inherited_level(src_equip.legacy_level)),
        )
        dst_equip.legacy_level = new_level
        if src_equip.stats:
            inherited = self._inherited_stats(src_equip.stats)
            merged = dict(dst_equip.stats)
            for key, value in inherited.items():
                merged[key] = max(merged.get(key, 0), value)
            dst_equip.stats = merged
        dst_equip.stats.update(
            {
                key: dst_equip.stats.get(key, 0) + bonus
                for key, bonus in self.get_legacy_stats(new_level).items()
            }
        )

        del self.equipment[src]
        return True, "transferred"

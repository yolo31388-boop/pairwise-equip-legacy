"""装备传承与升级系统

规则:
1. 传承有成功率, 等级越高成功率越低, 失败会降级;
2. 传承材料按部位与目标等级分层, 高阶传承需要稀有材料;
3. 传承有等级上限, 超过上限不能继续传承;
4. 传承成功后源装备被消耗, 失败则源装备降级, 无法无限使用;
5. 传承属性按比例继承, 存在固定损耗与随机波动;
6. 传承有冷却时间与每日次数限制, 防止刷属性。
"""
import random
import time
from dataclasses import dataclass, field

MAX_LEGACY_LEVEL = 20
COOLDOWN_SECONDS = 300.0
DAILY_LIMIT = 10
SUCCESS_BASE = 0.98
SUCCESS_DECAY = 0.03
SUCCESS_FLOOR = 0.10
INHERIT_RATIO = 0.9
FLUCTUATION = 0.05
FAIL_LEVEL_PENALTY = 3

MATERIAL_TIERS = ("normal", "rare", "epic")
SLOT_STONE = {
    "weapon": "sword",
    "armor": "guard",
    "helmet": "helm",
    "boots": "boot",
    "accessory": "ring",
}


@dataclass
class Equipment:
    eid: str
    name: str
    legacy_level: int = 0
    slot: str = "weapon"
    stats: dict = field(default_factory=dict)


class LegacySystem:
    def __init__(self, seed=42, clock=time.time):
        self.rng = random.Random(seed)
        self.clock = clock
        self.equipment: dict[str, Equipment] = {}
        self.legacy_cd: dict[str, float] = {}
        self.daily_count: dict[str, int] = {}
        self.materials: dict[str, int] = {}

    # ---- 规则1: 成功率随等级衰减 ----
    def get_success_rate(self, level: int) -> float:
        if level <= 0:
            return 1.0
        return max(SUCCESS_FLOOR, SUCCESS_BASE - SUCCESS_DECAY * level)

    # ---- 规则2: 材料按部位 + 目标等级分层 ----
    def get_material_tier(self, level: int) -> str:
        if level >= 15:
            return MATERIAL_TIERS[2]
        if level >= 8:
            return MATERIAL_TIERS[1]
        return MATERIAL_TIERS[0]

    def get_material_type(self, slot: str, level: int) -> str:
        stone = SLOT_STONE.get(slot, slot)
        return f"{self.get_material_tier(level)}_{stone}_stone"

    def get_required_materials(self, slot: str, level: int) -> dict[str, int]:
        return {self.get_material_type(slot, level): 1 + level // 5}

    # ---- 规则3: 等级上限 ----
    def get_max_level(self) -> int:
        return MAX_LEGACY_LEVEL

    # ---- 规则5: 传承属性随等级提升 ----
    def get_legacy_stats(self, level: int) -> dict:
        level = max(0, min(level, self.get_max_level()))
        return {"atk": 10 + level * 5}

    def _inherited_stats(self, src_equip: Equipment, level: int) -> dict:
        """按比例继承, 带固定损耗与随机波动。"""
        base = dict(src_equip.stats) if src_equip.stats else self.get_legacy_stats(level)
        factor = INHERIT_RATIO * self.rng.uniform(1.0 - FLUCTUATION, 1.0 + FLUCTUATION)
        return {key: round(value * factor, 2) for key, value in base.items()}

    # ---- 规则6: 冷却与每日次数 ----
    def can_legacy_again(self, eid: str, current_time: float) -> bool:
        return current_time >= self.legacy_cd.get(eid, 0.0)

    def get_daily_remaining(self, eid: str) -> int:
        return max(0, DAILY_LIMIT - self.daily_count.get(eid, 0))

    def _ready_at(self, eid: str, current_time: float | None) -> tuple[float, bool]:
        now = self.clock() if current_time is None else current_time
        return now, self.can_legacy_again(eid, now)

    # ---- 规则4: 传承主流程 ----
    def legacy_transfer(
        self,
        src: str,
        dst: str,
        current_time: float | None = None,
        consume_materials: bool = False,
    ) -> tuple[bool, str]:
        src_equip = self.equipment.get(src)
        dst_equip = self.equipment.get(dst)
        if src_equip is None or dst_equip is None:
            return False, "equipment_not_found"
        if src == dst:
            return False, "same_equipment"
        if src_equip.slot != dst_equip.slot:
            return False, "slot_mismatch"

        src_level = src_equip.legacy_level
        if src_level <= 0:
            return False, "source_level_too_low"
        if src_level > self.get_max_level():
            return False, "level_exceeds_max"

        now, cooled = self._ready_at(dst, current_time)
        if not cooled:
            return False, "cooldown_active"
        if self.get_daily_remaining(dst) <= 0:
            return False, "daily_limit_reached"

        required = self.get_required_materials(src_equip.slot, src_level)
        if consume_materials:
            for material, amount in required.items():
                if self.materials.get(material, 0) < amount:
                    return False, "insufficient_materials"
            for material, amount in required.items():
                self.materials[material] -= amount

        success = self.rng.random() < self.get_success_rate(src_level)
        self.legacy_cd[dst] = now + COOLDOWN_SECONDS
        self.daily_count[dst] = self.daily_count.get(dst, 0) + 1

        if success:
            dst_equip.legacy_level = src_level
            dst_equip.stats = self._inherited_stats(src_equip, src_level)
            del self.equipment[src]
            return True, "transferred"

        new_level = max(0, src_level - FAIL_LEVEL_PENALTY)
        src_equip.legacy_level = new_level
        dst_equip.legacy_level = max(0, dst_equip.legacy_level - 1)
        return False, "transfer_failed_level_downgraded"

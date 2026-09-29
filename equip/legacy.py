"""装备传承与升级系统 - 含6个bug"""
import random
from dataclasses import dataclass, field

@dataclass
class Equipment:
    eid: str
    name: str
    legacy_level: int = 0
    slot: str = "weapon"
    stats: dict = field(default_factory=dict)

class LegacySystem:
    def __init__(self, seed=42):
        self.rng = random.Random(seed)
        self.equipment: dict[str, Equipment] = {}
        self.legacy_cd: dict[str, float] = {}  # bug6: 无冷却

    def get_success_rate(self, level: int) -> float:
        # bug1: 100%成功
        return 1.0

    def get_material_type(self, slot: str, level: int) -> str:
        # bug2: 通用材料
        return "universal_stone"

    def get_max_level(self) -> int:
        # bug3: 无上限
        return 999

    def legacy_transfer(self, src: str, dst: str) -> tuple[bool, str]:
        # bug4: 原装备不消失
        src_equip = self.equipment[src]
        dst_equip = self.equipment[dst]
        dst_equip.legacy_level = src_equip.legacy_level
        return True, "transferred"

    def get_legacy_stats(self, level: int) -> dict:
        # bug5: 固定属性
        return {"atk": 10}

    def can_legacy_again(self, eid: str, current_time: float) -> bool:
        # bug6: 无冷却
        return True

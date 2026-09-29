"""装备传承与升级系统 - 红态测试"""
import pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from equip.legacy import LegacySystem, Equipment

class TestSuccessRate:
    def test_higher_level_lower_success(self):
        ls = LegacySystem()
        r1 = ls.get_success_rate(1)
        r15 = ls.get_success_rate(15)
        assert r15 < r1

class TestMaterialBySlot:
    def test_different_slots_use_different_materials(self):
        ls = LegacySystem()
        m1 = ls.get_material_type("weapon", 5)
        m2 = ls.get_material_type("armor", 5)
        assert m1 != m2

class TestMaxLevel:
    def test_legacy_has_max_level(self):
        ls = LegacySystem()
        assert ls.get_max_level() < 30

class TestSourceConsumed:
    def test_source_equip_consumed_on_transfer(self):
        ls = LegacySystem()
        ls.equipment["src"] = Equipment("src", "old", legacy_level=10)
        ls.equipment["dst"] = Equipment("dst", "new", legacy_level=0)
        ls.legacy_transfer("src", "dst")
        assert "src" not in ls.equipment or ls.equipment["src"].legacy_level == 0

class TestLegacyStats:
    def test_higher_legacy_gives_better_stats(self):
        ls = LegacySystem()
        s1 = ls.get_legacy_stats(1)
        s10 = ls.get_legacy_stats(10)
        assert s10["atk"] > s1["atk"]

class TestLegacyCooldown:
    def test_legacy_has_cooldown(self):
        ls = LegacySystem()
        ls.legacy_cd["e1"] = 100.0
        assert ls.can_legacy_again("e1", 50.0) == False
        assert ls.can_legacy_again("e1", 150.0) == True

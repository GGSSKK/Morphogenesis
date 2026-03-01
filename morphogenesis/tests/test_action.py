"""アクション実行器のテスト（全8アクション + クランプ境界 + TERMINATE 条件）"""
import pytest
from morphogenesis.core.action import execute
from morphogenesis.core.types import ActionCode, Segment, SCALE_MIN, SCALE_MAX


# ============================================================
# SCALE_DOWN_SMALL (code=0): scaleX *= 0.9
# ============================================================
class TestScaleDownSmall:
    """scaleX *= 0.9 のテスト"""

    def test_normal(self):
        """通常: 1.0 * 0.9 = 0.9"""
        seg = Segment(index=1, scale_x=1.0)
        execute(ActionCode.SCALE_DOWN_SMALL, seg, 5)
        assert seg.scale_x == pytest.approx(0.9)

    def test_at_minimum_boundary(self):
        """SCALE_MIN ぎりぎり: 0.06 * 0.9 = 0.054 >= 0.05 → 適用"""
        seg = Segment(index=1, scale_x=0.06)
        execute(ActionCode.SCALE_DOWN_SMALL, seg, 5)
        assert seg.scale_x == pytest.approx(0.054)

    def test_below_minimum_skip(self):
        """SCALE_MIN 未満になる場合: 0.05 * 0.9 = 0.045 < 0.05 → スキップ"""
        seg = Segment(index=1, scale_x=SCALE_MIN)
        execute(ActionCode.SCALE_DOWN_SMALL, seg, 5)
        assert seg.scale_x == SCALE_MIN  # 変更されない

    def test_returns_same_object(self):
        """戻り値は引数と同一オブジェクト"""
        seg = Segment(index=1, scale_x=1.0)
        result = execute(ActionCode.SCALE_DOWN_SMALL, seg, 5)
        assert result is seg


# ============================================================
# SCALE_UP_SMALL (code=1): scaleX *= 1.1
# ============================================================
class TestScaleUpSmall:
    """scaleX *= 1.1 のテスト"""

    def test_normal(self):
        """通常: 1.0 * 1.1 = 1.1"""
        seg = Segment(index=1, scale_x=1.0)
        execute(ActionCode.SCALE_UP_SMALL, seg, 5)
        assert seg.scale_x == pytest.approx(1.1)

    def test_at_maximum_boundary(self):
        """SCALE_MAX ぎりぎり: 7.0 * 1.1 = 7.7 <= 8.0 → 適用"""
        seg = Segment(index=1, scale_x=7.0)
        execute(ActionCode.SCALE_UP_SMALL, seg, 5)
        assert seg.scale_x == pytest.approx(7.7)

    def test_above_maximum_skip(self):
        """SCALE_MAX 超過: 7.5 * 1.1 = 8.25 > 8.0 → スキップ"""
        seg = Segment(index=1, scale_x=7.5)
        execute(ActionCode.SCALE_UP_SMALL, seg, 5)
        assert seg.scale_x == 7.5  # 変更されない

    def test_exactly_at_max(self):
        """SCALE_MAX ちょうど: 8.0 * 1.1 = 8.8 > 8.0 → スキップ"""
        seg = Segment(index=1, scale_x=SCALE_MAX)
        execute(ActionCode.SCALE_UP_SMALL, seg, 5)
        assert seg.scale_x == SCALE_MAX


# ============================================================
# MAINTAIN (code=2): no-op
# ============================================================
class TestMaintain:
    """維持（no-op）のテスト"""

    def test_no_change(self):
        """全属性が変更されない"""
        seg = Segment(index=1, scale_x=1.5, material="A")
        execute(ActionCode.MAINTAIN, seg, 5)
        assert seg.scale_x == 1.5
        assert seg.material == "A"
        assert seg.terminated is False


# ============================================================
# SCALE_UP_LARGE (code=3): scaleX *= 2.0
# ============================================================
class TestScaleUpLarge:
    """scaleX *= 2.0 のテスト"""

    def test_normal(self):
        """通常: 1.0 * 2.0 = 2.0"""
        seg = Segment(index=1, scale_x=1.0)
        execute(ActionCode.SCALE_UP_LARGE, seg, 5)
        assert seg.scale_x == pytest.approx(2.0)

    def test_above_maximum_skip(self):
        """SCALE_MAX 超過: 5.0 * 2.0 = 10.0 > 8.0 → スキップ"""
        seg = Segment(index=1, scale_x=5.0)
        execute(ActionCode.SCALE_UP_LARGE, seg, 5)
        assert seg.scale_x == 5.0  # 変更されない

    def test_at_half_max(self):
        """4.0 * 2.0 = 8.0 == SCALE_MAX → 適用"""
        seg = Segment(index=1, scale_x=4.0)
        execute(ActionCode.SCALE_UP_LARGE, seg, 5)
        assert seg.scale_x == pytest.approx(8.0)

    def test_just_over_half_max(self):
        """4.01 * 2.0 = 8.02 > 8.0 → スキップ"""
        seg = Segment(index=1, scale_x=4.01)
        execute(ActionCode.SCALE_UP_LARGE, seg, 5)
        assert seg.scale_x == 4.01


# ============================================================
# SCALE_DOWN_LARGE (code=4): scaleX *= 0.5
# ============================================================
class TestScaleDownLarge:
    """scaleX *= 0.5 のテスト"""

    def test_normal(self):
        """通常: 1.0 * 0.5 = 0.5"""
        seg = Segment(index=1, scale_x=1.0)
        execute(ActionCode.SCALE_DOWN_LARGE, seg, 5)
        assert seg.scale_x == pytest.approx(0.5)

    def test_below_minimum_skip(self):
        """SCALE_MIN 未満: 0.09 * 0.5 = 0.045 < 0.05 → スキップ"""
        seg = Segment(index=1, scale_x=0.09)
        execute(ActionCode.SCALE_DOWN_LARGE, seg, 5)
        assert seg.scale_x == 0.09  # 変更されない

    def test_at_double_min(self):
        """0.1 * 0.5 = 0.05 == SCALE_MIN → 適用"""
        seg = Segment(index=1, scale_x=0.1)
        execute(ActionCode.SCALE_DOWN_LARGE, seg, 5)
        assert seg.scale_x == pytest.approx(SCALE_MIN)

    def test_just_below_double_min(self):
        """0.099 * 0.5 = 0.0495 < 0.05 → スキップ"""
        seg = Segment(index=1, scale_x=0.099)
        execute(ActionCode.SCALE_DOWN_LARGE, seg, 5)
        assert seg.scale_x == 0.099


# ============================================================
# MATERIAL_A (code=5)
# ============================================================
class TestMaterialA:
    """マテリアルA設定のテスト"""

    def test_set_material(self):
        """マテリアルが "A" に設定される"""
        seg = Segment(index=1, scale_x=1.0, material="default")
        execute(ActionCode.MATERIAL_A, seg, 5)
        assert seg.material == "A"

    def test_overwrite_existing(self):
        """既存マテリアル "B" を "A" に上書き"""
        seg = Segment(index=1, scale_x=1.0, material="B")
        execute(ActionCode.MATERIAL_A, seg, 5)
        assert seg.material == "A"

    def test_scale_unchanged(self):
        """scaleX は変更されない"""
        seg = Segment(index=1, scale_x=2.5)
        execute(ActionCode.MATERIAL_A, seg, 5)
        assert seg.scale_x == 2.5


# ============================================================
# MATERIAL_B (code=6)
# ============================================================
class TestMaterialB:
    """マテリアルB設定のテスト"""

    def test_set_material(self):
        """マテリアルが "B" に設定される"""
        seg = Segment(index=1, scale_x=1.0, material="default")
        execute(ActionCode.MATERIAL_B, seg, 5)
        assert seg.material == "B"

    def test_overwrite_existing(self):
        """既存マテリアル "A" を "B" に上書き"""
        seg = Segment(index=1, scale_x=1.0, material="A")
        execute(ActionCode.MATERIAL_B, seg, 5)
        assert seg.material == "B"


# ============================================================
# TERMINATE (code=7): 体節数 >= 15 のみ発動
# ============================================================
class TestTerminate:
    """終了アクションのテスト"""

    def test_below_threshold(self):
        """体節数 < 15 → terminated は False のまま"""
        seg = Segment(index=10, scale_x=1.0)
        execute(ActionCode.TERMINATE, seg, 14)
        assert seg.terminated is False

    def test_at_threshold(self):
        """体節数 == 15 → terminated = True"""
        seg = Segment(index=15, scale_x=1.0)
        execute(ActionCode.TERMINATE, seg, 15)
        assert seg.terminated is True

    def test_above_threshold(self):
        """体節数 > 15 → terminated = True"""
        seg = Segment(index=20, scale_x=1.0)
        execute(ActionCode.TERMINATE, seg, 25)
        assert seg.terminated is True

    def test_at_count_one(self):
        """体節数 1 → terminated は False"""
        seg = Segment(index=1, scale_x=1.0)
        execute(ActionCode.TERMINATE, seg, 1)
        assert seg.terminated is False

    def test_scale_unchanged_on_terminate(self):
        """TERMINATE は scale を変更しない"""
        seg = Segment(index=15, scale_x=3.0)
        execute(ActionCode.TERMINATE, seg, 15)
        assert seg.scale_x == 3.0
        assert seg.terminated is True


# ============================================================
# クランプ動作: スキップ vs クランプ値適用 の検証
# ============================================================
class TestClampBehavior:
    """超過時は「変更スキップ」であり「クランプ値適用」ではないことを検証"""

    def test_scale_up_small_does_not_clamp_to_max(self):
        """SCALE_UP_SMALL: 7.5 * 1.1 = 8.25 → 8.0 にクランプされるのではなく、7.5 のまま"""
        seg = Segment(index=1, scale_x=7.5)
        execute(ActionCode.SCALE_UP_SMALL, seg, 5)
        assert seg.scale_x == 7.5  # 8.0 ではない

    def test_scale_down_small_does_not_clamp_to_min(self):
        """SCALE_DOWN_SMALL: 0.05 * 0.9 = 0.045 → 0.05 にクランプされるのではなく、0.05 のまま"""
        seg = Segment(index=1, scale_x=SCALE_MIN)
        execute(ActionCode.SCALE_DOWN_SMALL, seg, 5)
        assert seg.scale_x == SCALE_MIN  # クランプではなくスキップ

    def test_scale_up_large_does_not_clamp_to_max(self):
        """SCALE_UP_LARGE: 5.0 * 2.0 = 10.0 → 8.0 にクランプされるのではなく、5.0 のまま"""
        seg = Segment(index=1, scale_x=5.0)
        execute(ActionCode.SCALE_UP_LARGE, seg, 5)
        assert seg.scale_x == 5.0

    def test_scale_down_large_does_not_clamp_to_min(self):
        """SCALE_DOWN_LARGE: 0.09 * 0.5 = 0.045 → 0.05 にクランプされるのではなく、0.09 のまま"""
        seg = Segment(index=1, scale_x=0.09)
        execute(ActionCode.SCALE_DOWN_LARGE, seg, 5)
        assert seg.scale_x == 0.09

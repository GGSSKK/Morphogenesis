"""条件評価器のテスト（全8条件 + TOLERANCE エッジケース + N-2 フォールバック）"""
import pytest
from morphogenesis.core.condition import evaluate
from morphogenesis.core.types import ConditionCode, TOLERANCE


# ============================================================
# N1_SCALE_LT_HALF (code=0): N-1.scaleX < 0.5
# ============================================================
class TestN1ScaleLtHalf:
    """N-1.scaleX < 0.5 条件のテスト"""

    def test_clearly_below(self):
        """0.3 < 0.5 → True"""
        assert evaluate(ConditionCode.N1_SCALE_LT_HALF, 0.3, 1.0) is True

    def test_clearly_above(self):
        """0.7 < 0.5 → False"""
        assert evaluate(ConditionCode.N1_SCALE_LT_HALF, 0.7, 1.0) is False

    def test_at_threshold(self):
        """0.5 - TOLERANCE は境界値（False: 0.49 < 0.49 は偽）"""
        assert evaluate(ConditionCode.N1_SCALE_LT_HALF, 0.5 - TOLERANCE, 1.0) is False

    def test_just_below_threshold(self):
        """0.5 - TOLERANCE - 0.001 は True"""
        assert evaluate(ConditionCode.N1_SCALE_LT_HALF, 0.5 - TOLERANCE - 0.001, 1.0) is True

    def test_at_exact_half(self):
        """0.5 は 0.5 - 0.01 = 0.49 より大きいので False"""
        assert evaluate(ConditionCode.N1_SCALE_LT_HALF, 0.5, 1.0) is False

    def test_zero_scale(self):
        """0.0 < 0.5 → True"""
        assert evaluate(ConditionCode.N1_SCALE_LT_HALF, 0.0, 1.0) is True


# ============================================================
# N1_SCALE_GE_HALF (code=1): N-1.scaleX >= 0.5
# ============================================================
class TestN1ScaleGeHalf:
    """N-1.scaleX >= 0.5 条件のテスト"""

    def test_clearly_above(self):
        """0.7 >= 0.5 → True"""
        assert evaluate(ConditionCode.N1_SCALE_GE_HALF, 0.7, 1.0) is True

    def test_clearly_below(self):
        """0.3 >= 0.5 → False"""
        assert evaluate(ConditionCode.N1_SCALE_GE_HALF, 0.3, 1.0) is False

    def test_at_threshold(self):
        """0.5 - TOLERANCE = 0.49 >= 0.49 → True"""
        assert evaluate(ConditionCode.N1_SCALE_GE_HALF, 0.5 - TOLERANCE, 1.0) is True

    def test_at_exact_half(self):
        """0.5 >= 0.49 → True"""
        assert evaluate(ConditionCode.N1_SCALE_GE_HALF, 0.5, 1.0) is True

    def test_just_below_threshold(self):
        """0.5 - TOLERANCE - 0.001 = 0.489 >= 0.49 → False"""
        assert evaluate(ConditionCode.N1_SCALE_GE_HALF, 0.5 - TOLERANCE - 0.001, 1.0) is False


# ============================================================
# N1_SCALE_LT_N2 (code=2): N-1.scaleX < N-2.scaleX
# ============================================================
class TestN1ScaleLtN2:
    """N-1.scaleX < N-2.scaleX 条件のテスト"""

    def test_clearly_less(self):
        """0.5 < 1.0 → True"""
        assert evaluate(ConditionCode.N1_SCALE_LT_N2, 0.5, 1.0) is True

    def test_clearly_greater(self):
        """1.5 < 1.0 → False"""
        assert evaluate(ConditionCode.N1_SCALE_LT_N2, 1.5, 1.0) is False

    def test_equal(self):
        """1.0 < 1.0 → False（等価は「未満」ではない）"""
        assert evaluate(ConditionCode.N1_SCALE_LT_N2, 1.0, 1.0) is False

    def test_within_tolerance(self):
        """n2 - TOLERANCE + epsilon は False（TOLERANCE 内は等価扱い）"""
        # n1 = 0.995, n2 = 1.0 → n1 < n2 - 0.01 = 0.99 → False
        assert evaluate(ConditionCode.N1_SCALE_LT_N2, 0.995, 1.0) is False

    def test_just_outside_tolerance(self):
        """n2 - TOLERANCE - epsilon は True"""
        # n1 = 0.985, n2 = 1.0 → n1 < 0.99 → True
        assert evaluate(ConditionCode.N1_SCALE_LT_N2, 0.985, 1.0) is True

    def test_n2_fallback_equal(self):
        """N-2 フォールバック: n1=1.0, n2=1.0（初期値）→ False"""
        assert evaluate(ConditionCode.N1_SCALE_LT_N2, 1.0, 1.0) is False


# ============================================================
# N1_SCALE_GT_N2 (code=3): N-1.scaleX > N-2.scaleX
# ============================================================
class TestN1ScaleGtN2:
    """N-1.scaleX > N-2.scaleX 条件のテスト"""

    def test_clearly_greater(self):
        """1.5 > 1.0 → True"""
        assert evaluate(ConditionCode.N1_SCALE_GT_N2, 1.5, 1.0) is True

    def test_clearly_less(self):
        """0.5 > 1.0 → False"""
        assert evaluate(ConditionCode.N1_SCALE_GT_N2, 0.5, 1.0) is False

    def test_equal(self):
        """1.0 > 1.0 → False"""
        assert evaluate(ConditionCode.N1_SCALE_GT_N2, 1.0, 1.0) is False

    def test_within_tolerance(self):
        """n2 + TOLERANCE - epsilon は False（TOLERANCE 内は等価扱い）"""
        # n1 = 1.005, n2 = 1.0 → n1 > n2 + 0.01 = 1.01 → False
        assert evaluate(ConditionCode.N1_SCALE_GT_N2, 1.005, 1.0) is False

    def test_just_outside_tolerance(self):
        """n2 + TOLERANCE + epsilon は True"""
        # n1 = 1.015, n2 = 1.0 → n1 > 1.01 → True
        assert evaluate(ConditionCode.N1_SCALE_GT_N2, 1.015, 1.0) is True


# ============================================================
# N1_SCALE_EQ_N2 (code=4): |N-1.scaleX - N-2.scaleX| <= TOLERANCE
# ============================================================
class TestN1ScaleEqN2:
    """N-1.scaleX == N-2.scaleX（許容誤差付き）条件のテスト"""

    def test_exact_equal(self):
        """1.0 == 1.0 → True"""
        assert evaluate(ConditionCode.N1_SCALE_EQ_N2, 1.0, 1.0) is True

    def test_within_tolerance(self):
        """|1.005 - 1.0| = 0.005 <= 0.01 → True"""
        assert evaluate(ConditionCode.N1_SCALE_EQ_N2, 1.005, 1.0) is True

    def test_at_tolerance_boundary(self):
        """|1.01 - 1.0| ≈ 0.01 — 浮動小数点誤差で微小超過するためFalse"""
        # 浮動小数点: 1.01 - 1.0 = 0.010000000000000009 > TOLERANCE(0.01)
        assert evaluate(ConditionCode.N1_SCALE_EQ_N2, 1.01, 1.0) is False

    def test_just_outside_tolerance(self):
        """|1.011 - 1.0| = 0.011 > 0.01 → False"""
        assert evaluate(ConditionCode.N1_SCALE_EQ_N2, 1.011, 1.0) is False

    def test_clearly_different(self):
        """|2.0 - 1.0| = 1.0 > 0.01 → False"""
        assert evaluate(ConditionCode.N1_SCALE_EQ_N2, 2.0, 1.0) is False

    def test_negative_difference(self):
        """n1 < n2 の場合も許容誤差内なら True"""
        assert evaluate(ConditionCode.N1_SCALE_EQ_N2, 0.995, 1.0) is True

    def test_n2_fallback_default(self):
        """N-2 フォールバック: n1=1.0, n2=1.0 → True（初期値同士）"""
        assert evaluate(ConditionCode.N1_SCALE_EQ_N2, 1.0, 1.0) is True


# ============================================================
# ALWAYS_TRUE (code=5)
# ============================================================
class TestAlwaysTrue:
    """常にTrue条件のテスト"""

    def test_with_any_values(self):
        """どんな値でも True"""
        assert evaluate(ConditionCode.ALWAYS_TRUE, 0.0, 0.0) is True
        assert evaluate(ConditionCode.ALWAYS_TRUE, 100.0, 0.01) is True
        assert evaluate(ConditionCode.ALWAYS_TRUE, 0.5, 0.5) is True


# ============================================================
# N1_SCALE_LT_ONE (code=6): N-1.scaleX < 1.0
# ============================================================
class TestN1ScaleLtOne:
    """N-1.scaleX < 1.0 条件のテスト"""

    def test_clearly_below(self):
        """0.5 < 1.0 → True"""
        assert evaluate(ConditionCode.N1_SCALE_LT_ONE, 0.5, 1.0) is True

    def test_clearly_above(self):
        """1.5 < 1.0 → False"""
        assert evaluate(ConditionCode.N1_SCALE_LT_ONE, 1.5, 1.0) is False

    def test_at_threshold(self):
        """1.0 - TOLERANCE = 0.99 < 0.99 → False"""
        assert evaluate(ConditionCode.N1_SCALE_LT_ONE, 1.0 - TOLERANCE, 1.0) is False

    def test_just_below_threshold(self):
        """1.0 - TOLERANCE - 0.001 = 0.989 < 0.99 → True"""
        assert evaluate(ConditionCode.N1_SCALE_LT_ONE, 1.0 - TOLERANCE - 0.001, 1.0) is True

    def test_n2_irrelevant(self):
        """N-2 の値は無関係"""
        assert evaluate(ConditionCode.N1_SCALE_LT_ONE, 0.5, 999.0) is True


# ============================================================
# N1_SCALE_GE_ONE (code=7): N-1.scaleX >= 1.0
# ============================================================
class TestN1ScaleGeOne:
    """N-1.scaleX >= 1.0 条件のテスト"""

    def test_clearly_above(self):
        """1.5 >= 1.0 → True"""
        assert evaluate(ConditionCode.N1_SCALE_GE_ONE, 1.5, 1.0) is True

    def test_clearly_below(self):
        """0.5 >= 1.0 → False"""
        assert evaluate(ConditionCode.N1_SCALE_GE_ONE, 0.5, 1.0) is False

    def test_at_threshold(self):
        """1.0 - TOLERANCE = 0.99 >= 0.99 → True"""
        assert evaluate(ConditionCode.N1_SCALE_GE_ONE, 1.0 - TOLERANCE, 1.0) is True

    def test_at_exact_one(self):
        """1.0 >= 0.99 → True"""
        assert evaluate(ConditionCode.N1_SCALE_GE_ONE, 1.0, 1.0) is True

    def test_just_below_threshold(self):
        """0.989 >= 0.99 → False"""
        assert evaluate(ConditionCode.N1_SCALE_GE_ONE, 1.0 - TOLERANCE - 0.001, 1.0) is False


# ============================================================
# N-2 フォールバックシナリオ
# ============================================================
class TestN2Fallback:
    """N-2 不在時（segments[0] のデフォルト scale=1.0 にフォールバック）のテスト

    chain_builder で N-2 不在時に segments[0].scale_x=1.0 を渡す動作を想定。
    ここでは evaluate() に直接 n2_scale=1.0 を渡してテストする。
    """

    def test_lt_n2_with_fallback(self):
        """N-1=0.5, N-2=1.0(フォールバック) → 0.5 < 0.99 → True"""
        assert evaluate(ConditionCode.N1_SCALE_LT_N2, 0.5, 1.0) is True

    def test_gt_n2_with_fallback(self):
        """N-1=1.5, N-2=1.0(フォールバック) → 1.5 > 1.01 → True"""
        assert evaluate(ConditionCode.N1_SCALE_GT_N2, 1.5, 1.0) is True

    def test_eq_n2_with_fallback_same(self):
        """N-1=1.0, N-2=1.0(フォールバック) → |0| <= 0.01 → True"""
        assert evaluate(ConditionCode.N1_SCALE_EQ_N2, 1.0, 1.0) is True

    def test_eq_n2_with_fallback_different(self):
        """N-1=0.5, N-2=1.0(フォールバック) → |0.5| > 0.01 → False"""
        assert evaluate(ConditionCode.N1_SCALE_EQ_N2, 0.5, 1.0) is False

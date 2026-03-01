"""条件評価器（8条件、02Test準拠）

各条件コードに対応する評価関数。
TOLERANCE を用いた浮動小数点比較でエッジケースを安定処理する。
"""
from .types import ConditionCode, TOLERANCE


def evaluate(code: ConditionCode, n1_scale: float, n2_scale: float) -> bool:
    """条件コードを評価

    Args:
        code: 条件コード
        n1_scale: N-1体節のscaleX
        n2_scale: N-2体節のscaleX（不在時はsegments[0]のscale=1.0）

    Returns:
        条件が成立すれば True
    """
    if code == ConditionCode.N1_SCALE_LT_HALF:
        return n1_scale < 0.5 - TOLERANCE
    elif code == ConditionCode.N1_SCALE_GE_HALF:
        return n1_scale >= 0.5 - TOLERANCE
    elif code == ConditionCode.N1_SCALE_LT_N2:
        return n1_scale < n2_scale - TOLERANCE
    elif code == ConditionCode.N1_SCALE_GT_N2:
        return n1_scale > n2_scale + TOLERANCE
    elif code == ConditionCode.N1_SCALE_EQ_N2:
        return abs(n1_scale - n2_scale) <= TOLERANCE
    elif code == ConditionCode.ALWAYS_TRUE:
        return True
    elif code == ConditionCode.N1_SCALE_LT_ONE:
        return n1_scale < 1.0 - TOLERANCE
    elif code == ConditionCode.N1_SCALE_GE_ONE:
        return n1_scale >= 1.0 - TOLERANCE
    return False

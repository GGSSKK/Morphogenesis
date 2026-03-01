"""アクション実行器（8種、02Test準拠）

クランプ動作: スケール変更後の値が SCALE_MIN/SCALE_MAX を超える場合、
変更そのものをスキップする（クランプ値を適用するのではない）。
"""
from .types import ActionCode, Segment, SCALE_MIN, SCALE_MAX


def execute(code: ActionCode, segment: Segment, count: int,
            scale_max: float = SCALE_MAX) -> Segment:
    """アクションを体節に適用

    Args:
        code: アクションコード
        segment: 現在の体節（in-place変更される）
        count: 現在の体節数（Terminate判定用）
        scale_max: X軸スケール上限（デフォルト=SCALE_MAX）

    Returns:
        変更後のSegment（引数と同一オブジェクト）
    """
    if code == ActionCode.SCALE_DOWN_SMALL:
        new_scale = segment.scale_x * 0.9
        if new_scale >= SCALE_MIN:
            segment.scale_x = new_scale
    elif code == ActionCode.SCALE_UP_SMALL:
        new_scale = segment.scale_x * 1.1
        if new_scale <= scale_max:
            segment.scale_x = new_scale
    elif code == ActionCode.MAINTAIN:
        pass  # no-op: 現在値を維持
    elif code == ActionCode.SCALE_UP_LARGE:
        new_scale = segment.scale_x * 2.0
        if new_scale <= scale_max:
            segment.scale_x = new_scale
    elif code == ActionCode.SCALE_DOWN_LARGE:
        new_scale = segment.scale_x * 0.5
        if new_scale >= SCALE_MIN:
            segment.scale_x = new_scale
    elif code == ActionCode.MATERIAL_A:
        segment.material = "A"
    elif code == ActionCode.MATERIAL_B:
        segment.material = "B"
    elif code == ActionCode.TERMINATE:
        # 体節数が15以上の場合のみ終了フラグを立てる
        if count >= 15:
            segment.terminated = True
    return segment

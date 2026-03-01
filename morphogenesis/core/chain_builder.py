"""チェーン生成器（02Test準拠フロー）

生成アルゴリズム:
1. head = Segment(index=0, scale_x=1.0, pos_x=0.0)
2. 新体節: scale_x = N-1.scale_x, pos_x = N-1.pos_x + 1.0
3. 全ルール順次適用（条件は N-1/N-2 の scale_x で評価）
4. N-2 不在時は segments[0] にフォールバック
"""
from .types import Gene, Segment
from .condition import evaluate
from .action import execute


def build_chain(gene: Gene, max_segments: int = 30, scale_max: float = None) -> list[Segment]:
    """遺伝子からチェーン（体節列）を生成

    Args:
        gene: ルール配列を持つ遺伝子
        max_segments: 最大体節数（デフォルト30）
        scale_max: X軸スケール上限（None=デフォルトのSCALE_MAX使用）

    Returns:
        生成された体節のリスト（最低1体節）
    """
    if not gene.rules:
        return [Segment(index=0, scale_x=1.0, pos_x=0.0)]

    segments: list[Segment] = [Segment(index=0, scale_x=1.0, pos_x=0.0)]

    for i in range(1, max_segments):
        # N-1 と N-2 を取得（N-2 不在時は segments[0] にフォールバック）
        n1 = segments[-1]
        n2 = segments[-2] if len(segments) >= 2 else segments[0]

        # 新体節: N-1のscale・materialを引き継ぎ（位置は後で計算）
        seg = Segment(
            index=i,
            scale_x=n1.scale_x,
            pos_x=0.0,  # ルール適用後に計算
            material=n1.material,
        )

        # 全ルールを順次適用
        effective_max = scale_max if scale_max is not None else None
        for rule in gene.rules:
            if evaluate(rule.condition, n1.scale_x, n2.scale_x):
                if effective_max is not None:
                    execute(rule.action, seg, len(segments), scale_max=effective_max)
                else:
                    execute(rule.action, seg, len(segments))

        # 終了フラグが立っていたらチェーン終了
        if seg.terminated:
            break

        # 隣接配置: 前の体節の右端 + 自分の左端 = 隙間なし
        seg.pos_x = n1.pos_x + (n1.scale_x + seg.scale_x) / 2.0

        segments.append(seg)

    return segments

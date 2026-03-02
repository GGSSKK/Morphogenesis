"""チェーン生成器（独立モルフォゲン v2 + morphogen条件評価）

生成アルゴリズム:
1. head = Segment(index=0, scale_x=1.0, morphogen=1.0, pos_x=0.0)
2. 新体節: scale_x = N-1.scale_x, morphogen = N-1.morphogen, pos_x = N-1.pos_x + 1.0
3. 全ルール順次適用（条件は M フラグに応じて scale_x または morphogen で評価）
4. N-2 不在時は segments[0] にフォールバック
5. ルール適用後、発火ルールの T/H ビットで morphogen を更新
6. 付属肢: 体節の morphogen > gene.appendage_threshold で発生（scale_x とは脱結合）
7. 付属肢チェーン: morphogen が continuation_threshold 未満で成長停止
"""
from .types import Gene, Rule, Segment
from .condition import evaluate
from .action import execute

# モルフォゲン進化パラメータ
MORPHOGEN_SENSITIVITY = 0.2               # メインチェーン: 1体節あたり最大 ±0.2
APPENDAGE_MORPHOGEN_SENSITIVITY = 0.5     # 付属肢チェーン: 乗算的成長率（×1.5 or ×0.5/step）
MORPHOGEN_MAX = 10.0                      # 主チェーン上限（30体節でも飽和しない）
CONTINUATION_RATIO = 0.5      # 継続閾値 = 発生閾値の半分


def _eval_rule_condition(rule: Rule, n1_scale: float, n2_scale: float,
                          n1_morphogen: float, n2_morphogen: float) -> bool:
    """ルールの M フラグに応じて scale_x または morphogen で条件評価"""
    if rule.morphogen_condition:
        return evaluate(rule.condition, n1_morphogen, n2_morphogen)
    else:
        return evaluate(rule.condition, n1_scale, n2_scale)


def _update_morphogen(seg: Segment, gene: Gene,
                       n1_scale: float, n2_scale: float,
                       n1_morphogen: float, n2_morphogen: float,
                       sensitivity: float = MORPHOGEN_SENSITIVITY,
                       morphogen_ceiling: float = MORPHOGEN_MAX,
                       multiplicative: bool = False) -> None:
    """発火ルールの T/H ビットに基づいて morphogen を更新

    T(threshold_factor) が発火 → morphogen 上昇
    H(ratio_factor) が発火 → morphogen 下降

    sensitivity: 感度パラメータ
    morphogen_ceiling: 上限値（付属肢チェーンでは無制限にして飽和を回避）
    multiplicative: True の場合、乗算的進化（各ステップで ×(1+rate×sensitivity)）
        加算的: morph + rate × sens → 一定量ずつ変化（主チェーン向き）
        乗算的: morph × (1 + rate × sens) → 一定比率ずつ変化（付属肢向き）
        乗算的だと隣接節の長さ比が一定になり、劇的なサイズ変化が生まれる
    """
    t_fired = 0
    h_fired = 0
    for rule in gene.rules:
        if _eval_rule_condition(rule, n1_scale, n2_scale, n1_morphogen, n2_morphogen):
            if rule.threshold_factor:
                t_fired += 1
            if rule.ratio_factor:
                h_fired += 1

    n_rules = max(len(gene.rules), 1)
    morphogen_rate = (t_fired - h_fired) / n_rules  # [-1.0, +1.0]

    if multiplicative:
        # 乗算的: factor = 1 + rate × sensitivity
        # rate=+1, sens=0.5 → ×1.5（50%増）、rate=-1 → ×0.5（50%減）
        factor = max(0.01, 1.0 + morphogen_rate * sensitivity)
        new_morphogen = seg.morphogen * factor
    else:
        # 加算的（主チェーン）
        new_morphogen = seg.morphogen + morphogen_rate * sensitivity

    seg.morphogen = max(0.0, min(morphogen_ceiling, new_morphogen))


def build_appendage_chain(gene: Gene, head_scale: float,
                          max_segments: int = 15,
                          scale_max: float = None,
                          parent_scale: float = 1.0,
                          parent_prev_scale: float = 1.0,
                          parent_morphogen: float = 1.0,
                          parent_prev_morphogen: float = 1.0) -> list[Segment]:
    """付属肢チェーン生成（独立モルフォゲンで自然停止）

    Args:
        gene: ルール配列を持つ遺伝子（本体と同一）
        head_scale: 付属肢チェーンの先頭体節のscale_x
        max_segments: 付属肢チェーンの最大体節数（デフォルト15）
        scale_max: スケール上限（None=デフォルトのSCALE_MAX使用）
        parent_scale: 親体節のscale_x（head material決定用）
        parent_prev_scale: 親のN-1のscale_x（head material決定用）
        parent_morphogen: 親体節のmorphogen（付属肢チェーンの初期morphogen）
        parent_prev_morphogen: 親のN-1のmorphogen（head条件評価用）

    Returns:
        付属肢チェーンの体節リスト（最低1体節）
    """
    if not gene.rules:
        return [Segment(index=0, scale_x=head_scale, morphogen=parent_morphogen, pos_x=0.0)]

    # Head: 親体節パラメータからルール駆動でmaterial決定
    head = Segment(index=0, scale_x=head_scale, morphogen=parent_morphogen, pos_x=0.0)
    effective_max = scale_max if scale_max is not None else None
    for rule in gene.rules:
        if _eval_rule_condition(rule, parent_scale, parent_prev_scale,
                                parent_morphogen, parent_prev_morphogen):
            if effective_max is not None:
                execute(rule.action, head, count=0,
                        scale_max=effective_max, terminate_threshold=5)
            else:
                execute(rule.action, head, count=0, terminate_threshold=5)
    # ルールによるscale変更をリセット（開始スケールを維持）
    head.scale_x = head_scale
    head.terminated = False  # TERMINATEもリセット

    segments: list[Segment] = [head]

    # 継続閾値 = 発生閾値の半分（v2: morphogen ベース）
    continuation_threshold = gene.appendage_threshold * CONTINUATION_RATIO

    for i in range(1, max_segments):
        n1 = segments[-1]

        # morphogen チェック: 前体節のmorphogenが不足 → 成長停止
        if n1.morphogen < continuation_threshold:
            break

        n2 = segments[-2] if len(segments) >= 2 else segments[0]

        seg = Segment(
            index=i,
            scale_x=n1.scale_x,
            morphogen=n1.morphogen,
            pos_x=0.0,
            material=n1.material,
        )

        for rule in gene.rules:
            if _eval_rule_condition(rule, n1.scale_x, n2.scale_x,
                                    n1.morphogen, n2.morphogen):
                if effective_max is not None:
                    execute(rule.action, seg, len(segments),
                            scale_max=effective_max, terminate_threshold=5)
                else:
                    execute(rule.action, seg, len(segments),
                            terminate_threshold=5)

        # morphogen 更新（付属肢チェーン: 乗算的 + 上限なし → 各ステップで一定比率変化）
        _update_morphogen(seg, gene, n1.scale_x, n2.scale_x,
                          n1.morphogen, n2.morphogen,
                          sensitivity=APPENDAGE_MORPHOGEN_SENSITIVITY,
                          morphogen_ceiling=float('inf'),
                          multiplicative=True)

        if seg.terminated:
            break

        seg.pos_x = n1.pos_x + (n1.scale_x + seg.scale_x) / 2.0
        segments.append(seg)

    return segments


def build_chain(gene: Gene, max_segments: int = 30, scale_max: float = None,
                max_appendage_segments: int = 15) -> list[Segment]:
    """遺伝子からチェーン（体節列）を生成

    付属肢判定は独立モルフォゲンベース:
    体節の morphogen > gene.appendage_threshold → 付属肢を発生
    （scale_x とは脱結合: 小さい体節でも morphogen が高ければ付属肢あり）

    条件評価は M フラグに応じて:
    M=0: n1.scale_x / n2.scale_x で条件評価（従来の CA 規則）
    M=1: n1.morphogen / n2.morphogen で条件評価（morphogen 駆動）

    Args:
        gene: ルール配列を持つ遺伝子
        max_segments: 最大体節数（デフォルト30）
        scale_max: X軸スケール上限（None=デフォルトのSCALE_MAX使用）
        max_appendage_segments: 付属肢チェーンの最大体節数（デフォルト15）

    Returns:
        生成された体節のリスト（最低1体節）
    """
    if not gene.rules:
        return [Segment(index=0, scale_x=1.0, pos_x=0.0)]

    segments: list[Segment] = [Segment(index=0, scale_x=1.0, morphogen=1.0, pos_x=0.0)]

    for i in range(1, max_segments):
        # N-1 と N-2 を取得（N-2 不在時は segments[0] にフォールバック）
        n1 = segments[-1]
        n2 = segments[-2] if len(segments) >= 2 else segments[0]

        # 新体節: N-1のscale・morphogen・materialを引き継ぎ（位置は後で計算）
        seg = Segment(
            index=i,
            scale_x=n1.scale_x,
            morphogen=n1.morphogen,
            pos_x=0.0,  # ルール適用後に計算
            material=n1.material,
        )

        # 全ルールを順次適用（M フラグで scale_x or morphogen を条件に使用）
        effective_max = scale_max if scale_max is not None else None
        for rule in gene.rules:
            if _eval_rule_condition(rule, n1.scale_x, n2.scale_x,
                                    n1.morphogen, n2.morphogen):
                if effective_max is not None:
                    execute(rule.action, seg, len(segments), scale_max=effective_max)
                else:
                    execute(rule.action, seg, len(segments))

        # morphogen 更新（発火ルールの T/H ビットに基づく）
        _update_morphogen(seg, gene, n1.scale_x, n2.scale_x,
                          n1.morphogen, n2.morphogen)

        # 独立モルフォゲン濃度で付属肢判定（scale_x とは脱結合）
        if seg.morphogen > gene.appendage_threshold:
            seg.has_appendage = True
            seg.appendage_scale = seg.scale_x * gene.appendage_start_ratio

        # 終了フラグが立っていたらチェーン終了
        if seg.terminated:
            break

        # 隣接配置: 前の体節の右端 + 自分の左端 = 隙間なし
        seg.pos_x = n1.pos_x + (n1.scale_x + seg.scale_x) / 2.0

        segments.append(seg)

    # 付属肢チェーン構築
    for idx, seg in enumerate(segments):
        if seg.has_appendage:
            # 親のN-1を取得（head material/条件駆動用）
            parent_prev = segments[idx - 1] if idx >= 1 else segments[0]
            # 親のN-2を取得
            parent_prev2 = segments[idx - 2] if idx >= 2 else segments[0]
            seg.appendage_chain = build_appendage_chain(
                gene, head_scale=seg.appendage_scale,
                max_segments=max_appendage_segments,
                scale_max=scale_max,
                parent_scale=parent_prev.scale_x,
                parent_prev_scale=parent_prev2.scale_x,
                parent_morphogen=seg.morphogen,
                parent_prev_morphogen=parent_prev.morphogen,
            )

    return segments

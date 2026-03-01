"""チェーン生成器のテスト（空遺伝子 / 単一ルール / 最大体節数 / 終了 / N-2 フォールバック / マテリアル伝播）"""
import pytest
from morphogenesis.core.chain_builder import build_chain
from morphogenesis.core.types import (
    Gene, Rule, Segment, ConditionCode, ActionCode,
    SCALE_MIN, SCALE_MAX, TOLERANCE,
)


# ============================================================
# 空遺伝子
# ============================================================
class TestEmptyGene:
    """ルールなし遺伝子のテスト"""

    def test_returns_single_head(self):
        """空遺伝子 → head のみ（1体節）"""
        gene = Gene(rules=[])
        chain = build_chain(gene)
        assert len(chain) == 1

    def test_head_properties(self):
        """head の初期値確認"""
        gene = Gene(rules=[])
        chain = build_chain(gene)
        head = chain[0]
        assert head.index == 0
        assert head.scale_x == 1.0
        assert head.pos_x == 0.0
        assert head.material == "default"
        assert head.terminated is False


# ============================================================
# 単一ルール遺伝子
# ============================================================
class TestSingleRuleGene:
    """ルール1つの遺伝子のテスト"""

    def test_always_true_scale_up_small(self):
        """ALWAYS_TRUE + SCALE_UP_SMALL → 全体節が 1.1 倍ずつ成長"""
        gene = Gene(rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_UP_SMALL)])
        chain = build_chain(gene, max_segments=5)
        assert len(chain) == 5
        # head は 1.0、以降は前体節の scale * 1.1 が次体節に引き継がれ、さらに *1.1
        # seg[1]: 引き継ぎ 1.0 → ルール適用 → 1.0 * 1.1 = 1.1
        # seg[2]: 引き継ぎ 1.1 → ルール適用 → 1.1 * 1.1 = 1.21
        assert chain[0].scale_x == pytest.approx(1.0)
        assert chain[1].scale_x == pytest.approx(1.1)
        assert chain[2].scale_x == pytest.approx(1.21)

    def test_always_true_material_a(self):
        """ALWAYS_TRUE + MATERIAL_A → 全体節がマテリアルA"""
        gene = Gene(rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MATERIAL_A)])
        chain = build_chain(gene, max_segments=5)
        # head は "default"、seg[1] 以降は head の "default" を引き継いだ後に "A" が適用
        assert chain[0].material == "default"
        for seg in chain[1:]:
            assert seg.material == "A"

    def test_maintain_preserves_scale(self):
        """ALWAYS_TRUE + MAINTAIN → 全体節 scale_x=1.0"""
        gene = Gene(rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN)])
        chain = build_chain(gene, max_segments=10)
        for seg in chain:
            assert seg.scale_x == 1.0

    def test_positions_adjacent(self):
        """MAINTAIN（scale=1.0固定）の場合、隣接配置で pos_x = 0, 1, 2, 3, ...

        隣接配置: pos_x = prev.pos_x + (prev.scale_x + seg.scale_x) / 2
        全て scale=1.0 なので: pos_x = prev.pos_x + (1.0 + 1.0) / 2 = prev.pos_x + 1.0
        """
        gene = Gene(rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN)])
        chain = build_chain(gene, max_segments=5)
        for i, seg in enumerate(chain):
            assert seg.pos_x == pytest.approx(float(i))

    def test_positions_scaled_no_gap(self):
        """スケールが変わっても隙間なし（隣接配置）

        SCALE_DOWN_LARGE: scale *= 0.5
        seg[0]: scale=1.0, pos=0.0
        seg[1]: scale=0.5, pos = 0.0 + (1.0 + 0.5)/2 = 0.75
        seg[2]: scale=0.25, pos = 0.75 + (0.5 + 0.25)/2 = 1.125
        """
        gene = Gene(rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_DOWN_LARGE)])
        chain = build_chain(gene, max_segments=4)
        assert chain[0].pos_x == pytest.approx(0.0)
        assert chain[1].pos_x == pytest.approx(0.75)
        assert chain[2].pos_x == pytest.approx(1.125)


# ============================================================
# max_segments 制限
# ============================================================
class TestMaxSegments:
    """最大体節数制限のテスト"""

    def test_default_max(self):
        """デフォルト max_segments=30"""
        gene = Gene(rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN)])
        chain = build_chain(gene)
        assert len(chain) == 30

    def test_custom_max(self):
        """カスタム max_segments=10"""
        gene = Gene(rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN)])
        chain = build_chain(gene, max_segments=10)
        assert len(chain) == 10

    def test_max_one(self):
        """max_segments=1 → head のみ"""
        gene = Gene(rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN)])
        chain = build_chain(gene, max_segments=1)
        assert len(chain) == 1

    def test_max_two(self):
        """max_segments=2 → head + 1体節"""
        gene = Gene(rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN)])
        chain = build_chain(gene, max_segments=2)
        assert len(chain) == 2


# ============================================================
# 終了（TERMINATE）
# ============================================================
class TestTermination:
    """TERMINATE アクションによるチェーン終了のテスト"""

    def test_terminate_at_15(self):
        """ALWAYS_TRUE + TERMINATE → 15体節で終了（head含め15）"""
        gene = Gene(rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.TERMINATE)])
        chain = build_chain(gene, max_segments=30)
        # count は segments の長さ。15体節存在する時に次の体節で terminated=True
        # 体節0-14 = 15体節。16体節目（index=15）を生成時 count=15 → terminated → break
        assert len(chain) == 15

    def test_terminate_not_before_15(self):
        """体節数 < 15 では TERMINATE は効かない"""
        gene = Gene(rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.TERMINATE)])
        chain = build_chain(gene, max_segments=14)
        # max_segments=14 なので 14 体節で打ち止め（TERMINATE は count<15 では効かない）
        assert len(chain) == 14

    def test_terminate_with_other_rules(self):
        """複数ルール: SCALE_UP_SMALL + TERMINATE → 15体節で終了、スケールは適用済み"""
        gene = Gene(rules=[
            Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_UP_SMALL),
            Rule(ConditionCode.ALWAYS_TRUE, ActionCode.TERMINATE),
        ])
        chain = build_chain(gene, max_segments=30)
        assert len(chain) == 15
        # スケールは適用されている（head 以外は 1.1 倍ずつ成長）
        assert chain[1].scale_x == pytest.approx(1.1)


# ============================================================
# N-2 フォールバック
# ============================================================
class TestN2Fallback:
    """N-2 不在時の segments[0] フォールバックのテスト"""

    def test_first_segment_uses_head_as_n2(self):
        """index=1 生成時、N-2 は存在しないので segments[0]（head）にフォールバック

        N1_SCALE_EQ_N2 条件: head.scale=1.0, head.scale=1.0（フォールバック）→ 等価 → True
        """
        gene = Gene(rules=[Rule(ConditionCode.N1_SCALE_EQ_N2, ActionCode.MATERIAL_A)])
        chain = build_chain(gene, max_segments=3)
        # seg[1]: n1=head(1.0), n2=head(1.0, フォールバック) → EQ → True → MATERIAL_A
        assert chain[1].material == "A"

    def test_second_segment_uses_real_n2(self):
        """index=2 生成時は N-2 = segments[0]（フォールバックではなく実際の値）

        この場合 N-1=segments[1], N-2=segments[0]
        """
        gene = Gene(rules=[Rule(ConditionCode.N1_SCALE_EQ_N2, ActionCode.MATERIAL_B)])
        chain = build_chain(gene, max_segments=4)
        # seg[1]: n1=head(1.0), n2=head(1.0) → EQ → True → MATERIAL_B
        # seg[2]: n1=seg[1](1.0), n2=seg[0](1.0) → EQ → True → MATERIAL_B
        assert chain[1].material == "B"
        assert chain[2].material == "B"

    def test_n1_lt_n2_with_fallback(self):
        """N1_SCALE_LT_N2: n1=head(1.0), n2=head(1.0) → 1.0 < 0.99 → False"""
        gene = Gene(rules=[Rule(ConditionCode.N1_SCALE_LT_N2, ActionCode.MATERIAL_A)])
        chain = build_chain(gene, max_segments=3)
        # seg[1]: n1=1.0, n2=1.0(フォールバック) → 1.0 < 1.0-0.01 → False
        assert chain[1].material == "default"

    def test_n1_gt_n2_triggers_after_scale_change(self):
        """スケール変更後に N1_SCALE_GT_N2 が発動するケース

        ルール1: ALWAYS_TRUE + SCALE_UP_LARGE → scale *= 2.0
        ルール2: N1_SCALE_GT_N2 + MATERIAL_A
        seg[2]: n1=seg[1](2.0), n2=seg[0](1.0) → 2.0 > 1.01 → True → MATERIAL_A
        """
        gene = Gene(rules=[
            Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_UP_LARGE),
            Rule(ConditionCode.N1_SCALE_GT_N2, ActionCode.MATERIAL_A),
        ])
        chain = build_chain(gene, max_segments=4)
        # seg[1]: n1=head(1.0), n2=head(1.0) → GT: 1.0 > 1.01 → False → material stays "default"
        # ただし SCALE_UP_LARGE が適用されて seg[1].scale=2.0
        assert chain[1].scale_x == pytest.approx(2.0)
        assert chain[1].material == "default"  # n1(1.0) > n2(1.0)+tol は False
        # seg[2]: n1=seg[1](2.0), n2=seg[0](1.0) → GT: 2.0 > 1.01 → True → MATERIAL_A
        # SCALE_UP_LARGE: 2.0 * 2.0 = 4.0
        assert chain[2].scale_x == pytest.approx(4.0)
        assert chain[2].material == "A"


# ============================================================
# マテリアル伝播
# ============================================================
class TestMaterialPropagation:
    """マテリアルが次体節に引き継がれることのテスト"""

    def test_material_inherited(self):
        """一度 MATERIAL_A が適用されると、以降の体節にも引き継がれる

        条件: N1_SCALE_GE_ONE (常に True for scale=1.0) → MATERIAL_A
        """
        gene = Gene(rules=[Rule(ConditionCode.N1_SCALE_GE_ONE, ActionCode.MATERIAL_A)])
        chain = build_chain(gene, max_segments=5)
        assert chain[0].material == "default"  # head は変更されない
        for seg in chain[1:]:
            assert seg.material == "A"

    def test_material_can_be_overwritten(self):
        """MATERIAL_B が MATERIAL_A を上書きする

        ルール順: MATERIAL_A → MATERIAL_B（後勝ち）
        """
        gene = Gene(rules=[
            Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MATERIAL_A),
            Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MATERIAL_B),
        ])
        chain = build_chain(gene, max_segments=3)
        # 全体節に MATERIAL_A → MATERIAL_B の順で適用 → 最終的に "B"
        for seg in chain[1:]:
            assert seg.material == "B"

    def test_conditional_material_switch(self):
        """条件付きマテリアル切替

        ルール1: ALWAYS_TRUE + SCALE_DOWN_SMALL → 0.9 ずつ縮小
        ルール2: N1_SCALE_LT_HALF + MATERIAL_B → scale < 0.49 で MATERIAL_B
        """
        gene = Gene(rules=[
            Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_DOWN_SMALL),
            Rule(ConditionCode.N1_SCALE_LT_HALF, ActionCode.MATERIAL_B),
        ])
        chain = build_chain(gene, max_segments=15)
        # scale は 1.0 → 0.9 → 0.81 → 0.729 → 0.656 → 0.590 → 0.531 → 0.478 → ...
        # 0.478 < 0.49 → True
        # 最初の数体節は "default"、途中から "B" に切り替わるはず
        found_default = False
        found_b = False
        for seg in chain[1:]:
            if seg.material == "default":
                found_default = True
            elif seg.material == "B":
                found_b = True
        assert found_default, "初期は default マテリアルであるべき"
        assert found_b, "スケールが 0.5 未満になったら B に切り替わるべき"


# ============================================================
# 遺伝子シリアライズ往復
# ============================================================
class TestGeneRoundTrip:
    """遺伝子の文字列化→復元の往復テスト"""

    def test_round_trip(self):
        """ランダム遺伝子の to_string → from_string で同一チェーンを生成"""
        gene1 = Gene.random(num_rules=10, seed=123)
        s = gene1.to_string()
        gene2 = Gene.from_string(s)

        chain1 = build_chain(gene1, max_segments=20)
        chain2 = build_chain(gene2, max_segments=20)

        assert len(chain1) == len(chain2)
        for seg1, seg2 in zip(chain1, chain2):
            assert seg1.index == seg2.index
            assert seg1.scale_x == pytest.approx(seg2.scale_x)
            assert seg1.pos_x == pytest.approx(seg2.pos_x)
            assert seg1.material == seg2.material

    def test_empty_string_round_trip(self):
        """空文字列 → 空遺伝子 → head のみ"""
        gene = Gene.from_string("")
        chain = build_chain(gene)
        assert len(chain) == 1


# ============================================================
# スケール上限による実質的な安定化
# ============================================================
class TestScaleSaturation:
    """SCALE_MAX に到達するとスケール変更がスキップされる動作の確認"""

    def test_scale_up_saturates(self):
        """SCALE_UP_LARGE を繰り返すと SCALE_MAX で頭打ちになる"""
        gene = Gene(rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_UP_LARGE)])
        chain = build_chain(gene, max_segments=10)
        # 1.0 → 2.0 → 4.0 → 8.0 → 8.0（スキップ）→ 8.0...
        assert chain[0].scale_x == pytest.approx(1.0)
        assert chain[1].scale_x == pytest.approx(2.0)
        assert chain[2].scale_x == pytest.approx(4.0)
        assert chain[3].scale_x == pytest.approx(8.0)
        # 4体節目以降は 8.0 * 2.0 = 16.0 > 8.0 → スキップ → 引き継ぎの 8.0 が維持
        for seg in chain[4:]:
            assert seg.scale_x == pytest.approx(8.0)

    def test_scale_down_saturates(self):
        """SCALE_DOWN_LARGE を繰り返すと SCALE_MIN 付近で頭打ちになる"""
        gene = Gene(rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_DOWN_LARGE)])
        chain = build_chain(gene, max_segments=10)
        # 1.0 → 0.5 → 0.25 → 0.125 → 0.0625 → 0.0625（0.03125 < 0.05 → スキップ）
        assert chain[0].scale_x == pytest.approx(1.0)
        assert chain[1].scale_x == pytest.approx(0.5)
        assert chain[2].scale_x == pytest.approx(0.25)
        assert chain[3].scale_x == pytest.approx(0.125)
        assert chain[4].scale_x == pytest.approx(0.0625)
        # 0.0625 * 0.5 = 0.03125 < 0.05 → スキップ
        for seg in chain[5:]:
            assert seg.scale_x == pytest.approx(0.0625)

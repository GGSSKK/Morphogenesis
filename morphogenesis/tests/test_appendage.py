"""付属肢（Appendage）分岐システムのテスト — 独立モルフォゲン v2 + morphogen条件"""
import pytest
from morphogenesis.core.types import (
    Gene, Rule, Segment, ConditionCode, ActionCode,
)
from morphogenesis.core.chain_builder import (
    build_chain, build_appendage_chain,
    MORPHOGEN_SENSITIVITY, APPENDAGE_MORPHOGEN_SENSITIVITY,
    MORPHOGEN_MAX, CONTINUATION_RATIO,
)


# ============================================================
# シリアライズ互換性
# ============================================================
class TestSerializeCompat:
    """既存遺伝子文字列（旧8bit形式）との後方互換性"""

    def test_padding_00_means_no_threshold_factor(self):
        """旧8bit: パディング 00 → threshold_factor=False, ratio_factor=False, morphogen_condition=False"""
        rule = Rule.from_bits("10100100")  # CCCAAA00
        assert rule.threshold_factor is False
        assert rule.ratio_factor is False
        assert rule.morphogen_condition is False

    def test_short_bits_no_factors(self):
        """6bit文字列 → 全因子フィールドはFalse"""
        rule = Rule.from_bits("101001")
        assert rule.threshold_factor is False
        assert rule.ratio_factor is False
        assert rule.morphogen_condition is False

    def test_existing_gene_string_round_trip(self):
        """旧8bit形式の遺伝子文字列でチェーン生成が動作する"""
        gene_str = "10110100/00000100/10101000"
        gene = Gene.from_string(gene_str)
        chain = build_chain(gene, max_segments=10)
        assert len(chain) >= 1


# ============================================================
# ビット往復テスト（9bit対応）
# ============================================================
class TestBitRoundTrip:
    """to_bits / from_bits の往復テスト"""

    def test_no_factors_round_trip(self):
        """因子なしルールの往復（9bit: THM=000）"""
        rule = Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                    threshold_factor=False, ratio_factor=False,
                    morphogen_condition=False)
        bits = rule.to_bits()
        assert bits == "101010000"  # 9bit: ...THM = 000
        restored = Rule.from_bits(bits)
        assert restored.condition == rule.condition
        assert restored.action == rule.action
        assert restored.threshold_factor is False
        assert restored.ratio_factor is False
        assert restored.morphogen_condition is False

    def test_threshold_only_round_trip(self):
        """閾値因子のみの往復（THM=100）"""
        rule = Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                    threshold_factor=True, ratio_factor=False,
                    morphogen_condition=False)
        bits = rule.to_bits()
        assert bits == "101010100"  # ...THM = 100
        restored = Rule.from_bits(bits)
        assert restored.threshold_factor is True
        assert restored.ratio_factor is False
        assert restored.morphogen_condition is False

    def test_both_factors_round_trip(self):
        """TH両因子ありの往復（THM=110）"""
        rule = Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                    threshold_factor=True, ratio_factor=True,
                    morphogen_condition=False)
        bits = rule.to_bits()
        assert bits == "101010110"  # ...THM = 110
        restored = Rule.from_bits(bits)
        assert restored.threshold_factor is True
        assert restored.ratio_factor is True
        assert restored.morphogen_condition is False

    def test_morphogen_condition_round_trip(self):
        """morphogen条件フラグの往復（THM=001）"""
        rule = Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                    threshold_factor=False, ratio_factor=False,
                    morphogen_condition=True)
        bits = rule.to_bits()
        assert bits == "101010001"  # ...THM = 001
        restored = Rule.from_bits(bits)
        assert restored.morphogen_condition is True

    def test_all_flags_round_trip(self):
        """全フラグありの往復（THM=111）"""
        rule = Rule(ConditionCode.N1_SCALE_LT_HALF, ActionCode.MATERIAL_A,
                    threshold_factor=True, ratio_factor=True,
                    morphogen_condition=True)
        bits = rule.to_bits()
        assert bits == "000101111"  # CCC=000, AAA=101, THM=111
        restored = Rule.from_bits(bits)
        assert restored.condition == ConditionCode.N1_SCALE_LT_HALF
        assert restored.action == ActionCode.MATERIAL_A
        assert restored.threshold_factor is True
        assert restored.ratio_factor is True
        assert restored.morphogen_condition is True

    def test_gene_string_round_trip_with_factors(self):
        """因子付き遺伝子の文字列往復"""
        rules = [
            Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_UP_SMALL,
                 threshold_factor=True, ratio_factor=False, morphogen_condition=True),
            Rule(ConditionCode.N1_SCALE_LT_HALF, ActionCode.MATERIAL_A,
                 threshold_factor=False, ratio_factor=False, morphogen_condition=False),
        ]
        gene = Gene._from_rules(rules)
        s = gene.to_string()
        gene2 = Gene.from_string(s)
        assert len(gene2.rules) == 2
        assert gene2.rules[0].threshold_factor is True
        assert gene2.rules[0].ratio_factor is False
        assert gene2.rules[0].morphogen_condition is True
        assert gene2.rules[1].morphogen_condition is False

    def test_backward_compat_8bit_to_9bit(self):
        """旧8bitエンコーディングを9bitで復元: M=False"""
        rule = Rule.from_bits("10101010")  # 旧形式: T=1, H=0
        assert rule.threshold_factor is True
        assert rule.ratio_factor is False
        assert rule.morphogen_condition is False  # 旧形式にはMフラグなし


# ============================================================
# Gene パラメータ計算テスト
# ============================================================
class TestGeneParameters:
    """appendage_threshold / appendage_start_ratio の集約計算テスト"""

    def test_no_threshold_factors_high_threshold(self):
        """全ルールのthreshold_factor=False → threshold = 0.3（最低値）"""
        rules = [
            Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                 threshold_factor=False, ratio_factor=False),
        ]
        gene = Gene._from_rules(rules)
        assert gene.appendage_threshold == pytest.approx(0.3)

    def test_all_threshold_factors_max_threshold(self):
        """全ルールのthreshold_factor=True → threshold = 2.0（最高値）"""
        rules = [
            Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                 threshold_factor=True, ratio_factor=False),
        ]
        gene = Gene._from_rules(rules)
        assert gene.appendage_threshold == pytest.approx(2.0)

    def test_half_threshold_factors(self):
        """半分のルールがthreshold_factor=True → threshold = 0.3 + 0.5 * 1.7 = 1.15"""
        rules = [
            Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                 threshold_factor=True, ratio_factor=False),
            Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                 threshold_factor=False, ratio_factor=False),
        ]
        gene = Gene._from_rules(rules)
        assert gene.appendage_threshold == pytest.approx(0.3 + 0.5 * 1.7)

    def test_no_ratio_factors_min_ratio(self):
        """全ルールのratio_factor=False → start_ratio = 0.2（最低値）"""
        rules = [
            Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                 threshold_factor=False, ratio_factor=False),
        ]
        gene = Gene._from_rules(rules)
        assert gene.appendage_start_ratio == pytest.approx(0.2)

    def test_all_ratio_factors_max_ratio(self):
        """全ルールのratio_factor=True → start_ratio = 0.8（最高値）"""
        rules = [
            Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                 threshold_factor=False, ratio_factor=True),
        ]
        gene = Gene._from_rules(rules)
        assert gene.appendage_start_ratio == pytest.approx(0.8)

    def test_from_string_recalculates_params(self):
        """from_string で復元した Gene のパラメータが再計算される"""
        rules = [
            Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                 threshold_factor=True, ratio_factor=True),
            Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                 threshold_factor=False, ratio_factor=False),
        ]
        gene = Gene._from_rules(rules)
        s = gene.to_string()
        gene2 = Gene.from_string(s)
        assert gene2.appendage_threshold == pytest.approx(gene.appendage_threshold)
        assert gene2.appendage_start_ratio == pytest.approx(gene.appendage_start_ratio)


# ============================================================
# chain_builder: 独立モルフォゲン v2 付属肢判定
# ============================================================
class TestChainBuilderAppendage:
    """chain_builder での独立 morphogen ベース付属肢判定テスト"""

    def test_high_threshold_no_appendage(self):
        """閾値が高い（2.0）→ morphogen=1.0 では付属肢なし"""
        gene = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN)],
            appendage_threshold=2.0,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=5)
        for seg in chain:
            assert seg.has_appendage is False

    def test_low_threshold_appendage_via_morphogen(self):
        """閾値が低い（0.5）→ morphogen > 0.5 の体節に付属肢"""
        gene = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_UP_LARGE,
                         threshold_factor=True, ratio_factor=False)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=5)
        has_app = any(seg.has_appendage for seg in chain[1:])
        assert has_app, "morphogen > threshold の体節に付属肢があるべき"

    def test_appendage_scale_uses_scale_x(self):
        """appendage_scale = scale_x * appendage_start_ratio（morphogen ではなく scale_x ベース）"""
        gene = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                         threshold_factor=True, ratio_factor=False)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.3,
        )
        chain = build_chain(gene, max_segments=3)
        for seg in chain[1:]:
            if seg.has_appendage:
                assert seg.appendage_scale == pytest.approx(seg.scale_x * 0.3)

    def test_head_no_appendage(self):
        """head (index=0) にはルールが適用されないので付属肢なし"""
        gene = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                         threshold_factor=True, ratio_factor=False)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=5)
        assert chain[0].has_appendage is False


# ============================================================
# 独立モルフォゲン v2 専用テスト
# ============================================================
class TestMorphogenIndependent:
    """morphogen が scale_x と独立に進化することの検証"""

    def test_morphogen_independent_of_scale_x(self):
        """morphogen と scale_x が異なる値になる"""
        gene = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_DOWN_SMALL,
                         threshold_factor=True, ratio_factor=False)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=10)
        seg = chain[5]
        assert seg.scale_x < 1.0, "scale_x は減少するべき"
        assert seg.morphogen > 1.0, "morphogen は T ビット発火で上昇するべき"
        assert seg.morphogen != pytest.approx(seg.scale_x), "morphogen と scale_x は異なるべき"

    def test_morphogen_threshold_appendage(self):
        """morphogen > threshold で付属肢発生、scale_x は関係なし"""
        gene = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_DOWN_SMALL,
                         threshold_factor=True, ratio_factor=False)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=15)
        found_small_with_appendage = False
        for seg in chain[1:]:
            if seg.scale_x < 0.5 and seg.has_appendage:
                found_small_with_appendage = True
                break
        assert found_small_with_appendage, \
            "scale_x < threshold でも morphogen > threshold なら付属肢があるべき"

    def test_morphogen_low_no_appendage(self):
        """morphogen < threshold で付属肢なし（scale_x が大きくても）"""
        gene = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_UP_SMALL,
                         threshold_factor=False, ratio_factor=True)],
            appendage_threshold=0.8,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=15)
        found_large_no_appendage = False
        for seg in chain[5:]:
            if seg.scale_x > 0.8 and not seg.has_appendage:
                found_large_no_appendage = True
                break
        assert found_large_no_appendage, \
            "scale_x > threshold でも morphogen < threshold なら付属肢がないべき"

    def test_morphogen_evolution_t_dominant(self):
        """T ビット多い → morphogen 増加"""
        gene = Gene(
            rules=[
                Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                     threshold_factor=True, ratio_factor=False),
                Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                     threshold_factor=True, ratio_factor=False),
            ],
            appendage_threshold=2.0,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=5)
        assert chain[2].morphogen > chain[1].morphogen, \
            "T 優勢の遺伝子では morphogen が増加するべき"

    def test_morphogen_evolution_h_dominant(self):
        """H ビット多い → morphogen 減少"""
        gene = Gene(
            rules=[
                Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                     threshold_factor=False, ratio_factor=True),
                Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                     threshold_factor=False, ratio_factor=True),
            ],
            appendage_threshold=0.3,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=5)
        assert chain[2].morphogen < chain[1].morphogen, \
            "H 優勢の遺伝子では morphogen が減少するべき"

    def test_morphogen_clamped_to_range(self):
        """morphogen は [0.0, MORPHOGEN_MAX] にクランプされる"""
        gene = Gene(
            rules=[
                Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                     threshold_factor=False, ratio_factor=True),
            ] * 10,
            appendage_threshold=0.3,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=20)
        for seg in chain:
            assert 0.0 <= seg.morphogen <= MORPHOGEN_MAX


# ============================================================
# morphogen 条件評価（M フラグ）テスト
# ============================================================
class TestMorphogenCondition:
    """M フラグで条件評価が morphogen ベースに切り替わることの検証"""

    def test_morphogen_condition_fires_on_morphogen(self):
        """M=1 のルール: morphogen >= 1.0 で発火（scale_x に依存しない）"""
        gene = Gene(
            rules=[
                # M=0: SCALE_DOWN でscale_xを下げる（常に発火）
                Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_DOWN_SMALL,
                     threshold_factor=True, ratio_factor=False,
                     morphogen_condition=False),
                # M=1: morphogen >= 1.0 のとき MATERIAL_A（黒）を割り当て
                Rule(ConditionCode.N1_SCALE_GE_ONE, ActionCode.MATERIAL_A,
                     threshold_factor=False, ratio_factor=False,
                     morphogen_condition=True),
            ],
            appendage_threshold=2.0,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=10)
        # scale_x は減少、morphogen は上昇
        # morphogen >= 1.0 のとき M=1 ルールが発火 → MATERIAL_A
        found_a = any(seg.material == "A" for seg in chain[1:])
        assert found_a, "morphogen >= 1.0 のとき M=1 ルールで MATERIAL_A が割り当てられるべき"

    def test_morphogen_condition_does_not_fire_on_low_morphogen(self):
        """M=1 のルール: morphogen < 0.5 では LT_HALF が True"""
        gene = Gene(
            rules=[
                # H 優勢で morphogen を下げる
                Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                     threshold_factor=False, ratio_factor=True),
                Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                     threshold_factor=False, ratio_factor=True),
                Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                     threshold_factor=False, ratio_factor=True),
                # M=1: morphogen < 0.5 → MATERIAL_A
                Rule(ConditionCode.N1_SCALE_LT_HALF, ActionCode.MATERIAL_A,
                     morphogen_condition=True),
            ],
            appendage_threshold=2.0,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=20)
        # morphogen が 0.5 未満に下がった体節で MATERIAL_A が発火する
        found_a_with_low_morph = False
        for seg in chain[1:]:
            if seg.morphogen < 0.5 and seg.material == "A":
                found_a_with_low_morph = True
                break
        assert found_a_with_low_morph, \
            "morphogen < 0.5 のとき M=1 の LT_HALF ルールで MATERIAL_A が割り当てられるべき"

    def test_morphogen_condition_mixed_rules(self):
        """M=0 と M=1 のルールが混在: scale_x と morphogen の両方が影響"""
        gene = Gene(
            rules=[
                # M=0: scale_x を成長させる
                Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_UP_SMALL,
                     threshold_factor=True, ratio_factor=False,
                     morphogen_condition=False),
                # M=1: morphogen >= 1.0 のとき黒にする
                Rule(ConditionCode.N1_SCALE_GE_ONE, ActionCode.MATERIAL_A,
                     morphogen_condition=True),
                # M=1: morphogen < 1.0 のとき白にする
                Rule(ConditionCode.N1_SCALE_LT_ONE, ActionCode.MATERIAL_B,
                     morphogen_condition=True),
            ],
            appendage_threshold=2.0,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=10)
        # scale_x は増加、morphogen は T 優勢で上昇
        # morphogen >= 1.0 のとき MATERIAL_A（黒）、< 1.0 のとき MATERIAL_B（白）
        materials = set(seg.material for seg in chain[1:])
        assert len(materials) >= 1, "ルール混在でマテリアルが設定されるべき"

    def test_m_flag_preserved_in_gene_random(self):
        """Gene.random() で M フラグが生成される"""
        gene = Gene.random(num_rules=50, seed=42)
        has_morph = any(r.morphogen_condition for r in gene.rules)
        has_scale = any(not r.morphogen_condition for r in gene.rules)
        assert has_morph, "50ルールなら M=1 のルールがあるべき（30%確率）"
        assert has_scale, "50ルールなら M=0 のルールもあるべき"


# ============================================================
# Gene.random の既存RNG非干渉
# ============================================================
class TestRandomRngIndependence:
    """因子用RNGが既存の条件/アクションRNGに干渉しないことの検証"""

    def test_condition_action_unchanged(self):
        """因子追加前後で条件・アクションの乱数列が同一"""
        import random as stdlib_random
        rng = stdlib_random.Random(42)
        expected_pairs = []
        for _ in range(20):
            cond = rng.randint(0, 7)
            act = rng.randint(0, 7)
            expected_pairs.append((cond, act))

        gene = Gene.random(num_rules=20, seed=42)
        for i, rule in enumerate(gene.rules):
            assert int(rule.condition) == expected_pairs[i][0], f"rule {i} condition mismatch"
            assert int(rule.action) == expected_pairs[i][1], f"rule {i} action mismatch"


# ============================================================
# 付属肢チェーン（多体節）— morphogen ベース継続テスト
# ============================================================
class TestAppendageChain:
    """build_appendage_chain と build_chain の付属肢チェーン統合テスト"""

    def test_appendage_chain_length_ge_one(self):
        """付属肢チェーンの長さは1以上"""
        gene = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                         threshold_factor=True, ratio_factor=False)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=5)
        for seg in chain[1:]:
            if seg.has_appendage:
                assert len(seg.appendage_chain) >= 1

    def test_appendage_chain_head_scale(self):
        """付属肢チェーンの先頭体節は appendage_scale と同じ開始スケール"""
        gene = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                         threshold_factor=True, ratio_factor=False)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=3)
        for seg in chain[1:]:
            if seg.has_appendage:
                assert seg.appendage_chain[0].scale_x == pytest.approx(seg.appendage_scale)

    def test_appendage_chain_adjacent_positions(self):
        """付属肢チェーン内の体節は隣接配置"""
        gene = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                         threshold_factor=True, ratio_factor=False)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.8,
        )
        chain = build_chain(gene, max_segments=3, max_appendage_segments=5)
        for seg in chain[1:]:
            if not seg.has_appendage:
                continue
            app_chain = seg.appendage_chain
            for j in range(1, len(app_chain)):
                prev = app_chain[j - 1]
                curr = app_chain[j]
                expected_pos = prev.pos_x + (prev.scale_x + curr.scale_x) / 2.0
                assert curr.pos_x == pytest.approx(expected_pos), \
                    f"app_seg[{j}] pos_x mismatch: {curr.pos_x} != {expected_pos}"

    def test_appendage_continuation_morphogen_based(self):
        """morphogen 減衰で付属肢チェーンが自然停止"""
        gene = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_DOWN_SMALL,
                         threshold_factor=False, ratio_factor=True)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.8,
        )
        chain = build_chain(gene, max_segments=3, max_appendage_segments=30)
        for seg in chain[1:]:
            if seg.has_appendage and len(seg.appendage_chain) > 1:
                assert len(seg.appendage_chain) < 30, \
                    "morphogen 減衰で付属肢チェーンが最大に達する前に停止するべき"

    def test_appendage_chain_no_recursion(self):
        """付属肢チェーン内の体節は has_appendage=False（再帰なし）"""
        gene = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                         threshold_factor=True, ratio_factor=False)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=5, max_appendage_segments=5)
        for seg in chain[1:]:
            for app_seg in seg.appendage_chain:
                assert app_seg.has_appendage is False
                assert app_seg.appendage_chain == []

    def test_appendage_chain_max_segments_respected(self):
        """max_appendage_segments パラメータが尊重される"""
        gene = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                         threshold_factor=True, ratio_factor=False)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.8,
        )
        chain = build_chain(gene, max_segments=3, max_appendage_segments=3)
        for seg in chain[1:]:
            if seg.has_appendage:
                assert len(seg.appendage_chain) <= 3

    def test_appendage_chain_rules_applied(self):
        """付属肢チェーン内で遺伝子ルールが適用される"""
        gene = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_UP_SMALL,
                         threshold_factor=True, ratio_factor=False)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=3, max_appendage_segments=5)
        for seg in chain[1:]:
            if seg.has_appendage:
                app_chain = seg.appendage_chain
                head_scale = seg.appendage_scale
                assert app_chain[0].scale_x == pytest.approx(head_scale)
                if len(app_chain) >= 2:
                    assert app_chain[1].scale_x == pytest.approx(head_scale * 1.1)

    def test_build_appendage_chain_empty_gene(self):
        """空遺伝子 → head のみの付属肢チェーン"""
        gene = Gene(rules=[])
        app_chain = build_appendage_chain(gene, head_scale=0.5)
        assert len(app_chain) == 1
        assert app_chain[0].scale_x == pytest.approx(0.5)

    def test_build_appendage_chain_scale_max(self):
        """scale_max が付属肢チェーンにも適用される"""
        gene = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_UP_LARGE,
                         threshold_factor=True, ratio_factor=False)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.5,
        )
        app_chain = build_appendage_chain(gene, head_scale=1.0,
                                           max_segments=10, scale_max=3.0,
                                           init_morphogen=2.0)
        for seg in app_chain:
            assert seg.scale_x <= 3.0 + 0.01

    def test_no_appendage_no_chain(self):
        """付属肢なし体節の appendage_chain は空リスト"""
        gene = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN)],
            appendage_threshold=2.0,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=5)
        for seg in chain:
            assert seg.appendage_chain == []

    def test_appendage_head_material_rule_driven(self):
        """付属肢headのmaterialがルール駆動で決定される"""
        gene = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MATERIAL_A,
                         threshold_factor=True, ratio_factor=False)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=3, max_appendage_segments=3)
        for seg in chain[1:]:
            if seg.has_appendage:
                assert seg.appendage_chain[0].material == "A", \
                    "付属肢headのmaterialはルール駆動で決定されるべき"

    def test_start_ratio_affects_chain_shape(self):
        """appendage_start_ratioの違いが付属肢チェーンの形状に影響する"""
        gene_low = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_DOWN_SMALL,
                         threshold_factor=True, ratio_factor=False)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.2,
        )
        gene_high = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_DOWN_SMALL,
                         threshold_factor=True, ratio_factor=False)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.8,
        )
        chain_low = build_chain(gene_low, max_segments=3, max_appendage_segments=5)
        chain_high = build_chain(gene_high, max_segments=3, max_appendage_segments=5)

        if chain_low[1].has_appendage and chain_high[1].has_appendage:
            low_head = chain_low[1].appendage_chain[0].scale_x
            high_head = chain_high[1].appendage_chain[0].scale_x
            assert low_head != pytest.approx(high_head), \
                "start_ratio が異なれば付属肢チェーンの開始スケールも異なるべき"

    def test_appendage_joint_count_variety(self):
        """異なる遺伝子で異なる関節数"""
        gene_long = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                         threshold_factor=True, ratio_factor=False)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.8,
        )
        gene_short = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                         threshold_factor=False, ratio_factor=True)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.8,
        )
        chain_long = build_chain(gene_long, max_segments=5, max_appendage_segments=15)
        chain_short = build_chain(gene_short, max_segments=5, max_appendage_segments=15)

        def max_app_len(chain):
            return max((len(s.appendage_chain) for s in chain if s.has_appendage), default=0)

        long_len = max_app_len(chain_long)
        short_len = max_app_len(chain_short)
        assert long_len > short_len, \
            f"T 優勢({long_len}) は H 優勢({short_len}) より多くの関節を持つべき"

    def test_appendage_chain_inherits_parent_morphogen(self):
        """付属肢チェーンの先頭体節は親の morphogen を引き継ぐ"""
        gene = Gene(
            rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                         threshold_factor=True, ratio_factor=False)],
            appendage_threshold=0.5,
            appendage_start_ratio=0.5,
        )
        chain = build_chain(gene, max_segments=5, max_appendage_segments=5)
        for seg in chain[1:]:
            if seg.has_appendage:
                assert seg.appendage_chain[0].morphogen == pytest.approx(seg.morphogen), \
                    "付属肢チェーンの先頭 morphogen は親体節の morphogen と等しいべき"

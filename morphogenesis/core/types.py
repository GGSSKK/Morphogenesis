"""遺伝子駆動パターン生成の型定義（独立モルフォゲン v2）

体節チェーンの遺伝子表現: 条件コード(8種) x アクションコード(8種) のルール配列。
各ルールは9bitバイナリ文字列としてシリアライズ可能（旧8bitも後方互換で読み込み可）。
"""
from enum import IntEnum
from dataclasses import dataclass, field
import random

# --- 定数 ---
SCALE_MIN = 0.05
SCALE_MAX = 8.0
TOLERANCE = 0.01


class ConditionCode(IntEnum):
    """条件コード（8種）

    N-1, N-2 体節の scaleX（またはmorphogen: M=1時）を参照して真偽を返す。
    M(morphogen_condition)フラグが True の場合、scale_x の代わりに morphogen 値で評価する。
    """
    N1_SCALE_LT_HALF = 0      # val < 0.5
    N1_SCALE_GE_HALF = 1      # val >= 0.5
    N1_SCALE_LT_N2 = 2        # N-1.val < N-2.val
    N1_SCALE_GT_N2 = 3        # N-1.val > N-2.val
    N1_SCALE_EQ_N2 = 4        # N-1.val == N-2.val (許容誤差付き)
    ALWAYS_TRUE = 5            # 常にTRUE
    N1_SCALE_LT_ONE = 6       # val < 1.0
    N1_SCALE_GE_ONE = 7       # val >= 1.0


class ActionCode(IntEnum):
    """アクションコード（8種）

    体節の scaleX やマテリアルを変更する。
    TERMINATE は体節数 >= 15 のときのみ発動。
    """
    SCALE_DOWN_SMALL = 0   # scaleX *= 0.9
    SCALE_UP_SMALL = 1     # scaleX *= 1.1
    MAINTAIN = 2           # 維持（no-op）
    SCALE_UP_LARGE = 3     # scaleX *= 2.0
    SCALE_DOWN_LARGE = 4   # scaleX *= 0.5
    MATERIAL_A = 5         # マテリアルA
    MATERIAL_B = 6         # マテリアルB
    TERMINATE = 7          # 終了（体節数 >= 15 のみ）


@dataclass
class Rule:
    """単一ルール = 条件 + アクション + 閾値/比率因子 + morphogen条件フラグ

    Bit 6 (T): 遺伝子全体で集約 → appendage_threshold（付属肢発生閾値）
    Bit 7 (H): 遺伝子全体で集約 → appendage_start_ratio（付属肢開始スケール比率）
    Bit 8 (M): morphogen条件フラグ — True のとき条件を morphogen 値で評価
    """
    condition: ConditionCode
    action: ActionCode
    threshold_factor: bool = False        # Bit 6 — 集約→appendage_threshold
    ratio_factor: bool = False            # Bit 7 — 集約→appendage_start_ratio
    morphogen_condition: bool = False     # Bit 8 — morphogen ベース条件評価

    def to_bits(self) -> str:
        """9bitバイナリ文字列に変換（条件3bit + アクション3bit + T1bit + H1bit + M1bit）

        CCCAAATHM: C=条件, A=アクション, T=閾値因子, H=比率因子, M=morphogen条件
        """
        t = 1 if self.threshold_factor else 0
        h = 1 if self.ratio_factor else 0
        m = 1 if self.morphogen_condition else 0
        return f"{self.condition:03b}{self.action:03b}{t}{h}{m}"

    @classmethod
    def from_bits(cls, bits: str) -> "Rule":
        """8/9bitバイナリ文字列からルールを復元（旧8bit形式も後方互換で読み込み）"""
        cond = int(bits[:3], 2)
        act = int(bits[3:6], 2)
        threshold_factor = bool(int(bits[6])) if len(bits) > 6 else False
        ratio_factor = bool(int(bits[7])) if len(bits) > 7 else False
        morphogen_condition = bool(int(bits[8])) if len(bits) > 8 else False
        return cls(ConditionCode(cond), ActionCode(act),
                   threshold_factor, ratio_factor, morphogen_condition)


@dataclass
class Gene:
    """遺伝子 = ルールの配列 + モルフォゲン濃度パラメータ

    チェーン生成時、全ルールが各体節に順次適用される。
    appendage_threshold: 体節のscale_xがこの値を超えたら付属肢を発生
    appendage_start_ratio: 付属肢の開始スケール = 親scale_x × この比率
    """
    rules: list[Rule]
    appendage_threshold: float = 1.0
    appendage_start_ratio: float = 0.5

    @classmethod
    def _from_rules(cls, rules: list["Rule"]) -> "Gene":
        """ルール配列からbit集約でパラメータを計算してGeneを構築"""
        n = max(len(rules), 1)
        t_ratio = sum(1 for r in rules if r.threshold_factor) / n
        h_ratio = sum(1 for r in rules if r.ratio_factor) / n
        return cls(
            rules=rules,
            appendage_threshold=0.3 + t_ratio * 1.7,   # 範囲: 0.3〜2.0
            appendage_start_ratio=0.2 + h_ratio * 0.6,  # 範囲: 0.2〜0.8
        )

    @classmethod
    def random(cls, num_rules: int = 20, seed: int = 42) -> "Gene":
        """ランダム遺伝子生成

        Args:
            num_rules: ルール数
            seed: 乱数シード（再現性保証）
        """
        rng = random.Random(seed)
        rng_th = random.Random(seed + 1_000_000)  # 閾値/比率因子用独立RNG
        rng_morph = random.Random(seed + 2_000_000)  # morphogen条件フラグ用独立RNG
        rules = []
        for _ in range(num_rules):
            cond = ConditionCode(rng.randint(0, 7))
            act = ActionCode(rng.randint(0, 7))
            threshold_factor = rng_th.random() < 0.3
            ratio_factor = rng_th.random() < 0.5
            morphogen_condition = rng_morph.random() < 0.3  # 30% がmorphogen条件
            rules.append(Rule(cond, act, threshold_factor, ratio_factor, morphogen_condition))
        return cls._from_rules(rules)

    def to_string(self) -> str:
        """遺伝子を文字列表現に変換（'/'区切り）"""
        return "/".join(r.to_bits() for r in self.rules)

    @classmethod
    def from_string(cls, s: str) -> "Gene":
        """文字列から遺伝子を復元（bit集約でパラメータ再計算）"""
        if not s:
            return cls([])
        parts = s.split("/")
        rules = [Rule.from_bits(p) for p in parts]
        return cls._from_rules(rules)


@dataclass
class Segment:
    """体節データ

    チェーン内の1体節を表す。index はチェーン内の位置（0始点）。
    morphogen は scale_x とは独立に進化する不可視の濃度（付属肢発生判定に使用）。
    appendage_chain は付属肢チェーン（list[Segment]）。再帰なし（付属肢内の体節は更にサブ付属肢を持たない）。
    """
    index: int
    scale_x: float = 1.0
    morphogen: float = 1.0   # 独立モルフォゲン濃度（scale_x とは脱結合）
    pos_x: float = 0.0
    material: str = "default"  # "default" / "A"
    terminated: bool = False
    has_appendage: bool = False
    appendage_scale: float = 0.5
    appendage_chain: list = field(default_factory=list)  # list[Segment]

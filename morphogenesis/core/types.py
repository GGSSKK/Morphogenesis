"""遺伝子駆動パターン生成の型定義（02Test準拠）

体節チェーンの遺伝子表現: 条件コード(8種) x アクションコード(8種) のルール配列。
各ルールは8bitバイナリ文字列としてシリアライズ可能。
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

    N-1, N-2 体節の scaleX を参照して真偽を返す。
    """
    N1_SCALE_LT_HALF = 0      # N-1.scaleX < 0.5
    N1_SCALE_GE_HALF = 1      # N-1.scaleX >= 0.5
    N1_SCALE_LT_N2 = 2        # N-1.scaleX < N-2.scaleX
    N1_SCALE_GT_N2 = 3        # N-1.scaleX > N-2.scaleX
    N1_SCALE_EQ_N2 = 4        # N-1.scaleX == N-2.scaleX (許容誤差付き)
    ALWAYS_TRUE = 5            # 常にTRUE
    N1_SCALE_LT_ONE = 6       # N-1.scaleX < 1.0
    N1_SCALE_GE_ONE = 7       # N-1.scaleX >= 1.0


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
    """単一ルール = 条件 + アクション"""
    condition: ConditionCode
    action: ActionCode

    def to_bits(self) -> str:
        """8bitバイナリ文字列に変換（条件3bit + アクション3bit + パディング2bit）

        表示・シリアライズ用途。各コードは0-7の3bit範囲。
        """
        return f"{self.condition:03b}{self.action:03b}00"

    @classmethod
    def from_bits(cls, bits: str) -> "Rule":
        """8bitバイナリ文字列からルールを復元"""
        cond = int(bits[:3], 2)
        act = int(bits[3:6], 2)
        return cls(ConditionCode(cond), ActionCode(act))


@dataclass
class Gene:
    """遺伝子 = ルールの配列

    チェーン生成時、全ルールが各体節に順次適用される。
    """
    rules: list[Rule]

    @classmethod
    def random(cls, num_rules: int = 20, seed: int = 42) -> "Gene":
        """ランダム遺伝子生成

        Args:
            num_rules: ルール数
            seed: 乱数シード（再現性保証）
        """
        rng = random.Random(seed)
        rules = []
        for _ in range(num_rules):
            cond = ConditionCode(rng.randint(0, 7))
            act = ActionCode(rng.randint(0, 7))
            rules.append(Rule(cond, act))
        return cls(rules)

    def to_string(self) -> str:
        """遺伝子を文字列表現に変換（'/'区切り）"""
        return "/".join(r.to_bits() for r in self.rules)

    @classmethod
    def from_string(cls, s: str) -> "Gene":
        """文字列から遺伝子を復元"""
        if not s:
            return cls([])
        parts = s.split("/")
        return cls([Rule.from_bits(p) for p in parts])


@dataclass
class Segment:
    """体節データ

    チェーン内の1体節を表す。index はチェーン内の位置（0始点）。
    """
    index: int
    scale_x: float = 1.0
    pos_x: float = 0.0
    material: str = "default"  # "default" / "A" / "B"
    terminated: bool = False

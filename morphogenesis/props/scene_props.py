"""シーンプロパティ — update コールバックによる即時再生成"""
import bpy
from bpy.props import IntProperty, FloatProperty, StringProperty, EnumProperty


def _on_param_change(self, context):
    """パラメータ変更時に自動再生成（Seedスライダードラッグで即時反映）"""
    if self.get("_updating"):
        return
    self["_updating"] = True
    try:
        self.gene_string = ""
        bpy.ops.morpho.generate()
    finally:
        self["_updating"] = False


class MorphoProperties(bpy.types.PropertyGroup):
    """Morphogenesis シーンプロパティ"""

    seed: IntProperty(
        name="Seed",
        description="乱数シード値。変更すると異なる遺伝子パターンが生成される",
        default=42,
        min=0,
        max=99999,
        update=_on_param_change,
    )

    rule_count: IntProperty(
        name="Rules",
        description="遺伝子ルールの数。多いほど複雑なパターンになる",
        default=20,
        min=1,
        max=50,
        update=_on_param_change,
    )

    max_segments: IntProperty(
        name="Max Segments",
        description="生成される体節の最大数",
        default=30,
        min=5,
        max=100,
        update=_on_param_change,
    )

    mesh_type: EnumProperty(
        name="Mesh Type",
        description="各体節のメッシュ形状",
        items=[
            ("CUBE", "Cube", "立方体"),
            ("SPHERE", "Sphere", "球"),
            ("CYLINDER", "Cylinder", "円柱"),
            ("CONE", "Cone", "円錐"),
        ],
        default="SPHERE",
        update=_on_param_change,
    )

    scale_axis: EnumProperty(
        name="Scale Axis",
        description="遺伝子によるスケール変化を適用する軸",
        items=[
            ("X", "X", "X軸方向にスケール変化（横に伸縮）"),
            ("Y", "Y", "Y軸方向にスケール変化（縦に伸縮）"),
        ],
        default="Y",
        update=_on_param_change,
    )

    segment_max_scale: FloatProperty(
        name="Max Scale",
        description="遺伝子によるスケール変化の上限値。大きいほどダイナミックな形状になる",
        default=8.0,
        min=0.5,
        max=20.0,
        update=_on_param_change,
    )

    segment_uniform_scale: FloatProperty(
        name="Uniform Scale",
        description="スケール変化しない軸のスケール値",
        default=1.0,
        min=0.1,
        max=5.0,
        update=_on_param_change,
    )

    max_appendage_segments: IntProperty(
        name="Max Appendage Segs",
        description="付属肢チェーンの最大体節数",
        default=15,
        min=1,
        max=30,
        update=_on_param_change,
    )

    gene_string: StringProperty(
        name="Gene",
        description="現在の遺伝子文字列（自動生成）",
        default="",
    )

    segment_count: IntProperty(
        name="Segments",
        description="生成された体節数",
        default=0,
    )

    appendage_count: IntProperty(
        name="Appendages",
        description="付属肢のある体節数",
        default=0,
    )

"""生成オペレーター — 遺伝子文字列または現在のパラメータからクリーチャーを生成"""
import bpy
from ..core.types import Gene
from ..core.chain_builder import build_chain
from ..gn.chain_to_gn import build_gn_tree
from ..gn import geonodes_utils as gn
from ..gn.materials import get_or_create_material


OBJ_NAME = "Morpho_Creature"


def _ensure_material_slots(obj):
    """オブジェクトのマテリアルスロットに Morpho マテリアルを登録

    GN SetMaterial で使うマテリアルを事前にスロットに追加しておく。
    """
    for mat_key in ("default", "A", "B"):
        mat = get_or_create_material(mat_key)
        # 既にスロットにあるか確認
        found = False
        for slot in obj.material_slots:
            if slot.material and slot.material.name == mat.name:
                found = True
                break
        if not found:
            obj.data.materials.append(mat)


def _setup_viewport_for_materials(context):
    """ビューポートをマテリアル表示に設定（Solidモードで色を表示するため）"""
    for area in context.screen.areas if context.screen else []:
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    # Solid モードの場合、カラータイプを MATERIAL に設定
                    if space.shading.type == "SOLID":
                        space.shading.color_type = "MATERIAL"


class MORPHO_OT_Generate(bpy.types.Operator):
    """遺伝子からクリーチャーを生成"""
    bl_idname = "morpho.generate"
    bl_label = "Generate"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.morpho_props

        # 遺伝子生成
        if props.gene_string:
            gene = Gene.from_string(props.gene_string)
        else:
            gene = Gene.random(num_rules=props.rule_count, seed=props.seed)

        # チェーン生成
        chain = build_chain(
            gene,
            max_segments=props.max_segments,
            scale_max=props.segment_max_scale,
        )

        # GNツリー構築（軸選択と均一スケールを渡す）
        tree = build_gn_tree(
            chain,
            mesh_type=props.mesh_type,
            scale_axis=props.scale_axis,
            uniform_scale=props.segment_uniform_scale,
        )

        # デフォルトキューブを削除（初回生成時）
        default_cube = bpy.data.objects.get("Cube")
        if default_cube is not None:
            bpy.data.objects.remove(default_cube, do_unlink=True)

        # オブジェクト取得 or 作成
        obj = bpy.data.objects.get(OBJ_NAME)
        if obj is None:
            mesh = bpy.data.meshes.new(OBJ_NAME)
            obj = bpy.data.objects.new(OBJ_NAME, mesh)
            context.collection.objects.link(obj)

        # マテリアルスロットにマテリアルを登録（GN SetMaterial用）
        _ensure_material_slots(obj)

        # 既存GNモディファイアを更新（古い無効モディファイアもクリーンアップ）
        mod = None
        stale_mods = []
        for m in obj.modifiers:
            if m.type == "NODES":
                if m.node_group and m.node_group.name.startswith("Morpho"):
                    mod = m
                elif m.node_group is None:
                    stale_mods.append(m)

        # 古い無効モディファイアを削除
        for m in stale_mods:
            obj.modifiers.remove(m)

        if mod is None:
            gn.apply_geonodes_modifier(obj, tree)
        else:
            mod.node_group = tree

        # プロパティ更新
        props.gene_string = gene.to_string()
        props.segment_count = len(chain)

        # ビューポート更新
        context.view_layer.update()

        # ビューポートをマテリアル表示に設定
        _setup_viewport_for_materials(context)

        return {"FINISHED"}

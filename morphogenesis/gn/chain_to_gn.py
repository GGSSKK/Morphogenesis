"""チェーン→GNツリー変換

各体節を MeshPrimitive + Transform + SetMaterial で配置し、
JoinGeometry で結合するGNツリーを構築。
"""
import math
import bpy
from ..core.types import Segment
from . import geonodes_utils as gn
from .materials import get_or_create_material

# 球/円柱/円錐はデフォルトでZ軸方向 → Y軸90°回転でX軸方向に向ける
_ROT_Y_90 = (0.0, math.pi / 2, 0.0)

# メッシュ生成関数のマッピング
MESH_CREATORS = {
    "CUBE": lambda tree, loc: gn.mesh_cube(tree, location=loc),
    "SPHERE": lambda tree, loc: gn.mesh_uv_sphere(tree, location=loc),
    "CYLINDER": lambda tree, loc: gn.mesh_cylinder(tree, location=loc),
    "CONE": lambda tree, loc: gn.mesh_cone(tree, location=loc),
}

# 回転が必要なメッシュタイプ（極がX軸=関節方向を向くように）
_NEEDS_ROTATION = {"SPHERE", "CYLINDER", "CONE"}

TREE_NAME = "Morpho_GN"


def _compute_positions(chain: list[Segment], scale_axis: str,
                       uniform_scale: float) -> list[float]:
    """各体節のX軸配置位置を計算（隣接配置保証）

    scale_axis に関わらず、実際のX方向寸法に基づいて隙間なく配置する。
    """
    positions = [0.0]  # 先頭は原点

    for i in range(1, len(chain)):
        prev_seg = chain[i - 1]
        curr_seg = chain[i]

        # 各体節の実際のX方向サイズ
        if scale_axis == "X":
            prev_x_size = prev_seg.scale_x
            curr_x_size = curr_seg.scale_x
        else:  # "Y" — X方向は全て uniform_scale
            prev_x_size = uniform_scale
            curr_x_size = uniform_scale

        # 隣接配置: 前の右端 + 自分の左端 = 隙間なし
        positions.append(positions[-1] + (prev_x_size + curr_x_size) / 2.0)

    return positions


def build_gn_tree(chain: list[Segment], mesh_type: str = "CUBE",
                   scale_axis: str = "X",
                   uniform_scale: float = 1.0) -> bpy.types.GeometryNodeTree:
    """チェーン結果からGNツリーを構築

    Args:
        chain: build_chain() の出力
        mesh_type: "CUBE" / "SPHERE" / "CYLINDER" / "CONE"
        scale_axis: 遺伝子スケール変化の軸 ("X" or "Y")
        uniform_scale: スケール変化しない軸の値

    Returns:
        構築済みGeometryNodeTree
    """
    # 既存ツリーがあれば削除して再構築
    existing = bpy.data.node_groups.get(TREE_NAME)
    if existing:
        bpy.data.node_groups.remove(existing)

    tree = gn.create_node_group(TREE_NAME)
    group_out = gn.get_group_output(tree)
    group_out.location = (1000, 0)

    if not chain:
        return tree

    # マテリアル取得
    materials = {
        "default": get_or_create_material("default"),
        "A": get_or_create_material("A"),
        "B": get_or_create_material("B"),
    }

    mesh_creator = MESH_CREATORS.get(mesh_type, MESH_CREATORS["CUBE"])

    # 実際のX寸法に基づく配置位置を計算
    positions = _compute_positions(chain, scale_axis, uniform_scale)

    # 各体節のジオメトリソケットを収集
    geo_sockets = []

    for i, seg in enumerate(chain):
        y_offset = -i * 200  # ノードを縦に並べる

        # メッシュプリミティブ生成
        _, mesh_out = mesh_creator(tree, (-600, y_offset))

        # 球/円柱/円錐: 極がX軸（関節方向）を向くようにY軸90°回転
        if mesh_type in _NEEDS_ROTATION:
            _, rot_vec = gn.combine_xyz(
                tree, x=_ROT_Y_90[0], y=_ROT_Y_90[1], z=_ROT_Y_90[2],
                location=(-400, y_offset - 50))
            rot_node = gn.add_node(tree, "FunctionNodeEulerToRotation",
                                    location=(-300, y_offset - 50))
            gn.link(tree, rot_vec, rot_node.inputs["Euler"])
            _, mesh_out = gn.transform(
                tree, mesh_out, rotation=rot_node.outputs["Rotation"],
                location=(-200, y_offset))

        # スケールベクター: 遺伝子変化軸にseg.scale_x、他軸にuniform_scaleを適用
        if scale_axis == "X":
            sx, sy, sz = seg.scale_x, uniform_scale, uniform_scale
        else:  # "Y" — Y軸のみ変化、Z軸はuniform_scale
            sx, sy, sz = uniform_scale, seg.scale_x, uniform_scale

        _, scale_vec = gn.combine_xyz(
            tree, x=sx, y=sy, z=sz,
            location=(0, y_offset - 50))
        _, pos_vec = gn.combine_xyz(
            tree, x=positions[i], y=0.0, z=0.0,
            location=(0, y_offset + 50))
        _, tf_out = gn.transform(
            tree, mesh_out, translation=pos_vec, scale=scale_vec,
            location=(200, y_offset))

        # マテリアル割当
        mat = materials.get(seg.material, materials["default"])
        _, mat_out = gn.set_material(
            tree, tf_out, mat,
            location=(400, y_offset))

        geo_sockets.append(mat_out)

    # 全体節を結合
    if len(geo_sockets) == 1:
        gn.link(tree, geo_sockets[0], group_out.inputs["Geometry"])
    else:
        _, joined = gn.join_geometry(
            tree, *geo_sockets,
            location=(700, 0))
        gn.link(tree, joined, group_out.inputs["Geometry"])

    return tree

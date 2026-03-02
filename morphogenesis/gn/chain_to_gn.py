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

# 付属肢用: Z軸→Y軸回転（極/軸がY方向を向く）
_ROT_X_90 = (math.pi / 2, 0.0, 0.0)

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

# --- 付属肢サイズパラメータ ---
_APP_MAX_LENGTH_MULT = 100.0      # morphogen 最大時の長さ倍率
_APP_MAX_THICK_MULT = 5.0         # morphogen 最大時の太さ倍率
_APP_MORPHOGEN_REF = 1.5          # この morphogen 値で最大長に到達
_APP_BASE_LENGTH_RATIO = 0.02     # 親径に対する基本長さ比率
_APP_BASE_THICK_RATIO = 0.01      # 親径に対する基本太さ比率
_APP_BASE_LENGTH_FLOOR = 0.04     # 基本長さの最小値
_APP_BASE_THICK_FLOOR = 0.02      # 基本太さの最小値


def _create_rotated_mesh(tree, mesh_type, mesh_creator, rotation_euler, y_offset):
    """メッシュプリミティブ生成 + 非CUBE型は指定角度で回転"""
    _, mesh_out = mesh_creator(tree, (-600, y_offset))
    if mesh_type in _NEEDS_ROTATION:
        _, rot_vec = gn.combine_xyz(
            tree, x=rotation_euler[0], y=rotation_euler[1], z=rotation_euler[2],
            location=(-400, y_offset - 50))
        rot_node = gn.add_node(tree, "FunctionNodeEulerToRotation",
                                location=(-300, y_offset - 50))
        gn.link(tree, rot_vec, rot_node.inputs["Euler"])
        _, mesh_out = gn.transform(
            tree, mesh_out, rotation=rot_node.outputs["Rotation"],
            location=(-200, y_offset))
    return mesh_out


def _compute_positions(chain: list[Segment], scale_axis: str,
                       uniform_scale: float) -> list[float]:
    """各体節のX軸配置位置を計算（隣接配置保証）

    scale_axis に関わらず、実際のX方向寸法に基づいて隙間なく配置する。
    メイン体節のビジュアルサイズは scale_x × morphogen（2つの遺伝子駆動量の積）。
    """
    positions = [0.0]  # 先頭は原点

    for i in range(1, len(chain)):
        prev_seg = chain[i - 1]
        curr_seg = chain[i]

        # 各体節の実際のX方向サイズ（scale_x × morphogen の積）
        if scale_axis == "X":
            prev_x_size = prev_seg.scale_x * prev_seg.morphogen
            curr_x_size = curr_seg.scale_x * curr_seg.morphogen
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

    # マテリアル取得（白と黒の2色）
    materials = {
        "default": get_or_create_material("default"),
        "A": get_or_create_material("A"),
    }

    mesh_creator = MESH_CREATORS.get(mesh_type, MESH_CREATORS["CUBE"])

    # 実際のX寸法に基づく配置位置を計算
    positions = _compute_positions(chain, scale_axis, uniform_scale)

    # === Phase 1: 全メイン体節を構築 ===
    main_geo_sockets = []

    for i, seg in enumerate(chain):
        y_offset = -i * 200  # ノードを縦に並べる

        # メッシュプリミティブ生成（非CUBE型は回転付き）
        mesh_out = _create_rotated_mesh(tree, mesh_type, mesh_creator, _ROT_Y_90, y_offset)

        # スケールベクター: scale_x(乗算的) × morphogen(加算的) の積で視覚サイズ決定
        # scale_x: アクションルール駆動（指数的変化）
        # morphogen: T/Hビット駆動（線形的変化）
        visual_size = seg.scale_x * seg.morphogen
        if scale_axis == "X":
            sx, sy, sz = visual_size, uniform_scale, uniform_scale
        else:  # "Y" — Y軸のみ変化、Z軸はuniform_scale
            sx, sy, sz = uniform_scale, visual_size, uniform_scale

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

        main_geo_sockets.append(mat_out)

    # === Phase 2: 付属肢チェーンを構築（メイン体節は全て確定済み）===
    appendage_geo_sockets = []
    app_node_base_y = -len(chain) * 200 - 200  # メイン体節の下にノードを配置

    for i, seg in enumerate(chain):
        if not seg.has_appendage or not seg.appendage_chain:
            continue

        # 親体節の各軸寸法（scale_x × morphogen: 視覚サイズと一致）
        parent_visual = seg.scale_x * seg.morphogen
        if scale_axis == "X":
            parent_x_width = parent_visual   # X軸方向（チェーン方向）
            parent_y_half = uniform_scale / 2.0
        else:  # "Y"
            parent_x_width = uniform_scale   # X軸方向（チェーン方向）
            parent_y_half = parent_visual / 2.0

        parent_y_diameter = parent_y_half * 2.0
        parent_mat = materials.get(seg.material, materials["default"])

        for side_idx, sign in enumerate((+1.0, -1.0)):
            # 付属肢チェーンの各体節を Y 方向に積む
            y_cursor = sign * parent_y_half  # 親表面から開始

            # 付属肢寸法: morphogen 絶対値で長さ決定（チェーン内正規化は廃止）
            # 低 morphogen → 短い節、高 morphogen → 長い節
            # 基本サイズは親体節の Y 直径に比例（親のサイズが付属肢全体のスケールを決定）
            base_seg_length = max(_APP_BASE_LENGTH_FLOOR, parent_y_diameter * _APP_BASE_LENGTH_RATIO)
            base_seg_thick = max(_APP_BASE_THICK_FLOOR, parent_y_diameter * _APP_BASE_THICK_RATIO)

            for j, app_seg in enumerate(seg.appendage_chain):
                app_y_offset = app_node_base_y
                app_node_base_y -= 200

                # morphogen 絶対値 → [0, 1] にクランプ（正規化ではない）
                morph_t = min(app_seg.morphogen / _APP_MORPHOGEN_REF, 1.0)
                # 二乗カーブ: 低 morphogen を圧縮し、高 morphogen の差を強調
                morph_t_sq = morph_t * morph_t

                # 節の長さ: base × [1, _APP_MAX_LENGTH_MULT]
                length_mult = 1.0 + morph_t_sq * (_APP_MAX_LENGTH_MULT - 1.0)
                app_s = base_seg_length * length_mult

                # 節の太さ: base × [1, _APP_MAX_THICK_MULT]
                thick_mult = 1.0 + morph_t * (_APP_MAX_THICK_MULT - 1.0)
                app_uniform = base_seg_thick * thick_mult

                # Y座標: 節が自分の長さ分の空間を占有（端と端で隣接）
                y_cursor += sign * (app_s / 2.0)
                app_y = y_cursor

                # メッシュプリミティブ生成（非CUBE型は回転付き）
                app_mesh = _create_rotated_mesh(tree, mesh_type, mesh_creator, _ROT_X_90, app_y_offset)

                # 非均一スケール: Y軸にapp_s（長さ=1〜100倍）、X/Z軸にapp_uniform（太さ=1〜5倍）
                _, app_scale_vec = gn.combine_xyz(
                    tree, x=app_uniform, y=app_s, z=app_uniform,
                    location=(0, app_y_offset - 50))
                _, app_pos_vec = gn.combine_xyz(
                    tree, x=positions[i], y=app_y, z=0.0,
                    location=(0, app_y_offset + 50))
                _, app_tf_out = gn.transform(
                    tree, app_mesh, translation=app_pos_vec, scale=app_scale_vec,
                    location=(200, app_y_offset))

                # 付属肢体節のマテリアル（付属肢自身のmaterialを使用、フォールバックは親）
                app_mat = materials.get(app_seg.material, parent_mat)
                _, app_mat_out = gn.set_material(
                    tree, app_tf_out, app_mat,
                    location=(400, app_y_offset))

                appendage_geo_sockets.append(app_mat_out)

                # カーソルを次の体節の開始位置に進める
                y_cursor += sign * (app_s / 2.0)

    # === Phase 3: 全結合 ===
    all_geo = main_geo_sockets + appendage_geo_sockets

    if len(all_geo) == 1:
        gn.link(tree, all_geo[0], group_out.inputs["Geometry"])
    else:
        _, joined = gn.join_geometry(
            tree, *all_geo,
            location=(700, 0))
        gn.link(tree, joined, group_out.inputs["Geometry"])

    return tree

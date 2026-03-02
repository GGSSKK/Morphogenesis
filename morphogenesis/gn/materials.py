"""マテリアル管理 — get_or_create パターン"""
import bpy

# マテリアル定義
MATERIAL_CONFIGS = {
    "default": {
        "base_color": (1.0, 1.0, 1.0, 1.0),  # 白
        "metallic": 0.1,
        "roughness": 0.5,
    },
    "A": {
        "base_color": (0.05, 0.05, 0.05, 1.0),  # 黒
        "metallic": 0.1,
        "roughness": 0.5,
    },
}


def _find_principled_bsdf(mat):
    """Principled BSDF ノードを type ベースで検索（名前変更に対応）"""
    if mat.node_tree is None:
        return None
    for node in mat.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            return node
    return None


def get_or_create_material(name: str) -> bpy.types.Material:
    """マテリアルを取得、なければ作成（get_or_createパターン）

    既存マテリアルがある場合も色を再設定する（色設定の失敗を修復）。
    """
    mat_name = f"Morpho_{name}"
    mat = bpy.data.materials.get(mat_name)

    cfg = MATERIAL_CONFIGS.get(name, MATERIAL_CONFIGS["default"])

    if mat is None:
        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True

    # Principled BSDF を type ベースで検索して色を設定
    bsdf = _find_principled_bsdf(mat)
    if bsdf:
        bsdf.inputs["Base Color"].default_value = cfg["base_color"]
        bsdf.inputs["Metallic"].default_value = cfg["metallic"]
        bsdf.inputs["Roughness"].default_value = cfg["roughness"]

    # ビューポート Solid モードでも色が表示されるように設定
    mat.diffuse_color = cfg["base_color"]

    return mat

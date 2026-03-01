"""Morphogenesis 起動スクリプト — Blender 起動時に自動実行

Blender の起動オプション: --python launch_morpho.py
アドオンが有効化され、デフォルトパラメータでクリーチャーを自動生成する。
"""
import bpy
import sys
import os

# morphogenesis パッケージパスを追加
addon_dir = os.path.dirname(__file__)
if addon_dir not in sys.path:
    sys.path.insert(0, addon_dir)


def _setup_and_generate():
    """アドオン有効化 + デフォルト生成"""
    # symlink 経由で自動ロードされていなければ手動登録
    if not hasattr(bpy.types.Scene, "morpho_props"):
        from morphogenesis import register
        register()

    # デフォルトパラメータを設定
    props = bpy.context.scene.morpho_props
    props.mesh_type = "SPHERE"
    props.seed = 42
    props.scale_axis = "Y"

    # 初回生成
    bpy.ops.morpho.generate()

    # 3D ビューをフレームイン
    for area in bpy.context.screen.areas:
        if area.type == "VIEW_3D":
            for region in area.regions:
                if region.type == "WINDOW":
                    override = bpy.context.copy()
                    override["area"] = area
                    override["region"] = region
                    with bpy.context.temp_override(**override):
                        bpy.ops.view3d.view_all(center=False)
                    break
            break

    print("[Morphogenesis] 起動完了 — SPHERE デフォルト生成済み")


# Blender の起動処理が完了してから実行するためタイマーで遅延
bpy.app.timers.register(_setup_and_generate, first_interval=0.1)

"""Morphogenesis — 遺伝子駆動プロシージャルクリーチャー生成 Blender アドオン"""

bl_info = {
    "name": "Morphogenesis",
    "author": "GGSSKK",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar > Morphogenesis",
    "description": "遺伝子駆動のプロシージャルクリーチャー生成（02Test準拠）",
    "category": "Object",
}

# bpy はBlender内でのみ利用可能。pytest等の外部テスト時はガードする
try:
    import bpy
    _HAS_BPY = True
except ImportError:
    _HAS_BPY = False


def register():
    if not _HAS_BPY:
        return
    from .operators.generate import MORPHO_OT_Generate
    from .operators.randomize import MORPHO_OT_Randomize
    from .operators.save_creature import MORPHO_OT_SaveCreature
    from .operators.reload import MORPHO_OT_Reload
    from .panels.main_panel import MORPHO_PT_MainPanel
    from .props.scene_props import MorphoProperties

    classes = (
        MorphoProperties,
        MORPHO_OT_Generate,
        MORPHO_OT_Randomize,
        MORPHO_OT_SaveCreature,
        MORPHO_OT_Reload,
        MORPHO_PT_MainPanel,
    )

    # 再インストール時に既存クラスが残っている場合を安全に処理
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except RuntimeError:
            pass
    if hasattr(bpy.types.Scene, "morpho_props"):
        del bpy.types.Scene.morpho_props

    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.morpho_props = bpy.props.PointerProperty(type=MorphoProperties)


def unregister():
    if not _HAS_BPY:
        return
    from .operators.generate import MORPHO_OT_Generate
    from .operators.randomize import MORPHO_OT_Randomize
    from .operators.save_creature import MORPHO_OT_SaveCreature
    from .operators.reload import MORPHO_OT_Reload
    from .panels.main_panel import MORPHO_PT_MainPanel
    from .props.scene_props import MorphoProperties

    if hasattr(bpy.types.Scene, "morpho_props"):
        del bpy.types.Scene.morpho_props
    classes = (
        MorphoProperties,
        MORPHO_OT_Generate,
        MORPHO_OT_Randomize,
        MORPHO_OT_SaveCreature,
        MORPHO_OT_Reload,
        MORPHO_PT_MainPanel,
    )
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()

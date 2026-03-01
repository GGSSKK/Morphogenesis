"""リロードオペレーター — ビジネスロジックモジュールを再読み込み

Blender のクラス登録（Operator/Panel/PropertyGroup）は触らず、
core/* と gn/* のロジックモジュールのみリロードする。
これにより SEGV を回避しつつ、ロジック変更を即座に反映できる。

※ UI/プロパティ定義の変更には Blender 再起動が必要
"""
import bpy
import importlib
import sys


# リロード対象のモジュール（import順序に従って並べる）
_RELOAD_TARGETS = [
    "morphogenesis.core.types",
    "morphogenesis.core.condition",
    "morphogenesis.core.action",
    "morphogenesis.core.chain_builder",
    "morphogenesis.gn.geonodes_utils",
    "morphogenesis.gn.materials",
    "morphogenesis.gn.chain_to_gn",
    "morphogenesis.operators.generate",
]


class MORPHO_OT_Reload(bpy.types.Operator):
    """ロジックモジュールを再読み込み（開発用）"""
    bl_idname = "morpho.reload"
    bl_label = "Reload Addon"
    bl_options = {"REGISTER"}

    def execute(self, context):
        reloaded = 0
        for name in _RELOAD_TARGETS:
            mod = sys.modules.get(name)
            if mod is not None:
                try:
                    importlib.reload(mod)
                    reloaded += 1
                except Exception as e:
                    self.report({"WARNING"}, f"リロード失敗: {name} — {e}")

        # リロード後に再生成して変更を反映
        try:
            bpy.ops.morpho.generate()
        except Exception as e:
            self.report({"WARNING"}, f"再生成エラー: {e}")

        self.report({"INFO"}, f"{reloaded} モジュールをリロードしました")
        return {"FINISHED"}

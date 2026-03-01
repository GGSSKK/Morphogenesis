"""ランダム化オペレーター — 新しいSeedで遺伝子をランダム生成"""
import bpy
import random


class MORPHO_OT_Randomize(bpy.types.Operator):
    """ランダムSeedで遺伝子を再生成"""
    bl_idname = "morpho.randomize"
    bl_label = "Randomize"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        props = context.scene.morpho_props
        # gene_string をクリアしてSeedベース生成に戻す
        props.gene_string = ""
        # 新しいランダムSeed
        props.seed = random.randint(0, 99999)
        # seed の update コールバックが generate を呼ぶので
        # ここでは追加の generate 呼び出しは不要
        return {"FINISHED"}

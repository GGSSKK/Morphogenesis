"""メインパネル — 3Dビューサイドバー"""
import bpy


class MORPHO_PT_MainPanel(bpy.types.Panel):
    """Morphogenesis メインパネル"""
    bl_label = "Morphogenesis"
    bl_idname = "MORPHO_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Morphogenesis"

    def draw(self, context):
        layout = self.layout
        props = context.scene.morpho_props

        # Seed + Randomize ボタン
        row = layout.row(align=True)
        row.prop(props, "seed")
        row.operator("morpho.randomize", text="", icon="FILE_REFRESH")

        # パラメータ
        layout.prop(props, "rule_count")
        layout.prop(props, "max_segments")
        layout.prop(props, "max_appendage_segments")
        layout.prop(props, "mesh_type")

        layout.separator()

        # スケール設定
        layout.prop(props, "scale_axis")
        layout.prop(props, "segment_max_scale")
        layout.prop(props, "segment_uniform_scale")

        layout.separator()

        # 操作ボタン
        row = layout.row(align=True)
        row.scale_y = 1.5
        row.operator("morpho.save_creature", text="Save Creature", icon="FILE_TICK")

        layout.separator()

        # 情報表示
        box = layout.box()
        box.label(text="Info", icon="INFO")

        # 遺伝子文字列（長いので折り返し）
        gene_str = props.gene_string
        if gene_str:
            col = box.column(align=True)
            col.scale_y = 0.8
            # 最初の3ルールだけ表示
            parts = gene_str.split("/")
            preview = "/".join(parts[:3])
            if len(parts) > 3:
                preview += f"/... ({len(parts)} rules)"
            col.label(text=f"Gene: {preview}")

        box.label(text=f"Segments: {props.segment_count}")
        box.label(text=f"Appendages: {props.appendage_count}")

        layout.separator()

        # 開発用リロードボタン
        layout.operator("morpho.reload", text="Reload Addon", icon="FILE_REFRESH")

"""保存オペレーター — 現在のクリーチャーをArchiveコレクションにGN編集可能なまま保存"""
import bpy


ARCHIVE_COLLECTION = "Archive"


class MORPHO_OT_SaveCreature(bpy.types.Operator):
    """現在のクリーチャーをArchiveコレクションに保存"""
    bl_idname = "morpho.save_creature"
    bl_label = "Save Creature"
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        # ソースオブジェクト取得
        src = bpy.data.objects.get("Morpho_Creature")
        if src is None:
            self.report({"WARNING"}, "クリーチャーが存在しません。先にGenerateを実行してください")
            return {"CANCELLED"}

        # Archiveコレクション取得 or 作成
        archive = bpy.data.collections.get(ARCHIVE_COLLECTION)
        if archive is None:
            archive = bpy.data.collections.new(ARCHIVE_COLLECTION)
            context.scene.collection.children.link(archive)

        # 複製
        new_obj = src.copy()
        new_obj.data = src.data.copy()

        # GNモディファイアのノードツリーも複製（独立編集可能にする）
        for mod in new_obj.modifiers:
            if mod.type == "NODES" and mod.node_group:
                new_tree = mod.node_group.copy()
                mod.node_group = new_tree

        # 連番名
        idx = 1
        while bpy.data.objects.get(f"Creature_{idx:03d}"):
            idx += 1
        new_obj.name = f"Creature_{idx:03d}"
        if new_obj.data:
            new_obj.data.name = f"Creature_{idx:03d}"

        # GNツリーにも連番名
        for mod in new_obj.modifiers:
            if mod.type == "NODES" and mod.node_group:
                mod.node_group.name = f"Morpho_GN_{idx:03d}"

        # Archiveコレクションに追加
        archive.objects.link(new_obj)

        # 元のコレクションからは除去
        for col in new_obj.users_collection:
            if col != archive:
                col.objects.unlink(new_obj)

        # ビューポート非表示（eye アイコン OFF）
        new_obj.hide_set(True)

        # 遺伝子文字列をカスタムプロパティに保存
        props = context.scene.morpho_props
        new_obj["gene_string"] = props.gene_string
        new_obj["seed"] = props.seed

        self.report({"INFO"}, f"'{new_obj.name}' をArchiveに保存しました")
        return {"FINISHED"}

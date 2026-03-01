"""Blender ヘッドレス検証スクリプト

実行: blender --background --python test_blender.py
"""
import sys
import os
import importlib

# morphogenesis パッケージをインポートパスに追加
sys.path.insert(0, os.path.dirname(__file__))

import bpy

# symlink経由で自動ロードされたモジュールをリロードして最新コードを反映
for mod_name in sorted([n for n in sys.modules if n.startswith("morphogenesis")],
                       key=lambda n: n.count(".")):
    importlib.reload(sys.modules[mod_name])

# === 1. アドオン登録 ===
print("=== アドオン登録テスト ===")
from morphogenesis import register, unregister
# シンボリンク経由で自動ロード済みの場合はスキップ
if not hasattr(bpy.types.Scene, "morpho_props"):
    register()
    print("[OK] register() 成功")
else:
    print("[OK] アドオン既にロード済み（symlink経由）")

# morpho_props が登録されていることを確認
assert hasattr(bpy.types.Scene, "morpho_props"), "morpho_props が Scene に登録されていません"
print("[OK] morpho_props 登録確認")

# === 2. コアロジック確認 ===
print("\n=== コアロジック確認 ===")
from morphogenesis.core.types import Gene
from morphogenesis.core.chain_builder import build_chain

gene = Gene.random(num_rules=20, seed=42)
chain = build_chain(gene, max_segments=30)
print(f"[OK] Gene生成: {len(gene.rules)} ルール")
print(f"[OK] Chain生成: {len(chain)} 体節")
print(f"     Gene文字列: {gene.to_string()[:60]}...")
for seg in chain[:5]:
    print(f"     Seg[{seg.index}]: scale_x={seg.scale_x:.4f}, pos_x={seg.pos_x:.1f}, mat={seg.material}")
if len(chain) > 5:
    print(f"     ... (残り {len(chain) - 5} 体節)")

# === 3. GNツリー構築 ===
print("\n=== GNツリー構築テスト ===")
from morphogenesis.gn.chain_to_gn import build_gn_tree

for mesh_type in ["CUBE", "SPHERE", "CYLINDER", "CONE"]:
    tree = build_gn_tree(chain, mesh_type=mesh_type, scale_axis="X", uniform_scale=1.5)
    node_count = len(tree.nodes)
    link_count = len(tree.links)
    print(f"[OK] {mesh_type}: {node_count} ノード, {link_count} リンク")

# Y軸モードもテスト
tree_y = build_gn_tree(chain, mesh_type="SPHERE", scale_axis="Y", uniform_scale=1.0)
print(f"[OK] SPHERE Y-axis: {len(tree_y.nodes)} ノード")

# === 4. オペレーター実行 ===
print("\n=== オペレーター実行テスト ===")
# Generate
props = bpy.context.scene.morpho_props
props.seed = 42
props.rule_count = 20
props.max_segments = 30
props.mesh_type = "CUBE"
props.segment_max_scale = 8.0
props.segment_uniform_scale = 1.0
props.scale_axis = "X"

result = bpy.ops.morpho.generate()
assert result == {"FINISHED"}, f"Generate 失敗: {result}"
print("[OK] morpho.generate 成功")

obj = bpy.data.objects.get("Morpho_Creature")
assert obj is not None, "Morpho_Creature オブジェクトが見つかりません"
print(f"[OK] Morpho_Creature 作成確認 (modifiers: {len(obj.modifiers)})")

# GN モディファイアが残存しているか
gn_mod = None
for m in obj.modifiers:
    if m.type == "NODES":
        gn_mod = m
        break
assert gn_mod is not None, "GN モディファイアが見つかりません"
assert gn_mod.node_group is not None, "node_group が None"
print(f"[OK] GN モディファイア残存確認: {gn_mod.node_group.name}")

# === 5. Seed変更で再生成 ===
print("\n=== Seed変更テスト ===")
old_gene = props.gene_string
props.gene_string = ""
props.seed = 12345
bpy.ops.morpho.generate()
new_gene = props.gene_string
print(f"[OK] Seed 42 → 12345 で遺伝子変化: {old_gene[:30]}... → {new_gene[:30]}...")
assert old_gene != new_gene, "Seed変更後も遺伝子が同じ"
print("[OK] 遺伝子が変化していることを確認")

# === 6. Mesh Type 変更 ===
print("\n=== Mesh Type 変更テスト ===")
for mt in ["SPHERE", "CYLINDER", "CONE", "CUBE"]:
    props.mesh_type = mt
    props.gene_string = ""
    bpy.ops.morpho.generate()
    print(f"[OK] {mt} での生成成功")

# === 7. Save Creature ===
print("\n=== Save Creature テスト ===")
result = bpy.ops.morpho.save_creature()
assert result == {"FINISHED"}, f"Save 失敗: {result}"
archive = bpy.data.collections.get("Archive")
assert archive is not None, "Archive コレクションが見つかりません"
print(f"[OK] Archive コレクション確認: {len(archive.objects)} オブジェクト")

saved = None
for o in archive.objects:
    if o.name.startswith("Creature_"):
        saved = o
        break
assert saved is not None, "保存されたオブジェクトが見つかりません"
print(f"[OK] 保存オブジェクト: {saved.name}")

# GNモディファイアが編集可能か
saved_mod = None
for m in saved.modifiers:
    if m.type == "NODES":
        saved_mod = m
        break
assert saved_mod is not None, "保存オブジェクトにGNモディファイアがありません"
assert saved_mod.node_group is not None, "保存オブジェクトのnode_groupがNone"
# 元のオブジェクトとは別のGNツリーであること
assert saved_mod.node_group != gn_mod.node_group, "GNツリーが共有されています（独立コピーでない）"
print(f"[OK] GNモディファイア独立コピー確認: {saved_mod.node_group.name}")

# 複数回保存
bpy.ops.morpho.save_creature()
bpy.ops.morpho.save_creature()
print(f"[OK] 複数保存: Archive内 {len(archive.objects)} オブジェクト")

# === 8. プレビュー .blend 保存 ===
print("\n=== プレビュー保存 ===")
preview_path = "/tmp/Morphogenesis/morpho_preview.blend"
bpy.ops.wm.save_as_mainfile(filepath=preview_path)
print(f"[OK] プレビュー保存: {preview_path}")

# === クリーンアップ ===
unregister()
print("\n[OK] unregister() 成功")

print("\n" + "=" * 50)
print("全テスト通過！アドオンは正常に動作しています。")
print("=" * 50)

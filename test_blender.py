"""Blender ヘッドレス検証スクリプト（モルフォゲン濃度ベース対応）

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


def _set_props_batch(props, **kwargs):
    """update コールバックを抑制してプロパティを一括設定"""
    props["_updating"] = True
    try:
        for k, v in kwargs.items():
            setattr(props, k, v)
    finally:
        props["_updating"] = False

# === 2. コアロジック確認 ===
print("\n=== コアロジック確認 ===")
from morphogenesis.core.types import Gene
from morphogenesis.core.chain_builder import build_chain

gene = Gene.random(num_rules=20, seed=42)
chain = build_chain(gene, max_segments=30)
print(f"[OK] Gene生成: {len(gene.rules)} ルール")
print(f"[OK] Chain生成: {len(chain)} 体節")
print(f"     appendage_threshold: {gene.appendage_threshold:.3f}")
print(f"     appendage_start_ratio: {gene.appendage_start_ratio:.3f}")
print(f"     Gene文字列: {gene.to_string()[:60]}...")
for seg in chain[:5]:
    app_info = f", app={len(seg.appendage_chain)}" if seg.has_appendage else ""
    print(f"     Seg[{seg.index}]: scale_x={seg.scale_x:.4f}, pos_x={seg.pos_x:.1f}, mat={seg.material}{app_info}")
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
_set_props_batch(props,
    seed=42, rule_count=20, max_segments=30,
    mesh_type="CUBE", segment_max_scale=8.0,
    segment_uniform_scale=1.0, scale_axis="X", gene_string="",
)

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
_set_props_batch(props, gene_string="", seed=12345)
bpy.ops.morpho.generate()
new_gene = props.gene_string
print(f"[OK] Seed 42 → 12345 で遺伝子変化: {old_gene[:30]}... → {new_gene[:30]}...")
assert old_gene != new_gene, "Seed変更後も遺伝子が同じ"
print("[OK] 遺伝子が変化していることを確認")

# === 6. Mesh Type 変更 ===
print("\n=== Mesh Type 変更テスト ===")
for mt in ["SPHERE", "CYLINDER", "CONE", "CUBE"]:
    _set_props_batch(props, mesh_type=mt, gene_string="")
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

# === 8. 付属肢チェーン（モルフォゲン濃度ベース）テスト ===
print("\n=== 付属肢チェーンテスト ===")

from morphogenesis.core.types import Rule, ConditionCode, ActionCode

# 低閾値で付属肢が発生する遺伝子
gene_app = Gene(
    rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN)],
    appendage_threshold=0.5,
    appendage_start_ratio=0.5,
)
chain_app = build_chain(gene_app, max_segments=10, max_appendage_segments=5)
app_count = sum(1 for s in chain_app if s.has_appendage)
app_seg_total = sum(len(s.appendage_chain) for s in chain_app if s.has_appendage)
print(f"[OK] 付属肢付きチェーン: {len(chain_app)} 体節, {app_count} 体節に付属肢, 付属肢体節合計: {app_seg_total}")

# 付属肢チェーンの多体節確認
for seg in chain_app:
    if seg.has_appendage:
        assert len(seg.appendage_chain) >= 1, f"seg[{seg.index}] の付属肢チェーンが空"
        assert seg.appendage_chain[0].scale_x == seg.appendage_scale, \
            f"seg[{seg.index}] 付属肢先頭スケールが appendage_scale と不一致"
    # 再帰なし確認
    for app_seg in seg.appendage_chain:
        assert app_seg.has_appendage is False, "付属肢チェーン内はサブ付属肢なし"
        assert app_seg.appendage_chain == [], "付属肢チェーン内のappendage_chainは空"
print(f"[OK] 付属肢チェーン多体節・再帰なし確認完了")

# GNツリー比較
gene_no_app = Gene(
    rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN)],
    appendage_threshold=100.0,  # 高閾値 → 付属肢なし
    appendage_start_ratio=0.5,
)
chain_no_app = build_chain(gene_no_app, max_segments=10)
tree_no_app = build_gn_tree(chain_no_app, mesh_type="SPHERE", scale_axis="Y", uniform_scale=1.0)
node_count_no_app = len(tree_no_app.nodes)

tree_app = build_gn_tree(chain_app, mesh_type="SPHERE", scale_axis="Y", uniform_scale=1.0)
node_count_app = len(tree_app.nodes)
link_count_app = len(tree_app.links)
print(f"[OK] 付属肢GNツリー: {node_count_app} ノード, {link_count_app} リンク")
print(f"[OK] 付属肢なし: {node_count_no_app} ノード → 付属肢あり: {node_count_app} ノード (差: +{node_count_app - node_count_no_app})")
assert node_count_app > node_count_no_app, "付属肢付きはノード数が多いはず"

# 全メッシュタイプで付属肢GNツリーを構築
for mt in ["CUBE", "SPHERE", "CYLINDER", "CONE"]:
    tree_mt = build_gn_tree(chain_app, mesh_type=mt, scale_axis="X", uniform_scale=1.5)
    print(f"[OK] 付属肢 {mt}: {len(tree_mt.nodes)} ノード")

# オペレーターで付属肢付き生成
_set_props_batch(props,
    seed=42, rule_count=20, max_segments=30,
    max_appendage_segments=10, mesh_type="SPHERE",
    scale_axis="Y", segment_uniform_scale=1.0, gene_string="",
)
bpy.ops.morpho.generate()
print(f"[OK] Seed=42 付属肢体節合計: {props.appendage_count}")

# マテリアル2色確認
gene_mat = Gene(
    rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MATERIAL_B)],
    appendage_threshold=0.5, appendage_start_ratio=0.5,
)
chain_mat = build_chain(gene_mat, max_segments=5)
for seg in chain_mat[1:]:
    assert seg.material == "A", f"MATERIAL_B should assign 'A', got '{seg.material}'"
print("[OK] MATERIAL_B assigns 'A' (2色統一)")

# start_ratio差テスト
gene_low_r = Gene(
    rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_DOWN_SMALL)],
    appendage_threshold=0.5, appendage_start_ratio=0.2,
)
gene_high_r = Gene(
    rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_DOWN_SMALL)],
    appendage_threshold=0.5, appendage_start_ratio=0.8,
)
chain_s0 = build_chain(gene_low_r, max_segments=3, max_appendage_segments=5)
chain_s1 = build_chain(gene_high_r, max_segments=3, max_appendage_segments=5)
if chain_s0[1].has_appendage and chain_s1[1].has_appendage:
    s0_head = chain_s0[1].appendage_chain[0].scale_x
    s1_head = chain_s1[1].appendage_chain[0].scale_x
    print(f"[OK] start_ratio 差: low={s0_head:.4f}, high={s1_head:.4f}")
    assert abs(s0_head - s1_head) > 0.01, "start_ratio で開始スケールが異なるべき"

# === 9. 付属肢プレビュー .blend 保存 ===
print("\n=== 付属肢プレビュー保存 ===")

_set_props_batch(props,
    mesh_type="SPHERE", scale_axis="Y", segment_uniform_scale=1.0,
    gene_string=gene_app.to_string(), max_appendage_segments=5,
)
bpy.ops.morpho.generate()
print(f"[OK] 付属肢プレビュー生成: {props.segment_count} 体節, {props.appendage_count} 付属肢")

preview_path = "/tmp/Morphogenesis/morpho_preview.blend"
bpy.ops.wm.save_as_mainfile(filepath=preview_path)
print(f"[OK] プレビュー保存: {preview_path}")

# === クリーンアップ ===
unregister()
print("\n[OK] unregister() 成功")

print("\n" + "=" * 50)
print("全テスト通過！アドオンは正常に動作しています。")
print("=" * 50)

"""Blender ヘッドレス検証スクリプト（独立モルフォゲン v2 + morphogen条件評価 対応）

実行: blender --background --factory-startup -noaudio --python test_blender_quick.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

import bpy

# === 1. アドオン登録 ===
print("=== 1. register ===")
from morphogenesis import register, unregister
register()
assert hasattr(bpy.types.Scene, "morpho_props")
print("[OK] register")


def _set_props_batch(props, **kwargs):
    """update コールバックを抑制してプロパティを一括設定"""
    props["_updating"] = True
    try:
        for k, v in kwargs.items():
            setattr(props, k, v)
    finally:
        props["_updating"] = False


# === 2. Generate ===
print("\n=== 2. Generate ===")
props = bpy.context.scene.morpho_props
_set_props_batch(props,
    seed=42, rule_count=20, max_segments=30,
    max_appendage_segments=10, mesh_type="SPHERE",
    scale_axis="Y", segment_uniform_scale=1.0, gene_string="",
)
result = bpy.ops.morpho.generate()
assert result == {"FINISHED"}
print(f"[OK] Generate: segs={props.segment_count}, app_segs={props.appendage_count}")

# === 3. All mesh types ===
print("\n=== 3. All mesh types ===")
for mt in ["CUBE", "SPHERE", "CYLINDER", "CONE"]:
    _set_props_batch(props, mesh_type=mt, gene_string="")
    bpy.ops.morpho.generate()
    print(f"[OK] {mt}")

# === 4. Save ===
print("\n=== 4. Save ===")
result = bpy.ops.morpho.save_creature()
assert result == {"FINISHED"}
print("[OK] Save")

# === 5. Appendage chain（独立モルフォゲン v2）===
print("\n=== 5. Appendage chain ===")
from morphogenesis.core.types import Gene, Rule, ConditionCode, ActionCode
from morphogenesis.core.chain_builder import build_chain
from morphogenesis.gn.chain_to_gn import build_gn_tree

# 低閾値 + T ビット発火で付属肢が発生する遺伝子
gene_app = Gene(
    rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                threshold_factor=True, ratio_factor=False)],
    appendage_threshold=0.5,
    appendage_start_ratio=0.5,
)
chain_app = build_chain(gene_app, max_segments=10, max_appendage_segments=5)
app_total = sum(len(s.appendage_chain) for s in chain_app if s.has_appendage)
print(f"[OK] Chain: {len(chain_app)} segs, app_total={app_total}")

# morphogen 独立性チェック
for s in chain_app[1:]:
    assert hasattr(s, 'morphogen'), "Segment に morphogen フィールドがあるべき"
print("[OK] morphogen field exists")

# no recursion check
for s in chain_app:
    for a in s.appendage_chain:
        assert not a.has_appendage
        assert a.appendage_chain == []
print("[OK] No recursion")

# GN tree comparison
gene_no = Gene(
    rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN)],
    appendage_threshold=100.0,
    appendage_start_ratio=0.5,
)
tree_no = build_gn_tree(
    build_chain(gene_no, max_segments=10),
    mesh_type="SPHERE", scale_axis="Y", uniform_scale=1.0)
node_count_no = len(tree_no.nodes)

tree_app_gn = build_gn_tree(chain_app, mesh_type="SPHERE", scale_axis="Y", uniform_scale=1.0)
node_count_app = len(tree_app_gn.nodes)
print(f"[OK] Nodes: no_app={node_count_no}, with_app={node_count_app} (+{node_count_app - node_count_no})")
assert node_count_app > node_count_no

# All mesh types with appendages
for mt in ["CUBE", "SPHERE", "CYLINDER", "CONE"]:
    t = build_gn_tree(chain_app, mesh_type=mt, scale_axis="X", uniform_scale=1.5)
    print(f"[OK] App {mt}: {len(t.nodes)} nodes")

# start_ratio difference
gene_low_r = Gene(
    rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_DOWN_SMALL,
                threshold_factor=True, ratio_factor=False)],
    appendage_threshold=0.5, appendage_start_ratio=0.2,
)
gene_high_r = Gene(
    rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_DOWN_SMALL,
                threshold_factor=True, ratio_factor=False)],
    appendage_threshold=0.5, appendage_start_ratio=0.8,
)
cs = build_chain(gene_low_r, max_segments=3, max_appendage_segments=5)
cl = build_chain(gene_high_r, max_segments=3, max_appendage_segments=5)
if cs[1].has_appendage and cl[1].has_appendage:
    s0 = cs[1].appendage_chain[0].scale_x
    s1 = cl[1].appendage_chain[0].scale_x
    print(f"[OK] start_ratio: low={s0:.4f}, high={s1:.4f}")
    assert abs(s0 - s1) > 0.01

# === 6. マテリアル2色確認 ===
print("\n=== 6. Material 2-color ===")
gene_mat_a = Gene(
    rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MATERIAL_A)],
    appendage_threshold=100.0, appendage_start_ratio=0.5,
)
chain_mat_a = build_chain(gene_mat_a, max_segments=5)
for seg in chain_mat_a[1:]:
    assert seg.material == "A", f"MATERIAL_A should assign 'A', got '{seg.material}'"
print("[OK] MATERIAL_A assigns 'A' (black)")

gene_mat_b = Gene(
    rules=[
        Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MATERIAL_A),
        Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MATERIAL_B),
    ],
    appendage_threshold=100.0, appendage_start_ratio=0.5,
)
chain_mat_b = build_chain(gene_mat_b, max_segments=5)
for seg in chain_mat_b[1:]:
    assert seg.material == "default", \
        f"MATERIAL_B should assign 'default' (white), got '{seg.material}'"
print("[OK] MATERIAL_B assigns 'default' (white)")

# 白黒混在テスト
gene_mixed = Gene(
    rules=[
        Rule(ConditionCode.N1_SCALE_LT_HALF, ActionCode.MATERIAL_A),
        Rule(ConditionCode.N1_SCALE_GE_HALF, ActionCode.MATERIAL_B),
        Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_DOWN_SMALL),
    ],
    appendage_threshold=100.0, appendage_start_ratio=0.5,
)
chain_mixed = build_chain(gene_mixed, max_segments=20)
mats = set(seg.material for seg in chain_mixed[1:])
print(f"[OK] Mixed materials: {mats}")
assert "A" in mats and "default" in mats, f"白黒混在するべき: {mats}"

# === 7. 独立モルフォゲン検証 ===
print("\n=== 7. Independent morphogen ===")
gene_morph = Gene(
    rules=[Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_DOWN_SMALL,
                threshold_factor=True, ratio_factor=False)],
    appendage_threshold=0.5, appendage_start_ratio=0.5,
)
chain_morph = build_chain(gene_morph, max_segments=15)
small_with_app = [s for s in chain_morph[1:] if s.scale_x < 0.5 and s.has_appendage]
print(f"[OK] scale_x < threshold but has_appendage: {len(small_with_app)} segs")
assert len(small_with_app) > 0, "scale_x と morphogen が脱結合しているべき"

for seg in chain_morph[3:]:
    assert abs(seg.morphogen - seg.scale_x) > 0.01, \
        f"seg[{seg.index}]: morphogen={seg.morphogen:.4f} should differ from scale_x={seg.scale_x:.4f}"
print("[OK] morphogen != scale_x")

# === 8. Morphogen 条件評価（M フラグ）===
print("\n=== 8. Morphogen condition (M flag) ===")
# M=1 ルール: morphogen >= 1.0 のとき MATERIAL_A
gene_m = Gene(
    rules=[
        Rule(ConditionCode.ALWAYS_TRUE, ActionCode.SCALE_DOWN_SMALL,
             threshold_factor=True, morphogen_condition=False),
        Rule(ConditionCode.N1_SCALE_GE_ONE, ActionCode.MATERIAL_A,
             morphogen_condition=True),  # M=1: morphogen で判定
    ],
    appendage_threshold=2.0, appendage_start_ratio=0.5,
)
chain_m = build_chain(gene_m, max_segments=10)
# morphogen >= 1.0 (T で上昇) の体節は MATERIAL_A
found_a = any(seg.material == "A" for seg in chain_m[1:])
print(f"[OK] M=1 condition fires: MATERIAL_A found = {found_a}")
assert found_a, "M=1 ルールで morphogen >= 1.0 のとき MATERIAL_A が割り当てられるべき"

# 9bit エンコーディング確認
rule_with_m = Rule(ConditionCode.ALWAYS_TRUE, ActionCode.MAINTAIN,
                   threshold_factor=True, ratio_factor=False, morphogen_condition=True)
bits = rule_with_m.to_bits()
assert len(bits) == 9, f"9bit エンコーディング: {bits}"
restored = Rule.from_bits(bits)
assert restored.morphogen_condition is True
print(f"[OK] 9bit encoding: {bits}")

# 旧8bit 後方互換
old_rule = Rule.from_bits("10101010")  # 旧8bit形式
assert old_rule.morphogen_condition is False
print("[OK] Backward compat: 8bit → M=False")

# === 9. Preview save ===
print("\n=== 9. Preview save ===")
_set_props_batch(props,
    mesh_type="SPHERE", scale_axis="Y", segment_uniform_scale=1.0,
    gene_string=gene_app.to_string(), max_appendage_segments=5,
)
bpy.ops.morpho.generate()
preview_path = "/tmp/Morphogenesis/morpho_preview.blend"
bpy.ops.wm.save_as_mainfile(filepath=preview_path)
print(f"[OK] Preview saved: {preview_path}")

unregister()
print("\n" + "=" * 50)
print("全テスト通過！")
print("=" * 50)

"""Geometry Nodes ツリー構築ヘルパー（Rubicon geonodes_utils.py から移植・簡略化）"""
import bpy


def create_node_group(name: str) -> bpy.types.GeometryNodeTree:
    """新規 Geometry Node Tree を作成"""
    tree = bpy.data.node_groups.new(name, type="GeometryNodeTree")
    if not any(n.type == "GROUP_INPUT" for n in tree.nodes):
        tree.nodes.new("NodeGroupInput")
    if not any(n.type == "GROUP_OUTPUT" for n in tree.nodes):
        tree.nodes.new("NodeGroupOutput")
    tree.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    tree.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    return tree


def get_group_input(tree):
    """Group Input ノードを取得"""
    for node in tree.nodes:
        if node.type == "GROUP_INPUT":
            return node
    raise RuntimeError("Group Input ノードが見つかりません")


def get_group_output(tree):
    """Group Output ノードを取得"""
    for node in tree.nodes:
        if node.type == "GROUP_OUTPUT":
            return node
    raise RuntimeError("Group Output ノードが見つかりません")


def add_node(tree, node_type, location=(0, 0), label=""):
    """ツリーにノードを追加"""
    node = tree.nodes.new(type=node_type)
    node.location = location
    if label:
        node.label = label
    return node


def link(tree, from_socket, to_socket):
    """ソケット間をリンク"""
    tree.links.new(from_socket, to_socket)


def set_input(node, input_name, value):
    """ノードの入力にデフォルト値を設定"""
    if isinstance(input_name, int):
        if input_name < len(node.inputs):
            node.inputs[input_name].default_value = value
            return
        raise IndexError(f"インデックス {input_name} がノード '{node.name}' の範囲外です")
    for inp in node.inputs:
        if inp.name == input_name:
            inp.default_value = value
            return
    raise KeyError(f"入力 '{input_name}' がノード '{node.name}' に見つかりません")


def apply_geonodes_modifier(obj, tree):
    """Geometry Nodes モディファイアをオブジェクトに追加"""
    mod = obj.modifiers.new(name=tree.name, type="NODES")
    mod.node_group = tree


def mesh_cube(tree, size=None, size_socket=None, location=(0, 0), label=""):
    """MeshCube ノード"""
    node = add_node(tree, "GeometryNodeMeshCube", location, label or "Cube")
    if size_socket is not None:
        link(tree, size_socket, node.inputs["Size"])
    elif size is not None:
        _, vec = combine_xyz(tree, x=size[0], y=size[1], z=size[2],
                             location=(location[0] - 200, location[1]))
        link(tree, vec, node.inputs["Size"])
    return node, node.outputs["Mesh"]


def mesh_uv_sphere(tree, segments=16, rings=8, radius=0.5,
                   location=(0, 0), label=""):
    """MeshUVSphere ノード"""
    node = add_node(tree, "GeometryNodeMeshUVSphere", location, label or "Sphere")
    set_input(node, "Segments", segments)
    set_input(node, "Rings", rings)
    set_input(node, "Radius", radius)
    return node, node.outputs["Mesh"]


def mesh_cylinder(tree, radius=0.5, depth=1.0, vertices=16,
                  fill_type="TRIANGLE_FAN",
                  location=(0, 0), label=""):
    """MeshCylinder ノード（N-gon回避: TRIANGLE_FAN デフォルト）"""
    node = add_node(tree, "GeometryNodeMeshCylinder", location, label or "Cylinder")
    node.fill_type = fill_type
    set_input(node, "Vertices", vertices)
    set_input(node, "Radius", radius)
    set_input(node, "Depth", depth)
    return node, node.outputs["Mesh"]


def mesh_cone(tree, radius_top=0.0, radius_bottom=0.5, depth=1.0,
              vertices=16, fill_type="TRIANGLE_FAN",
              location=(0, 0), label=""):
    """MeshCone ノード"""
    node = add_node(tree, "GeometryNodeMeshCone", location, label or "Cone")
    node.fill_type = fill_type
    set_input(node, "Vertices", vertices)
    set_input(node, "Radius Top", radius_top)
    set_input(node, "Radius Bottom", radius_bottom)
    set_input(node, "Depth", depth)
    return node, node.outputs["Mesh"]


def combine_xyz(tree, x=None, y=None, z=None, location=(0, 0), label=""):
    """CombineXYZ ノード"""
    node = add_node(tree, "ShaderNodeCombineXYZ", location, label)
    for axis_name, val in [("X", x), ("Y", y), ("Z", z)]:
        if val is None:
            continue
        if isinstance(val, (int, float)):
            node.inputs[axis_name].default_value = float(val)
        else:
            link(tree, val, node.inputs[axis_name])
    return node, node.outputs[0]


def transform(tree, geometry_socket, translation=None, rotation=None, scale=None,
              location=(0, 0), label=""):
    """Transform ノード"""
    node = add_node(tree, "GeometryNodeTransform", location, label or "Transform")
    link(tree, geometry_socket, node.inputs["Geometry"])
    if translation is not None:
        link(tree, translation, node.inputs["Translation"])
    if rotation is not None:
        link(tree, rotation, node.inputs["Rotation"])
    if scale is not None:
        link(tree, scale, node.inputs["Scale"])
    return node, node.outputs["Geometry"]


def set_material(tree, mesh_socket, material, location=(0, 0), label="",
                 selection_socket=None):
    """SetMaterial ノード"""
    node = add_node(tree, "GeometryNodeSetMaterial", location, label or "SetMaterial")
    node.inputs["Material"].default_value = material
    link(tree, mesh_socket, node.inputs["Geometry"])
    if selection_socket is not None:
        link(tree, selection_socket, node.inputs["Selection"])
    return node, node.outputs["Geometry"]


def join_geometry(tree, *geometry_sockets, location=(0, 0), label=""):
    """JoinGeometry — 複数ジオメトリを結合"""
    node = add_node(tree, "GeometryNodeJoinGeometry", location, label or "Join")
    for sock in geometry_sockets:
        link(tree, sock, node.inputs["Geometry"])
    return node, node.outputs["Geometry"]

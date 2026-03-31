bl_info = {
    "name": "Blockout Technical Mesh Check",
    "author": "Codex",
    "version": (1, 2, 0),
    "blender": (3, 3, 0),
    "location": "View3D > Sidebar > Blockout",
    "description": "Технический чеклист проверки меша для hard-surface blockout",
    "category": "3D View",
}

import bmesh
import bpy
from bpy.props import BoolProperty, EnumProperty, PointerProperty, StringProperty
from bpy.types import Operator, Panel, PropertyGroup


CHECK_SECTIONS = [
    (
        "1. Трансформации",
        [
            ("s1_scale_111", "Scale = 1,1,1"),
            ("s1_rot_000", "Rotation = 0,0,0"),
            ("s1_transform_applied", "Transform frozen / applied"),
            ("s1_no_negative", "Нет negative scale"),
            ("s1_no_non_uniform", "Нет non-uniform scale"),
        ],
    ),
    (
        "2. Пивоты",
        [
            ("s2_pivot_logic", "Pivot в логичном месте"),
            ("s2_not_world_zero", "Pivot не в мире 0,0,0 без причины"),
            ("s2_orientation", "Pivot orientation выровнен"),
            ("s2_movable_parts", "Подвижные части имеют отдельный pivot"),
            ("s2_reset_rotation", "Reset pivot rotation"),
        ],
    ),
    (
        "3. Нормали и шейдинг",
        [
            ("s3_normals_out", "Все нормали направлены наружу"),
            ("s3_no_flipped", "Нет flipped faces"),
            ("s3_hard_edges", "Hard edges читаются корректно"),
            ("s3_no_gradients", "Нет shading gradients на плоскостях"),
            ("s3_no_black", "Нет black artifacts"),
            ("s3_no_avg_corners", "Нет averaged shading на углах"),
            ("s3_matcap_test", "Проверено matcap / studio light"),
        ],
    ),
    (
        "4. Геометрия",
        [
            ("s4_no_ngon_important", "Нет n-gons на важных формах"),
            ("s4_no_ngon_cyl", "Нет n-gons на цилиндрах"),
            ("s4_no_ngon_round", "Нет n-gons на скруглениях"),
            ("s4_ngon_caps_only", "N-gons только на плоских заглушках"),
            ("s4_no_thin_tris", "Нет тонких треугольников"),
            ("s4_no_skinny_poly", "Нет длинных skinny полигонов"),
            ("s4_no_boolean_lamella", "Нет ламелей после boolean"),
        ],
    ),
    (
        "5. Пересечения",
        [
            ("s5_no_self_intersection", "Нет self-intersection"),
            ("s5_no_overlapping", "Нет overlapping faces"),
            ("s5_no_zfighting", "Нет z-fighting"),
            ("s5_no_doubles", "Нет doubled vertices"),
            ("s5_merge_checked", "Merge distance проверен"),
        ],
    ),
    (
        "6. Толщина",
        [
            ("s6_no_single_plane", "Нет single-plane где нужна толщина"),
            ("s6_shell_thickness", "Shell имеет толщину"),
            ("s6_holes_not_paper", "Отверстия не бумажные"),
        ],
    ),
    (
        "7. Топология под HP",
        [
            ("s7_cyl_sides", "Цилиндры имеют достаточно сторон"),
            ("s7_mult_4", "Сегменты кратны 4 (желательно)"),
            ("s7_predictable_flow", "Edge flow предсказуем для bevel"),
            ("s7_no_pinching", "Нет будущих pinching мест"),
            ("s7_boolean_ready", "Boolean-ready"),
        ],
    ),
    (
        "8. Сглаживание",
        [
            ("s8_autosmooth_not_hiding", "Auto smooth не скрывает ошибки"),
            ("s8_no_weighted", "Нет поддержки shading через weighted normals"),
            ("s8_no_bevel_shader", "Нет bevel shader костылей"),
            ("s8_geometry_only", "Только геометрия"),
        ],
    ),
    (
        "9. Инстансы и дубликаты",
        [
            ("s9_no_random_instances", "Нет случайных instances"),
            ("s9_mirror_applied", "Mirror применён"),
            ("s9_history_clean", "History очищена"),
            ("s9_no_construction_history", "Нет construction history"),
        ],
    ),
    (
        "10. Имена",
        [
            ("s10_meaningful_names", "Объекты имеют осмысленные имена"),
            ("s10_no_cube001", "Нет default Cube001"),
            ("s10_no_duplicates", "Нет дубликатов имён"),
            ("s10_logical_groups", "Логическая группировка"),
        ],
    ),
    (
        "11. Целостность меша (Mesh Integrity)",
        [
            ("s11_no_double_vertices", "Нет double vertices"),
            ("s11_no_unwelded", "Нет несшитых вершин внутри элемента"),
            ("s11_single_shell", "Один элемент = одна непрерывная оболочка"),
            ("s11_no_internal_faces", "Нет внутренних полигонов"),
            ("s11_no_lamina", "Нет lamina faces"),
            ("s11_no_non_manifold", "Нет non-manifold геометрии"),
            ("s11_no_multi_edges", "Нет edges с более чем 2 полигонами"),
            ("s11_no_zero_area", "Нет нулевой площади полигонов"),
            ("s11_no_loose", "Нет висящих рёбер и вершин"),
            ("s11_no_boolean_gaps", "Нет скрытых разрывов после boolean"),
        ],
    ),
]

INTEGRITY_SELECT_MODES = [
    ("NON_MANIFOLD", "Select Non-Manifold", "Выделяет non-manifold рёбра/вершины"),
    ("LOOSE", "Select Loose", "Выделяет висящие вершины/рёбра"),
    ("DOUBLES", "Select Doubles", "Выделяет дубликаты вершин по расстоянию"),
    ("INTERIOR", "Select Interior Faces", "Выделяет внутренние полигоны"),
    ("ZERO_AREA", "Select Zero Area Faces", "Выделяет полигоны нулевой площади"),
    ("MULTI_FACE_EDGES", "Edges > 2 Faces", "Выделяет рёбра с более чем 2 полигонами"),
    ("UNWELDED", "Select Unwelded Vertices", "Выделяет несшитые (split) вершины"),
]

CHECK_ITEMS = [item for _section, items in CHECK_SECTIONS for item in items]


class BlockoutTechProps(PropertyGroup):
    status_message: StringProperty(name="Статус", default="Готово к технической проверке")
    integrity_mode: EnumProperty(
        name="Integrity Select",
        description="Какую проблему целостности меша выделить",
        items=INTEGRITY_SELECT_MODES,
        default="NON_MANIFOLD",
    )


def _set_edit_mode(context):
    obj = context.active_object
    if not obj or obj.type != "MESH":
        return None

    if context.mode != "EDIT_MESH":
        bpy.ops.object.mode_set(mode="EDIT")

    return obj


def _clear_selection(bm):
    for v in bm.verts:
        v.select = False
    for e in bm.edges:
        e.select = False
    for f in bm.faces:
        f.select = False


def _select_doubles(bm, distance):
    result = bmesh.ops.find_doubles(bm, verts=bm.verts, dist=distance)
    doubles = {pair[0] for pair in result.get("targetmap", {}).items()}
    for vert in doubles:
        vert.select = True
    return len(doubles)


def _select_interior_faces(bm):
    count = 0
    for face in bm.faces:
        if all(edge.is_manifold and len(edge.link_faces) >= 2 for edge in face.edges):
            face.select = True
            count += 1
    return count


def _select_zero_area_faces(bm, eps=1e-12):
    count = 0
    for face in bm.faces:
        if face.calc_area() <= eps:
            face.select = True
            count += 1
    return count


def _select_multi_face_edges(bm):
    count = 0
    for edge in bm.edges:
        if len(edge.link_faces) > 2:
            edge.select = True
            count += 1
    return count


def _select_unwelded_vertices(bm):
    edge_key_usage = {}
    for face in bm.faces:
        v_count = len(face.verts)
        for idx in range(v_count):
            va = face.verts[idx]
            vb = face.verts[(idx + 1) % v_count]
            edge_key = tuple(sorted((tuple(round(c, 7) for c in va.co), tuple(round(c, 7) for c in vb.co))))
            edge_key_usage[edge_key] = edge_key_usage.get(edge_key, 0) + 1

    count = 0
    for vert in bm.verts:
        linked_edges = vert.link_edges
        if not linked_edges:
            continue
        local_boundary = 0
        for edge in linked_edges:
            va, vb = edge.verts
            edge_key = tuple(sorted((tuple(round(c, 7) for c in va.co), tuple(round(c, 7) for c in vb.co))))
            if edge_key_usage.get(edge_key, 0) == 1:
                local_boundary += 1
        if local_boundary >= 2 and not vert.is_boundary:
            vert.select = True
            count += 1
    return count


for prop_name, _label in CHECK_ITEMS:
    setattr(BlockoutTechProps, prop_name, BoolProperty(default=False))


class BLOCKOUT_OT_select_integrity_issue(Operator):
    bl_idname = "blockout.select_integrity_issue"
    bl_label = "Select Mesh Issue"
    bl_description = "Выделяет проблемные элементы меша в Edit Mode"

    merge_distance: bpy.props.FloatProperty(
        name="Merge Distance",
        default=0.0001,
        min=0.0,
        description="Порог для поиска дублей вершин",
    )

    def execute(self, context):
        props = context.scene.blockout_tech
        obj = _set_edit_mode(context)
        if obj is None:
            self.report({'WARNING'}, "Выберите активный Mesh объект")
            return {'CANCELLED'}

        bm = bmesh.from_edit_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        _clear_selection(bm)

        mode = props.integrity_mode
        selected_count = 0

        if mode == "NON_MANIFOLD":
            for edge in bm.edges:
                if not edge.is_manifold:
                    edge.select = True
                    selected_count += 1
        elif mode == "LOOSE":
            for vert in bm.verts:
                if not vert.link_edges:
                    vert.select = True
                    selected_count += 1
            for edge in bm.edges:
                if len(edge.link_faces) == 0:
                    edge.select = True
                    selected_count += 1
        elif mode == "DOUBLES":
            selected_count = _select_doubles(bm, self.merge_distance)
        elif mode == "INTERIOR":
            selected_count = _select_interior_faces(bm)
        elif mode == "ZERO_AREA":
            selected_count = _select_zero_area_faces(bm)
        elif mode == "MULTI_FACE_EDGES":
            selected_count = _select_multi_face_edges(bm)
        elif mode == "UNWELDED":
            selected_count = _select_unwelded_vertices(bm)

        bmesh.update_edit_mesh(obj.data, loop_triangles=False, destructive=False)

        props.status_message = f"Выделено проблемных элементов: {selected_count} ({mode})"
        self.report({'INFO'}, props.status_message)
        return {'FINISHED'}


class BLOCKOUT_OT_tech_autocheck(Operator):
    bl_idname = "blockout.tech_autocheck"
    bl_label = "Тех. автотест"
    bl_description = "Проверяет объективные параметры: transforms, scale и имена"

    def execute(self, context):
        props = context.scene.blockout_tech
        obj = context.active_object

        if not obj or obj.type != "MESH":
            props.status_message = "Выберите активный Mesh объект для автотеста"
            self.report({'WARNING'}, props.status_message)
            return {'CANCELLED'}

        eps = 1e-5
        sx, sy, sz = obj.scale
        rx, ry, rz = obj.rotation_euler

        props.s1_scale_111 = (
            abs(sx - 1.0) < eps and abs(sy - 1.0) < eps and abs(sz - 1.0) < eps
        )
        props.s1_rot_000 = abs(rx) < eps and abs(ry) < eps and abs(rz) < eps
        props.s1_transform_applied = props.s1_scale_111 and props.s1_rot_000
        props.s1_no_negative = sx > 0 and sy > 0 and sz > 0
        props.s1_no_non_uniform = abs(sx - sy) < eps and abs(sy - sz) < eps

        props.s10_no_cube001 = not obj.name.lower().startswith("cube")

        all_names = [o.name for o in context.scene.objects]
        duplicate_count = len(all_names) - len(set(all_names))
        props.s10_no_duplicates = duplicate_count == 0

        if props.s1_transform_applied and props.s1_no_non_uniform and props.s1_no_negative:
            props.status_message = "Автотест: трансформации в порядке, продолжайте ручной техчек"
            self.report({'INFO'}, props.status_message)
        else:
            props.status_message = "Автотест: исправьте трансформации (scale/rotation/non-uniform)"
            self.report({'WARNING'}, props.status_message)

        return {'FINISHED'}


class BLOCKOUT_OT_tech_reset(Operator):
    bl_idname = "blockout.tech_reset"
    bl_label = "Сбросить чеклист"

    def execute(self, context):
        props = context.scene.blockout_tech
        for prop_name, _ in CHECK_ITEMS:
            setattr(props, prop_name, False)
        props.status_message = "Чеклист сброшен"
        return {'FINISHED'}


class VIEW3D_PT_blockout_tech_check(Panel):
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Blockout"
    bl_label = "BLOCKOUT — TECHNICAL MESH CHECK"

    def draw(self, context):
        layout = self.layout
        props = context.scene.blockout_tech

        done = sum(1 for prop_name, _ in CHECK_ITEMS if getattr(props, prop_name))
        total = len(CHECK_ITEMS)
        percent = int(done / total * 100) if total else 0

        hdr = layout.box()
        hdr.label(text=f"Прогресс: {done}/{total} ({percent}%)", icon="CHECKMARK")
        hdr.label(text=props.status_message, icon="INFO")

        row = layout.row(align=True)
        row.operator("blockout.tech_autocheck", icon="SHADERFX")
        row.operator("blockout.tech_reset", icon="LOOP_BACK")

        integrity = layout.box()
        integrity.label(text="Integrity Select Tools")
        integrity.prop(props, "integrity_mode", text="Mode")
        integrity.operator("blockout.select_integrity_issue", icon="RESTRICT_SELECT_OFF")

        for section_name, items in CHECK_SECTIONS:
            box = layout.box()
            box.label(text=section_name)
            for prop_name, label in items:
                box.prop(props, prop_name, text=label)

        quick = layout.box()
        quick.label(text="Быстрые тесты:")
        quick.label(text="• Merge by distance: не должно ничего схлопываться")
        quick.label(text="• Select non-manifold: должно быть пусто")
        quick.label(text="• Delete loose: ничего не удаляется")
        quick.label(text="• Shade smooth + matcap: нет полос")
        quick.label(text="• Solidify preview: меш не рвётся")


classes = (
    BlockoutTechProps,
    BLOCKOUT_OT_select_integrity_issue,
    BLOCKOUT_OT_tech_autocheck,
    BLOCKOUT_OT_tech_reset,
    VIEW3D_PT_blockout_tech_check,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.blockout_tech = PointerProperty(type=BlockoutTechProps)


def unregister():
    del bpy.types.Scene.blockout_tech
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()

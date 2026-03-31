# Blockout Technical Mesh Check (Blender Add-on)

Аддон добавляет панель `BLOCKOUT — TECHNICAL MESH CHECK` в `View3D > Sidebar > Blockout`.

## Что изменено

Теперь чеклист ориентирован именно на **техническую валидацию меша**, а не на художественный blockout:

- 11 разделов:
  1. Трансформации
  2. Пивоты
  3. Нормали и шейдинг
  4. Геометрия
  5. Пересечения
  6. Толщина
  7. Топология под HP
  8. Сглаживание
  9. Инстансы и дубликаты
  10. Имена
  11. Целостность меша
- Прогресс выполнения чеклиста в процентах.
- `Тех. автотест` для объективных проверок на активном mesh-объекте:
  - Transform applied (Scale/Rotation)
  - Negative / non-uniform scale
  - Проверка имени `Cube*`
  - Базовая проверка дублей имён объектов
- `Select Mesh Issue` — **реально выделяет проблемные элементы** в Edit Mode:
  - Non-manifold
  - Loose geometry
  - Doubles (по merge distance)
  - Interior faces
  - Zero-area faces
  - Edges с более чем 2 полигонами
  - Unwelded (split) vertices
- `Сбросить чеклист`.

## Установка

1. Blender → `Edit > Preferences > Add-ons > Install...`
2. Выбери `blockout_checklist_addon.py`
3. Включи `Blockout Technical Mesh Check`
4. Открой `3D View > Sidebar (N) > Blockout`

## Примечание

Часть пунктов неизбежно остаётся ручной проверкой, так как требует инженерного и визуального суждения.

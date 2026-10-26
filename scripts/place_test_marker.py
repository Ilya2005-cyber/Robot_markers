
from pathlib import Path

# Главная папка проекта
PROJECT = Path.home() / "warehouse_project"

# Исходный мир
source = PROJECT / "worlds" / "warehouse_base.world"

# Мир, который мы создаём
output = PROJECT / "worlds" / "warehouse_hd13_test.world"

# STL стеллажа
mesh_path = PROJECT / "meshes" / "Стеллаж 6.stl"

# Проверяем существование файлов
if not source.is_file():
    raise FileNotFoundError(f"Не найден мир: {source}")

if not mesh_path.is_file():
    raise FileNotFoundError(f"Не найден STL: {mesh_path}")

# Читаем исходный мир
world_text = source.read_text(encoding="utf-8")

# Положение тестового маркера
marker_x = -0.100
marker_y = 3.0005
marker_z = 0.120

marker_sdf = f"""
    <include>
      <uri>/home/ilya/warehouse_project/models/stag_hd13_test</uri>
      <name>hd13_rack4_shelf1</name>
      <pose>{marker_x} {marker_y} {marker_z} 1.570796 0 0</pose>
    </include>
"""

if "</world>" not in world_text:
    raise ValueError("Не найден закрывающий тег </world>")

# Добавляем маркер в копию мира
new_world = world_text.replace(
    "</world>",
    marker_sdf + "\n  </world>",
    1
)

# Сохраняем результат
output.write_text(new_world, encoding="utf-8")


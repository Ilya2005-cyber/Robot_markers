#!/usr/bin/env python3

from pathlib import Path
import hashlib
import shutil
import xml.etree.ElementTree as ET

# 1. Пути к проекту
project = Path(__file__).resolve().parent.parent
source_world = project / "worlds" / "warehouse_base.world"
output_world = project / "worlds" / "warehouse_hd13_36.world"
hd = project / "models" / "materials" / "textures" / "HD13"
models_dir = project / "models" / "models_markers"

# 2. Положение маркеров, подобранное в Gazebo
local_x = -0.016

local_y_row_1 = 0.0045
roll_row_1 = -1.570796

local_y_row_2 = -0.6045
roll_row_2 = 1.570796

shelf_z_values = [0.30, 0.66, 1.02, 1.365, 1.695, 1.960]

N_RACKS = 6
N_MARKERS = N_RACKS * len(shelf_z_values)

# Создаем уникальную модель для одного маркера HD13
def create_marker_model(marker_id, image_path):


    label = f"{marker_id:03d}"
    model_name = f"stag_hd13_{label}"

    model_dir = models_dir / model_name
    scripts_dir = model_dir / "materials" / "scripts"
    textures_dir = model_dir / "materials" / "textures"

    scripts_dir.mkdir(parents=True, exist_ok=True)
    textures_dir.mkdir(parents=True, exist_ok=True)

    # 1. Копируем изображение соответствующего ID
    image_filename = f"hd13_{label}.png"
    shutil.copy2(image_path, textures_dir / image_filename)

    # 2. Создаём model.config
    config_text = f"""
<model>
  <name>{model_name}</name>
  <version>1.0</version>
  <sdf version="1.7">model.sdf</sdf>
  <description>STag HD13 ID {marker_id}</description>
</model>
"""

    (model_dir / "model.config").write_text(
        config_text, encoding="utf-8"
    )

    # 3. Создаём уникальный материал
    material_name = f"STag/HD13_{label}"

    material_text = f"""
material {material_name}
{{
    technique
    {{
        pass
        {{
            lighting off

            texture_unit
            {{
                texture ../textures/{image_filename}
            }}
        }}
    }}
}}
"""

    (scripts_dir / "stag.material").write_text(
        material_text, encoding="utf-8"
    )

    # 4. Создаём model.sdf
    sdf_text = f"""
<sdf version="1.7">
  <model name="{model_name}">
    <static>true</static>

    <link name="marker_link">

      <visual name="backing">
        <pose>0 0 -0.001 0 0 0</pose>
        <geometry>
          <box>
            <size>0.092 0.092 0.002</size>
          </box>
        </geometry>
        <material>
          <ambient>1 1 1 1</ambient>
          <diffuse>1 1 1 1</diffuse>
        </material>
      </visual>

      <visual name="marker_image">
        <pose>0 0 0.001 0 0 0</pose>

        <geometry>
          <plane>
            <normal>0 0 1</normal>
            <size>0.09 0.09</size>
          </plane>
        </geometry>

        <material>
          <script>
            <uri>model://{model_name}/materials/scripts</uri>
            <uri>model://{model_name}/materials/textures</uri>
            <name>{material_name}</name>
          </script>
        </material>

      </visual>

    </link>
  </model>
</sdf>
"""
    ET.fromstring(sdf_text)
    (model_dir / "model.sdf").write_text(
        sdf_text, encoding="utf-8"
    )

    return model_dir


def main():
    # 3. Проверяем входные файлы до создания результатов
    necessary = [source_world]
    for path in necessary:
        if not path.is_file():
            raise FileNotFoundError(f"Не найден файл: {path}")

    images = []
    missing = []
    for marker_id in range(N_MARKERS):
        image = hd / f"{marker_id:05d}.png"

        if image.is_file():
            images.append(image)
        else:
            missing.append(image.name)

    if missing:
        raise FileNotFoundError(
            f"Не найдены изображения: {', '.join(missing)}"
        )

    hashes = []
    for image in images:
        data = image.read_bytes()
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError(f"Файл не является PNG: {image}")
        hashes.append(hashlib.sha256(data).hexdigest())
    if len(set(hashes)) != N_MARKERS:
        raise ValueError("Есть одинаковые PNG. Каждому ID требуется свой код HD13.")

    # 4. Читаем координаты стеллажей из исходного SDF
    root = ET.parse(source_world).getroot()
    world = root.find("world")
    if world is None:
        raise ValueError("Не найден тег <world> в warehouse_base.world")

    rack_positions = {}
    for rack_number in range(1, N_RACKS + 1):
        rack_name = f"warehouse_racks_{rack_number}"
        rack_model = world.find(f"./model[@name='{rack_name}']")
        if rack_model is None:
            raise ValueError(f"Не найден стеллаж: {rack_name}")
        pose_text = rack_model.findtext("pose")
        if not pose_text:
            raise ValueError(f"У стеллажа {rack_name} нет <pose>")
        values = [float(v) for v in pose_text.split()]
        if len(values) != 6:
            raise ValueError(f"Некорректный <pose> у стеллажа {rack_name}")
        rack_x, rack_y, rack_z, roll, pitch, yaw = values
        if any(abs(v) > 0.00001 for v in (roll, pitch, yaw)):
            raise ValueError(
                f"Стеллаж {rack_name} повернут. Для него нужно учитывать вращение "
                "при вычислении мировых координат маркера."
            )
        rack_positions[rack_number] = (rack_x, rack_y, rack_z)

    # 5. генерируем SDF-модели и XML-вставки
    marker_blocks = []
    for rack_number in range(1, N_RACKS + 1):
        rack_x, rack_y, rack_z = rack_positions[rack_number]
        if rack_number in (1, 2, 3):
            local_y = local_y_row_1
            marker_roll = roll_row_1
        else:
            local_y = local_y_row_2
            marker_roll = roll_row_2

        for shelf_number, local_z in enumerate(shelf_z_values, start=1):
            marker_id = (rack_number - 1) * len(shelf_z_values) + (shelf_number - 1)
            create_marker_model(marker_id, images[marker_id])
            marker_x = rack_x + local_x
            marker_y = rack_y + local_y
            marker_z = rack_z + local_z
            marker_name = f"hd13_rack{rack_number}_shelf{shelf_number}"
            marker_block = f"""
    <include>
      <uri>model://stag_hd13_{marker_id:03d}</uri>
      <name>{marker_name}</name>
      <pose>{marker_x:.6f} {marker_y:.6f} {marker_z:.6f} {marker_roll:.6f} 0 0</pose>
    </include>
"""
            marker_blocks.append(marker_block)
    # 6. Сохраняем новый мир; исходный warehouse_base.world не изменяем
    world_text = source_world.read_text(encoding="utf-8")
    world_text = world_text.replace("/home/ilya/warehouse_project/", str(project) + "/")
    if "</world>" not in world_text:
        raise ValueError("В исходном SDF нет закрывающего тега </world>")
    new_world = world_text.replace("</world>", "".join(marker_blocks) + "\n  </world>", 1)
    ET.fromstring(new_world)  # проверим корректность XML
    output_world.write_text(new_world, encoding="utf-8")

    print(f"Новый мир создан: {output_world}")



if __name__ == "__main__":
    main()
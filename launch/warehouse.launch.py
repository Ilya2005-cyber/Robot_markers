from pathlib import Path

from launch import LaunchDescription
from launch.actions import (
    SetEnvironmentVariable,
    TimerAction,
    ExecuteProcess,
)
from launch.substitutions import Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    # Корневая папка нашего проекта
    project_dir = Path(__file__).resolve().parent.parent

    # Пути к файлам
    world_file = project_dir / "worlds" / "warehouse_hd13_36.world"
    xacro_file = project_dir / "robot_description" / "urdf" / "warehouse_r2d2.urdf.xacro"

    # Пути для поиска моделей Gazebo
    model_path = str(project_dir / "models" / "models_markers")

    gazebo_models = SetEnvironmentVariable(
        name="GAZEBO_MODEL_PATH",
        value=model_path
    )

    # Преобразуем Xacro в URDF
    robot_description = ParameterValue(
        Command(["xacro ", str(xacro_file)]),
        value_type=str
    )

    # Узел публикации описания робота и TF
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[
            {"robot_description": robot_description,
             "use_sim_time": True}
        ]
    )

    # Запуск Gazebo Classic с нашим складом
    gazebo = ExecuteProcess(
        cmd=[
            "gazebo",
            "--verbose",
            "-s", "libgazebo_ros_init.so",
            "-s", "libgazebo_ros_factory.so",
            str(world_file),
        ],
        output="screen",
    )
    # Создание робота по описанию из ROS 2
    spawn_robot = Node(
        package="gazebo_ros",
        executable="spawn_entity.py",
        name="spawn_warehouse_robot",
        output="screen",
        arguments=[
            "-topic", "robot_description",
            "-entity", "warehouse_r2d2",
            "-x", "-2.0",
            "-y", "1.5",
            "-z", "0.60",
        ]
    )

    return LaunchDescription([
        gazebo_models,
        gazebo,
        robot_state_publisher,
        TimerAction(
            period=1.0,
            actions=[spawn_robot]
        ),
    ])

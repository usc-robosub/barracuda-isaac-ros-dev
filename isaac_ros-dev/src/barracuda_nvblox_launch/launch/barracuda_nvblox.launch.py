#!/usr/bin/env python3
"""Barracuda nvblox launch.

This launch follows the structure used by the nvblox_examples_bringup
examples but only launches the nvblox composable node. It assumes a ZED
driver is already running in another container and will subscribe to the
standard ZED topics.
"""
from typing import List, Tuple

from launch import Action, LaunchDescription
from launch_ros.descriptions import ComposableNode
import isaac_ros_launch_utils as lu

from nvblox_ros_python_utils.nvblox_launch_utils import NvbloxMode, NvbloxCamera
from nvblox_ros_python_utils.nvblox_constants import NVBLOX_CONTAINER_NAME


def get_zed_remappings(mode: NvbloxMode) -> List[Tuple[str, str]]:
    assert mode is NvbloxMode.static, 'Nvblox only supports static mode for ZED cameras.'
    remappings = []
    remappings.append(('camera_0/depth/image', '/zed/zed_node/depth/depth_registered'))
    remappings.append(('camera_0/depth/camera_info', '/zed/zed_node/depth/camera_info'))
    remappings.append(('camera_0/color/image', '/zed/zed_node/rgb/image_rect_color'))
    remappings.append(('camera_0/color/camera_info', '/zed/zed_node/rgb/camera_info'))
    remappings.append(('pose', '/zed/zed_node/pose'))
    return remappings


def get_isaac_sim_remappings(mode: NvbloxMode, num_cameras: int, lidar: bool) -> List[Tuple[str, str]]:
    remappings: List[Tuple[str, str]] = []
    camera_names = ['front_stereo_camera', 'left_stereo_camera', 'right_stereo_camera'][:num_cameras]
    for i, name in enumerate(camera_names):
        remappings.append((f'camera_{i}/depth/image', f'{name}/depth/ground_truth'))
        remappings.append((f'camera_{i}/depth/camera_info', f'{name}/left/camera_info'))
        remappings.append((f'camera_{i}/color/image', f'{name}/left/image_raw'))
        remappings.append((f'camera_{i}/color/camera_info', f'{name}/left/camera_info'))
    if mode is NvbloxMode.people_segmentation:
        remappings.append(('camera_0/mask/image', '/semantic_conversion/front_stereo_camera/semantic_mono8'))
        remappings.append(('camera_0/mask/camera_info', '/front_stereo_camera/left/camera_info'))
    if lidar:
        remappings.append(('pointcloud', '/front_3d_lidar/point_cloud'))
    return remappings


def get_realsense_remappings(mode: NvbloxMode, num_cameras: int = 1) -> List[Tuple[str, str]]:
    remappings: List[Tuple[str, str]] = []
    for i in range(0, num_cameras):
        if i == 0:
            remappings.append((f'camera_{i}/depth/image', f'/camera{i}/realsense_splitter_node/output/depth'))
            remappings.append((f'camera_{i}/depth/camera_info', f'/camera{i}/depth/camera_info'))
        else:
            remappings.append((f'camera_{i}/depth/image', f'/camera{i}/depth/image_rect_raw'))
            remappings.append((f'camera_{i}/depth/camera_info', f'/camera{i}/depth/camera_info'))

        if mode is NvbloxMode.people_segmentation:
            remappings.append((f'camera_{i}/color/image', f'/camera{i}/segmentation/image_resized'))
            remappings.append((f'camera_{i}/color/camera_info', f'/camera{i}/segmentation/camera_info_resized'))
            remappings.append((f'camera_{i}/mask/image', f'/camera{i}/segmentation/people_mask'))
            remappings.append((f'camera_{i}/mask/camera_info', f'/camera{i}/segmentation/camera_info_resized'))
        else:
            remappings.append((f'camera_{i}/color/image', f'/camera{i}/color/image_raw'))
            remappings.append((f'camera_{i}/color/camera_info', f'/camera{i}/color/camera_info'))

            if mode is NvbloxMode.people_detection:
                remappings.append((f'camera_{i}/mask/image', f'/camera{i}/detection/people_mask'))
                remappings.append((f'camera_{i}/mask/camera_info', f'/camera{i}/color/camera_info'))

    return remappings


def add_nvblox(args: lu.ArgumentContainer) -> List[Action]:
    mode = NvbloxMode[args.mode]
    camera = NvbloxCamera[args.camera]
    num_cameras = int(args.num_cameras) if hasattr(args, 'num_cameras') else 1
    use_lidar = lu.is_true(args.lidar) if hasattr(args, 'lidar') else False

    # Support multiple camera backends by selecting remappings accordingly.
    if camera is NvbloxCamera.isaac_sim:
        remappings = get_isaac_sim_remappings(mode, num_cameras, use_lidar)
        assert num_cameras <= 3, 'Isaac Sim example supports up to 3 cameras.'
    elif camera is NvbloxCamera.realsense:
        remappings = get_realsense_remappings(mode, num_cameras)
        assert num_cameras >= 1, 'Realsense example requires at least 1 camera.'
    elif camera is NvbloxCamera.multi_realsense:
        remappings = get_realsense_remappings(mode, num_cameras)
    elif camera in [NvbloxCamera.zed2, NvbloxCamera.zedx]:
        remappings = get_zed_remappings(mode)
        assert num_cameras == 1, 'Zed example can only run with 1 camera.'
        assert not use_lidar, 'Can not run lidar for zed example.'
    else:
        # Fallback: don't apply remappings; user can remap externally.
        remappings = []

    parameters = []
    # Only provide minimal runtime parameters here; omit example YAMLs.
    parameters.append({'num_cameras': num_cameras})
    parameters.append({'use_lidar': use_lidar})

    nvblox_node = ComposableNode(
        name='nvblox_node',
        package='nvblox_ros',
        plugin='nvblox::NvbloxNode',
        remappings=remappings,
        parameters=parameters,
    )

    actions: List[Action] = []
    if args.run_standalone:
        actions.append(lu.component_container(args.container_name))
    actions.append(lu.load_composable_nodes(args.container_name, [nvblox_node]))
    actions.append(lu.log_info([
        "Starting nvblox with the '", str(camera), "' camera in '", str(mode), "' mode."
    ]))
    return actions


def generate_launch_description() -> LaunchDescription:
    args = lu.ArgumentContainer()
    args.add_arg('mode', 'static')
    args.add_arg('camera', 'zed2')
    args.add_arg('num_cameras', 1)
    args.add_arg('lidar', 'False')
    args.add_arg('container_name', NVBLOX_CONTAINER_NAME)
    args.add_arg('run_standalone', 'False')

    args.add_opaque_function(add_nvblox)
    return LaunchDescription(args.get_launch_actions())

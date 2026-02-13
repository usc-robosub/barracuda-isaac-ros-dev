#!/usr/bin/env bash
set -e

# Workspace entrypoint used in the barracuda nvblox image.
# If RUN_BARRACUDA_NVBLOX=1 is set, build the package and launch nvblox.

ISAAC_WS=${ISAAC_ROS_WS:-/workspaces/isaac_ros-dev}

cd "$ISAAC_WS" || exit 1

# Ensure ROS_DOMAIN_ID is set to 0 when not provided
if [[ -z "${ROS_DOMAIN_ID:-}" ]]; then
  export ROS_DOMAIN_ID=0
fi

# Source base ROS setup if available
if [[ -f /opt/ros/humble/setup.bash ]]; then
  # shellcheck disable=SC1091
  . /opt/ros/humble/setup.bash
else
  echo "[entrypoint][warn] /opt/ros/humble/setup.bash not found" >&2
fi

# Source workspace setup if it exists (so interactive shells see overlays)
if [[ -f install/setup.bash ]]; then
  # shellcheck disable=SC1091
  source install/setup.bash
else
  echo "[entrypoint][warn] install/setup.bash not found (build may be required)" >&2
fi

if [[ "${RUN_BARRACUDA_NVBLOX:-0}" == "1" ]]; then
  echo "[entrypoint] Building barracuda_nvblox_launch..."
  if ! colcon build --packages-select barracuda_nvblox_launch; then
    echo "[entrypoint][error] colcon build failed for barracuda_nvblox_launch" >&2
    exit 1
  fi
  echo "[entrypoint] Sourcing workspace..."
  # shellcheck disable=SC1091
  if ! . install/setup.bash; then
    echo "[entrypoint][error] Failed to source install/setup.bash" >&2
    exit 1
  fi
  echo "[entrypoint] Launching barracuda_nvblox.launch.py"
  if ! ros2 launch barracuda_nvblox_launch barracuda_nvblox.launch.py; then
    exit_code=$?
    echo "[entrypoint][error] nvblox launch failed with exit code ${exit_code}" >&2
    exit ${exit_code}
  fi
  echo "[entrypoint] nvblox launch exited successfully"
  exit 0
fi

# If no command provided, drop to an interactive shell so the container
# doesn't immediately exit. If a command is provided, exec it.
if [[ $# -eq 0 ]]; then
  exec /bin/bash
else
  exec "$@"
fi

# file: ~/catkin_ws/src/multi_boat_control/setup_env.sh

#!/bin/bash

# --- 在这里修改IP地址 ---
MASTER_IP=192.168.202.147  # boat1的IP
#BOAT_IP=192.168.1.101   # 如果在boat1上运行，就填boat1的IP
BOAT_IP=192.168.202.147   # 如果在boat2上运行，就填boat2的IP

# --- 以下内容保持不变 ---
export ROS_MASTER_URI=http://${MASTER_IP}:11311
export ROS_IP=${BOAT_IP}

echo "ROS network configured:"
echo "  -> ROS_MASTER_URI=${ROS_MASTER_URI}"
echo "  -> ROS_IP=${ROS_IP}"

source ~/multi_boat_control/devel/setup.bash
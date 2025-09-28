#!/bin/bash

# Multi-Boat Control System Setup Script - Phase 2
# 项目设置和环境配置脚本 (Enhanced for Complete Control Architecture)
# Version: 2.0.0

set -e  # Exit on any error

echo "=== Multi-Boat Control System Setup (Phase 2) ==="
echo "Enhanced setup for complete RTK + Heading state estimation and Pixhawk control"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 成功和失败标记
SUCCESS="${GREEN}✓${NC}"
FAILURE="${RED}✗${NC}"
WARNING="${YELLOW}⚠${NC}"
INFO="${BLUE}ℹ${NC}"

# 创建必要的目录结构
echo -e "${INFO} Creating enhanced directory structure..."
mkdir -p scripts
mkdir -p launch
mkdir -p msg
mkdir -p config
mkdir -p logs    # 新增：用于日志存储

echo -e "${SUCCESS} Directory structure created"

# 设置所有Python脚本的执行权限
echo -e "${INFO} Setting executable permissions for Python scripts..."

# 现有脚本
chmod +x scripts/rtk_node.py 2>/dev/null || echo -e "${WARNING} rtk_node.py not found"
chmod +x scripts/state_estimator_node.py 2>/dev/null || echo -e "${WARNING} state_estimator_node.py not found"
chmod +x scripts/sensor_diagnostic.py 2>/dev/null || echo -e "${WARNING} sensor_diagnostic.py not found"

# Phase 2 新增脚本
chmod +x scripts/control_interface_node.py 2>/dev/null || echo -e "${WARNING} control_interface_node.py not found (Phase 2 file)"
chmod +x scripts/vehicle_extensions.py 2>/dev/null || echo -e "${WARNING} vehicle_extensions.py not found (Phase 2 file)"

# 安装脚本权限
chmod +x install_dependencies.sh 2>/dev/null || echo -e "${WARNING} install_dependencies.sh not found"

echo -e "${SUCCESS} Script permissions configured"

# 检查ROS环境
echo -e "${INFO} Checking ROS environment..."
if [ -z "$ROS_DISTRO" ]; then
    echo -e "${FAILURE} ROS environment not detected!"
    echo "Please source ROS setup.bash first:"
    echo "  source /opt/ros/noetic/setup.bash  # For ROS Noetic"
    echo "  source /opt/ros/melodic/setup.bash # For ROS Melodic"
    exit 1
else
    echo -e "${SUCCESS} ROS Distribution detected: $ROS_DISTRO"
fi

# 检查catkin workspace
if [ -z "$ROS_PACKAGE_PATH" ] || [[ ! "$ROS_PACKAGE_PATH" == *"catkin_ws"* ]]; then
    echo -e "${WARNING} Catkin workspace may not be properly sourced"
    echo "Make sure to source your workspace setup.bash:"
    echo "  source ~/catkin_ws/devel/setup.bash"
fi

# 检查Python版本
echo -e "${INFO} Checking Python environment..."
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1-2)
echo -e "${SUCCESS} Python version: $PYTHON_VERSION"

# 检查Phase 1依赖
echo -e "${INFO} Checking Phase 1 dependencies..."
python3 -c "import serial" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${SUCCESS} pyserial is available"
else
    echo -e "${FAILURE} pyserial not found"
    echo "Install with: pip3 install pyserial"
fi

# 检查Phase 2关键依赖
echo -e "${INFO} Checking Phase 2 dependencies (Pixhawk communication)..."

# 检查dronekit
python3 -c "import dronekit" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${SUCCESS} dronekit is available"
    DRONEKIT_VERSION=$(python3 -c "import dronekit; print(dronekit.__version__)" 2>/dev/null || echo "unknown")
    echo "  Version: $DRONEKIT_VERSION"
else
    echo -e "${FAILURE} dronekit not found (CRITICAL for Phase 2)"
    echo "Install with: pip3 install dronekit>=2.9.2"
fi

# 检查pymavlink
python3 -c "import pymavlink" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${SUCCESS} pymavlink is available"
    PYMAVLINK_VERSION=$(python3 -c "import pymavlink; print(pymavlink.__version__)" 2>/dev/null || echo "unknown")
    echo "  Version: $PYMAVLINK_VERSION"
else
    echo -e "${FAILURE} pymavlink not found (CRITICAL for Phase 2)"
    echo "Install with: pip3 install pymavlink>=2.4.37"
fi

# 检查ROS Python依赖
python3 -c "import rospy, std_msgs, geometry_msgs, sensor_msgs" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${SUCCESS} ROS Python packages are available"
else
    echo -e "${FAILURE} ROS Python packages not found"
    echo "Install with: sudo apt install ros-$ROS_DISTRO-rospy ros-$ROS_DISTRO-std-msgs ros-$ROS_DISTRO-geometry-msgs ros-$ROS_DISTRO-sensor-msgs"
fi

# 检查tf变换库（IMU数据需要）
python3 -c "from tf.transformations import quaternion_from_euler" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${SUCCESS} tf transformations available"
else
    echo -e "${FAILURE} tf transformations not found"
    echo "Install with: sudo apt install ros-$ROS_DISTRO-tf"
fi

# 检查设备权限和连接
echo -e "${INFO} Checking hardware device permissions..."

# 检查RTK GPS设备
if [ -e "/dev/ttyUSB0" ]; then
    echo -e "${SUCCESS} Found RTK GPS device at /dev/ttyUSB0"
    if [ -r "/dev/ttyUSB0" ] && [ -w "/dev/ttyUSB0" ]; then
        echo -e "${SUCCESS} RTK device has read/write permissions"
    else
        echo -e "${FAILURE} RTK device needs permission"
        echo "Fix with: sudo chmod 666 /dev/ttyUSB0"
    fi
else
    echo -e "${WARNING} RTK device /dev/ttyUSB0 not found (normal if hardware not connected)"
fi

# 检查Pixhawk设备 (Phase 2新增)
if [ -e "/dev/ttyAMA0" ]; then
    echo -e "${SUCCESS} Found Pixhawk device at /dev/ttyAMA0"
    if [ -r "/dev/ttyAMA0" ] && [ -w "/dev/ttyAMA0" ]; then
        echo -e "${SUCCESS} Pixhawk device has read/write permissions"
    else
        echo -e "${FAILURE} Pixhawk device needs permission"
        echo "Fix with: sudo chmod 666 /dev/ttyAMA0"
    fi
else
    echo -e "${WARNING} Pixhawk device /dev/ttyAMA0 not found"
    echo "Alternative devices to check:"
    echo "  /dev/ttyUSB1, /dev/ttyUSB2 (USB-connected Pixhawk)"
    echo "  /dev/ttyACM0 (some Pixhawk variants)"
fi

# 用户组权限检查
echo -e "${INFO} Checking user group permissions..."
if groups $USER | grep -q dialout; then
    echo -e "${SUCCESS} User $USER is in dialout group"
else
    echo -e "${FAILURE} User $USER is NOT in dialout group"
    echo "Fix with:"
    echo "  sudo usermod -a -G dialout $USER"
    echo "  Then logout and login again"
fi

# 检查ROS包依赖
echo -e "${INFO} Checking ROS package dependencies..."

# 检查teleop_twist_keyboard (测试用)
rospack find teleop_twist_keyboard >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${SUCCESS} teleop_twist_keyboard package found"
else
    echo -e "${WARNING} teleop_twist_keyboard not found (needed for testing)"
    echo "Install with: sudo apt install ros-$ROS_DISTRO-teleop-twist-keyboard"
fi

# 检查rqt相关包（监控用）
rospack find rqt_graph >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${SUCCESS} rqt_graph package found"
else
    echo -e "${WARNING} rqt_graph not found (useful for debugging)"
    echo "Install with: sudo apt install ros-$ROS_DISTRO-rqt-graph"
fi

# 项目文件检查
echo -e "${INFO} Checking project file structure..."

# 检查消息文件
if [ -f "msg/RTK.msg" ]; then
    echo -e "${SUCCESS} RTK.msg found"
else
    echo -e "${FAILURE} RTK.msg not found (Phase 1 required)"
fi

if [ -f "msg/BoatState.msg" ]; then
    echo -e "${SUCCESS} BoatState.msg found (Phase 2)"
else
    echo -e "${WARNING} BoatState.msg not found (Phase 2 required for complete state)"
fi

# 检查关键脚本
REQUIRED_SCRIPTS=("rtk_node.py" "state_estimator_node.py" "control_interface_node.py")
for script in "${REQUIRED_SCRIPTS[@]}"; do
    if [ -f "scripts/$script" ]; then
        echo -e "${SUCCESS} $script found"
    else
        echo -e "${WARNING} $script not found"
    fi
done

# Phase 2特定文件
if [ -f "scripts/vehicle_extensions.py" ]; then
    echo -e "${SUCCESS} vehicle_extensions.py found (Phase 2)"
else
    echo -e "${WARNING} vehicle_extensions.py not found (Phase 2 ExtendedVehicle support)"
fi

# 检查launch文件
if [ -f "launch/integrated_boat_system.launch" ]; then
    echo -e "${SUCCESS} integrated_boat_system.launch found (Phase 2)"
else
    echo -e "${WARNING} integrated_boat_system.launch not found (Phase 2 complete system)"
fi

# 快速依赖安装选项
echo ""
echo -e "${INFO} Quick dependency installation:"
echo "Run the following commands if any dependencies are missing:"
echo ""
echo "# Install Python dependencies:"
echo "pip3 install dronekit>=2.9.2 pymavlink>=2.4.37 pyserial>=3.5"
echo ""
echo "# Install ROS dependencies:"
echo "sudo apt install ros-$ROS_DISTRO-teleop-twist-keyboard ros-$ROS_DISTRO-tf ros-$ROS_DISTRO-rqt-graph"
echo ""
echo "# Fix device permissions:"
echo "sudo usermod -a -G dialout $USER  # Then logout/login"
echo ""

# 构建和测试指导
echo ""
echo "=== Phase 2 Next Steps ==="
echo ""
echo "1. ${BLUE}Build the enhanced package:${NC}"
echo "   cd ~/catkin_ws"
echo "   catkin_make"
echo "   source devel/setup.bash"
echo ""
echo "2. ${BLUE}Test individual components:${NC}"
echo "   # Test RTK GPS data:"
echo "   roslaunch multi_boat_control rtk_test.launch"
echo ""
echo "   # Test Pixhawk control interface:"
echo "   roslaunch multi_boat_control test_control_interface.launch"
echo ""
echo "3. ${BLUE}Launch complete system (Phase 2):${NC}"
echo "   roslaunch multi_boat_control integrated_boat_system.launch"
echo ""
echo "4. ${BLUE}Monitor system status:${NC}"
echo "   rostopic echo /boat_state          # Complete state (RTK + heading)"
echo "   rostopic echo /imu/data            # IMU data"
echo "   rostopic echo /boat/heading        # Heading data"
echo "   rqt_graph                          # System visualization"
echo ""
echo "5. ${BLUE}Manual control testing:${NC}"
echo "   # Use keyboard control (opens in XTerm)"
echo "   # Or send manual commands:"
echo "   rostopic pub /control_interface_node/cmd_vel geometry_msgs/Twist 'linear: {x: 1.0}' -r 10"
echo ""

# 故障排除提示
echo -e "${INFO} Common troubleshooting:"
echo "• Connection issues: Check device paths and permissions"
echo "• Build errors: Ensure all msg files are present before catkin_make"
echo "• Import errors: Verify Python dependencies with pip3 list"
echo "• Permission denied: Add user to dialout group and relogin"
echo ""

echo -e "${SUCCESS} Phase 2 setup check completed!"
echo ""
echo -e "${YELLOW}Ready for multi-boat cooperative control system deployment!${NC}"
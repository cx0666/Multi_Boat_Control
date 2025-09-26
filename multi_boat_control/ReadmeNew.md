# 🚤 多艇协同控制系统 - 项目部署与验证指南

## 📋 指南概述

本指南专为**项目合作者和测试人员**编写，提供**手把手的操作步骤**，确保系统正确运行并验证所有关键功能：

✅ **系统正确启动和运行**  
✅ **RTK GPS数据正常发布**  
✅ **航向角信息准确获取**  
✅ **USV电机控制响应正常**  
✅ **消息通信完整性验证**  

---

## 🎯 核心验证目标

### 必须验证的功能点：
1. **RTK GPS数据质量** - 高精度定位数据获取
2. **航向角信息精度** - Pixhawk IMU朝向数据
3. **状态融合正确性** - RTK + 航向角完整状态
4. **电机控制响应** - USV前进、后退、转向
5. **系统稳定性** - 长时间运行无故障

---

## 📂 项目文件结构确认

**首先确认您的项目具有完整的文件结构：**

```
multi_boat_control/
├── msg/
│   ├── RTK.msg                          ✅ 必需
│   └── BoatState.msg                    ✅ 必需 (Phase 2)
├── scripts/
│   ├── rtk_node.py                      ✅ 必需
│   ├── state_estimator_node.py          ✅ 必需
│   ├── control_interface_node.py        ✅ 必需 (Phase 2重构版)
│   ├── vehicle_extensions.py            ✅ 必需 (Phase 2新增)
│   └── sensor_diagnostic.py             ⭕ 可选
├── launch/
│   ├── test_control_interface.launch    ✅ 必需
│   └── integrated_boat_system.launch    ✅ 必需 (Phase 2)
├── requirements.txt                     ✅ 必需
├── install_dependencies.sh              ✅ 必需
└── setup.sh                            ✅ 推荐
```

---

## 🔧 Step 1: 环境准备与依赖检查

### 1.1 运行环境检查脚本
```bash
# 进入项目目录
cd /path/to/your/catkin_ws/src/multi_boat_control

# 运行增强版环境检查
chmod +x setup.sh
./setup.sh
```

**期望输出示例：**
```
=== Multi-Boat Control System Setup (Phase 2) ===
✓ ROS Distribution detected: noetic
✓ Python version: 3.8
✓ dronekit is available
✓ pymavlink is available
✓ User ubuntu is in dialout group
✓ Found RTK GPS device at /dev/ttyUSB0
✓ Found Pixhawk device at /dev/ttyAMA0
✓ Setup check completed!
```

### 1.2 安装Python依赖
```bash
# 方法1：使用安装脚本（推荐）
chmod +x install_dependencies.sh
./install_dependencies.sh

# 方法2：手动安装
pip3 install --user dronekit>=2.9.2 pymavlink>=2.4.37 pyserial>=3.5

# 验证安装
python3 -c "import dronekit, pymavlink, serial; print('All dependencies OK')"
```

### 1.3 设置硬件设备权限
```bash
# 添加用户到dialout组（一次性操作）
sudo usermod -a -G dialout $USER

# ⚠️ 重要：注销并重新登录使权限生效
# logout && login

# 验证权限
groups $USER | grep dialout  # 应显示dialout组

# 临时权限设置（立即生效）
sudo chmod 666 /dev/ttyUSB0   # RTK设备
sudo chmod 666 /dev/ttyAMA0   # Pixhawk设备
```

### 1.4 编译ROS包
```bash
# 进入catkin工作空间
cd ~/catkin_ws

# 编译项目
catkin_make

# 验证编译成功
echo $?  # 应输出0表示成功

# 加载环境变量
source devel/setup.bash

# 验证消息类型
rosmsg show multi_boat_control/RTK        # 应显示RTK消息结构
rosmsg show multi_boat_control/BoatState  # 应显示BoatState消息结构
```

---

## 🚀 Step 2: 分阶段系统验证

### 2.1 Phase 1验证 - RTK GPS数据采集

**启动RTK节点：**
```bash
# 终端1：启动RTK数据采集
roscore &
rosrun multi_boat_control rtk_node.py

# 期望输出：
# [INFO] RTK Node starting...
# [INFO] Opening serial port: /dev/ttyUSB0 at 115200 baud
# [INFO] RTK connection established
```

**验证RTK数据发布：**
```bash
# 终端2：监控RTK数据
rostopic echo /rtk_data

# 期望输出示例：
# header:
#   stamp:
#     secs: 1640995200
#   frame_id: "rtk_gps"
# latitude: 30.123456        ← 应为真实GPS坐标
# longitude: 120.654321      ← 应为真实GPS坐标
# ground_speed_mps: 0.0      ← 静止时应为0
# course_over_ground_deg: 0.0
# gps_fix_valid: True        ← 必须为True
```

**RTK数据质量检查：**
```bash
# 检查发布频率（应为1-10Hz）
rostopic hz /rtk_data

# 检查数据连续性
rostopic echo /rtk_data --filter="m.gps_fix_valid" | head -10

# 验证坐标合理性（纬度25-50°，经度80-140°为中国范围）
rostopic echo /rtk_data --filter="m.latitude > 25 and m.latitude < 50"
```

**✅ Phase 1验证通过标准：**
- RTK数据稳定发布（>1Hz）
- `gps_fix_valid = True`
- 经纬度坐标符合实际位置
- 无错误日志输出

---

### 2.2 Phase 2验证 - Pixhawk控制接口

**启动控制接口节点：**
```bash
# 终端1：启动控制接口（包含IMU和航向角发布）
roslaunch multi_boat_control test_control_interface.launch

# 期望输出：
# [INFO] === Enhanced Control Interface Node Starting ===
# [INFO] Configuration: /dev/ttyAMA0 @ 921600 baud
# [INFO] ✓ Vehicle connected successfully
# [INFO] Step 1: ✓ Vehicle is armable
# [INFO] Step 2: ✓ Mode set to GUIDED  
# [INFO] Step 3: ✓ Vehicle armed successfully
# [INFO] 🎉 Boat initialization completed!
# [INFO] ✓ Publishing threads started
# [INFO] === Control Interface Node Ready ===
```

**验证IMU数据发布：**
```bash
# 终端2：监控IMU数据
rostopic echo /imu/data

# 期望输出：
# header:
#   stamp: {secs: xxx, nsecs: xxx}
#   frame_id: "base_link"
# orientation:           ← 四元数姿态
#   x: 0.123, y: 0.456, z: 0.789, w: 0.987
# angular_velocity:      ← 角速度 (rad/s)
#   x: 0.01, y: 0.02, z: 0.03
# linear_acceleration:   ← 线加速度 (m/s²)
#   x: 0.1, y: 0.2, z: 9.8  ← z轴应接近重力加速度
```

**验证航向角数据发布：**
```bash
# 终端3：监控航向角数据
rostopic echo /boat/heading

# 期望输出：
# data: 87.5  ← 航向角度值 (0-360°, 0°=磁北, 90°=磁东)

# 检查发布频率（应为10Hz）
rostopic hz /boat/heading
# average rate: 10.000
```

**验证电机控制响应（重要！）：**

⚠️ **安全注意：进行电机测试前确保USV在安全的测试环境中**

```bash
# 方法1：键盘遥操作测试（在XTerm窗口中）
# 按键控制：
# i = 前进, , = 后退, j = 左转, l = 右转, k = 停止

# 方法2：手动命令测试
# 前进测试（0.5 m/s）
rostopic pub /control_interface_node/cmd_vel geometry_msgs/Twist "linear: {x: 0.5}" -r 10

# 观察：USV应开始前进移动
# 停止命令
rostopic pub /control_interface_node/cmd_vel geometry_msgs/Twist "linear: {x: 0.0}" -r 10

# 转向测试（0.3 rad/s顺时针）
rostopic pub /control_interface_node/cmd_vel geometry_msgs/Twist "angular: {z: 0.3}" -r 10

# 观察：USV应开始顺时针转动
```

**电机响应验证清单：**
- [ ] 前进指令：USV向前移动
- [ ] 后退指令：USV向后移动  
- [ ] 左转指令：USV逆时针转动
- [ ] 右转指令：USV顺时针转动
- [ ] 停止指令：USV立即停止

**✅ Phase 2验证通过标准：**
- Pixhawk成功连接并初始化（GUIDED模式+ARM）
- IMU数据稳定发布（10Hz），包含姿态、角速度、加速度
- 航向角数据稳定发布（10Hz），数值合理（0-360°）
- 电机控制指令正确响应，USV按预期移动

---

### 2.3 完整系统验证 - 状态融合

**启动完整系统：**
```bash
# 启动完整系统（RTK + 状态估计 + Pixhawk控制）
roslaunch multi_boat_control integrated_boat_system.launch

# 期望输出：
# [INFO] RTK Node starting...
# [INFO] State Estimator Node (Phase 2) Starting
# [INFO] Enhanced Control Interface Node Starting
# ... (各节点成功启动信息)
# [INFO] State Estimator Status: RTK=True, Heading=True, Combined=True, Rate=10.0 Hz
```

**验证完整状态消息：**
```bash
# 监控完整状态
rostopic echo /boat_state

# 期望输出示例：
# header:
#   stamp: {secs: xxx, nsecs: xxx}
#   frame_id: "boat_base_link"
# latitude: 30.123456              ← RTK GPS纬度
# longitude: 120.654321            ← RTK GPS经度
# ground_speed_mps: 0.0            ← GPS地面速度
# course_over_ground_deg: 45.0     ← GPS航向角
# gps_fix_valid: True              ← GPS状态
# heading_magnetic_deg: 87.5       ← Pixhawk磁航向角
# heading_valid: True              ← 航向角状态
# rtk_timestamp: {secs: xxx}       ← RTK数据时间戳
# heading_timestamp: {secs: xxx}   ← 航向角时间戳
# rtk_source: "RTK_GPS"
# heading_source: "Pixhawk_IMU"
```

**数据融合质量检查：**
```bash
# 检查数据发布频率（应为10Hz）
rostopic hz /boat_state

# 检查数据完整性（RTK和航向角都有效）
rostopic echo /boat_state --filter="m.gps_fix_valid and m.heading_valid"

# 检查数据同步性（时间戳差异应<1秒）
rostopic echo /boat_state --filter="(m.rtk_timestamp.secs - m.heading_timestamp.secs) < 1"

# 统计数据质量
rostopic echo /boat_state | grep -E "gps_fix_valid|heading_valid" | head -20
```

**✅ 完整系统验证通过标准：**
- 所有三个节点（RTK、状态估计、控制接口）成功启动
- `/boat_state`消息稳定发布（10Hz）
- RTK和航向角数据都标记为有效（`True`）
- 数据时间戳同步（<1秒差异）
- 坐标和航向角数值合理

---

## 🔍 Step 3: 深度功能测试

### 3.1 端到端控制测试

**测试完整控制循环：**
```bash
# 1. 启动完整系统
roslaunch multi_boat_control integrated_boat_system.launch

# 2. 等待系统稳定（约30秒）
sleep 30

# 3. 记录初始状态
rostopic echo /boat_state -n 1 > initial_state.log

# 4. 发送控制指令并观察状态变化
rostopic pub /control_interface_node/cmd_vel geometry_msgs/Twist "linear: {x: 1.0}" -r 10 &
sleep 5  # 前进5秒
rostopic echo /boat_state -n 5 > moving_state.log

# 5. 停止并记录最终状态
rostopic pub /control_interface_node/cmd_vel geometry_msgs/Twist "linear: {x: 0.0}" -r 10 &
sleep 2
rostopic echo /boat_state -n 1 > final_state.log

# 6. 分析状态变化
echo "初始位置：" && grep -E "latitude|longitude" initial_state.log
echo "移动中状态：" && grep -E "latitude|longitude" moving_state.log | head -2
echo "最终位置：" && grep -E "latitude|longitude" final_state.log
```

**期望结果分析：**
- 初始状态和最终状态的经纬度应有明显差异（USV确实移动了）
- `ground_speed_mps`在运动期间应大于0
- 航向角数据应保持稳定有效

### 3.2 通信质量长期测试

**24小时稳定性测试：**
```bash
# 创建监控脚本
cat << EOF > monitor_system.sh
#!/bin/bash
echo "开始24小时系统监控..." | tee system_monitor.log
while true; do
    timestamp=\$(date)
    
    # 检查节点状态
    rtk_alive=\$(rostopic echo /rtk_data --timeout=5 -n 1 >/dev/null 2>&1 && echo "OK" || echo "FAIL")
    heading_alive=\$(rostopic echo /boat/heading --timeout=5 -n 1 >/dev/null 2>&1 && echo "OK" || echo "FAIL")
    state_alive=\$(rostopic echo /boat_state --timeout=5 -n 1 >/dev/null 2>&1 && echo "OK" || echo "FAIL")
    
    # 记录状态
    echo "[\$timestamp] RTK:\$rtk_alive Heading:\$heading_alive State:\$state_alive" | tee -a system_monitor.log
    
    # 每10分钟检查一次
    sleep 600
done
EOF

chmod +x monitor_system.sh

# 启动监控（后台运行）
./monitor_system.sh &

# 24小时后检查结果
tail -100 system_monitor.log | grep -c "RTK:OK.*Heading:OK.*State:OK"
# 应接近144（24小时 * 6次/小时）
```

### 3.3 消息内容准确性验证

**GPS精度验证：**
```bash
# 记录静止状态下的GPS数据（10分钟）
timeout 600 rostopic echo /boat_state | grep -E "latitude|longitude" > gps_precision_test.log

# 分析GPS精度
python3 << EOF
import re
data = []
with open('gps_precision_test.log', 'r') as f:
    for line in f:
        if 'latitude:' in line:
            lat = float(re.search(r'latitude: ([-+]?\d*\.?\d+)', line).group(1))
            data.append(('lat', lat))
        elif 'longitude:' in line:
            lon = float(re.search(r'longitude: ([-+]?\d*\.?\d+)', line).group(1))
            data.append(('lon', lon))

lats = [x[1] for x in data if x[0] == 'lat']
lons = [x[1] for x in data if x[0] == 'lon']

if lats and lons:
    lat_std = (max(lats) - min(lats))
    lon_std = (max(lons) - min(lons))
    print(f"GPS精度分析:")
    print(f"纬度变化范围: {lat_std:.8f}° (±{lat_std*111000:.2f}m)")
    print(f"经度变化范围: {lon_std:.8f}° (±{lon_std*111000:.2f}m)")
    print(f"RTK精度评估: {'优秀' if lat_std < 0.000001 else '良好' if lat_std < 0.00001 else '需改进'}")
EOF
```

**航向角一致性验证：**
```bash
# 同时记录GPS航向和IMU航向进行对比
timeout 300 rostopic echo /boat_state | grep -E "course_over_ground_deg|heading_magnetic_deg" > heading_comparison.log

# 分析航向角一致性
echo "GPS航向角 vs IMU航向角对比："
paste <(grep "course_over_ground_deg" heading_comparison.log) <(grep "heading_magnetic_deg" heading_comparison.log) | head -10
```

---

## 🛠️ Step 4: 故障排除指南

### 4.1 常见问题诊断

**问题1：RTK数据不发布**
```bash
# 诊断步骤
echo "检查RTK设备连接..."
ls -l /dev/ttyUSB*

echo "检查设备权限..."
groups $USER | grep dialout

echo "测试串口通信..."
sudo minicom -D /dev/ttyUSB0 -b 115200
# 应看到NMEA数据流

echo "检查节点日志..."
rosnode list | grep rtk
rosnode info /rtk_node
```

**问题2：Pixhawk连接失败**
```bash
# 诊断步骤
echo "检查Pixhawk设备..."
ls -l /dev/ttyAMA0 /dev/ttyUSB1

echo "测试dronekit连接..."
python3 -c "
from dronekit import connect
try:
    vehicle = connect('/dev/ttyAMA0', baud=921600, wait_ready=True, timeout=30)
    print('✓ Pixhawk连接成功')
    print(f'模式: {vehicle.mode.name}')
    print(f'解锁状态: {vehicle.armed}')
    print(f'GPS状态: {vehicle.gps_0.fix_type}')
    vehicle.close()
except Exception as e:
    print(f'✗ 连接失败: {e}')
"
```

**问题3：电机不响应**
```bash
# 安全检查清单
echo "电机控制安全检查："
echo "1. 确认USV在安全测试环境"
echo "2. 检查Pixhawk模式..."
rostopic echo /boat/pixhawk_connected -n 1

echo "3. 检查控制指令接收..."
rostopic echo /control_interface_node/cmd_vel &
rostopic pub /control_interface_node/cmd_vel geometry_msgs/Twist "linear: {x: 0.1}" -r 5
sleep 3
pkill rostopic

echo "4. 检查MAVLink消息发送日志..."
# 查看控制节点日志中是否有"Sent velocity command"信息
```

**问题4：状态融合数据异常**
```bash
# 数据质量检查
echo "检查数据源状态..."
rostopic echo /boat_state -n 1 | grep -E "_valid|_source"

echo "检查时间同步..."
rostopic echo /boat_state -n 1 | grep -E "timestamp"

echo "检查数据范围合理性..."
rostopic echo /boat_state -n 3 | grep -E "latitude|longitude|heading_magnetic_deg"
```

### 4.2 性能调优建议

**优化发布频率：**
```bash
# 根据应用需求调整频率
# 高频率(20Hz) - 精确控制
roslaunch multi_boat_control integrated_boat_system.launch imu_publish_rate:=20.0

# 中频率(10Hz) - 标准应用
roslaunch multi_boat_control integrated_boat_system.launch imu_publish_rate:=10.0

# 低频率(5Hz) - 节省带宽
roslaunch multi_boat_control integrated_boat_system.launch imu_publish_rate:=5.0
```

**网络负载优化：**
```bash
# 监控网络使用率
iftop -i wlan0

# 优化ROS网络
export ROS_IP=192.168.1.100  # 使用固定IP
export ROS_MASTER_URI=http://192.168.1.100:11311
```

---

## ✅ Step 5: 验收测试清单

### 5.1 必须通过的验收测试

**□ 环境准备验证**
- [ ] 所有Python依赖已安装（dronekit, pymavlink, pyserial）
- [ ] 用户已加入dialout组并重新登录
- [ ] ROS环境正确配置（noetic/melodic）
- [ ] 项目编译成功（catkin_make无错误）

**□ 硬件连接验证**
- [ ] RTK GPS设备检测（/dev/ttyUSB0）
- [ ] Pixhawk设备检测（/dev/ttyAMA0）
- [ ] 设备权限正确（读写权限）
- [ ] 串口通信正常

**□ 单节点功能验证**
- [ ] RTK节点：数据发布稳定，gps_fix_valid=True
- [ ] 控制接口节点：Pixhawk连接成功，模式GUIDED，已解锁
- [ ] 状态估计节点：状态融合正常，数据完整

**□ 数据发布验证**
- [ ] /rtk_data消息：包含准确的经纬度、速度
- [ ] /boat/heading消息：航向角0-360°，更新频率10Hz
- [ ] /imu/data消息：包含姿态、角速度、线加速度
- [ ] /boat_state消息：RTK+航向角融合，两个数据源都有效

**□ 电机控制验证（关键！）**
- [ ] 前进指令：USV向前移动，速度可控
- [ ] 后退指令：USV向后移动
- [ ] 左转指令：USV逆时针转动
- [ ] 右转指令：USV顺时针转动
- [ ] 停止指令：USV立即停止所有运动
- [ ] 键盘遥操作：所有按键正确响应

**□ 系统集成验证**
- [ ] 完整系统启动：三个节点同时正常运行
- [ ] 数据同步：各数据源时间戳差异<1秒
- [ ] 长期稳定：连续运行1小时无故障
- [ ] 资源使用：CPU使用率<50%，内存使用合理

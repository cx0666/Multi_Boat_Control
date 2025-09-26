# 📋 Multi-Boat Control System - 使用指南与故障排除

## 🚀 项目使用流程

### 第一步：环境准备
```bash
# 1. 确保ROS环境
source /opt/ros/noetic/setup.bash  # 或对应的ROS版本

# 2. 构建项目
cd ~/catkin_ws/src
# [将所有项目文件复制到 multi_boat_control/ 目录]
cd ~/catkin_ws
catkin_make
source devel/setup.bash

# 3. 设置权限
chmod +x src/multi_boat_control/scripts/*.py
sudo chmod 666 /dev/ttyUSB0  # RTK设备权限
```

### 第二步：逐步验证 (推荐流程)

#### **🔍 Step 1: 传感器状态验证**
```bash
# 启动传感器监控模式
roslaunch multi_boat_control sensor_monitor.launch

# 预期看到：
# 🛰️  RTK #0001: GPS(29.9984123, 122.1603456) -> Local(45.67, 12.34m)...
# 🧭 IMU #0001: Yaw: 87.2°, AngVel_Z: 0.045 rad/s...
# 📊 SENSOR STATUS SUMMARY
#    RTK:  ✅ Working | Count: 0042 | Rate: 1.0 Hz  
#    IMU:  ✅ Working | Count: 0156 | Rate: 50.0 Hz
```

#### **🔍 Step 2: 完整系统验证**
```bash
# 启动完整状态估计系统
roslaunch multi_boat_control boat_state_estimation.launch

# 预期看到：
# ✅ RTK: Operating normally
# ✅ IMU: Operating normally
# 📊 Sensor Status: RTK ✅ | IMU ✅ | State publishing at 10Hz
```

#### **🔍 Step 3: 数据流验证**
```bash
# 在新终端中检查数据流
rostopic echo /rtk/raw
rostopic echo /boat_A/state
rostopic echo /imu/data

# 检查频率
rostopic hz /rtk/raw      # 应该约 1Hz
rostopic hz /boat_A/state # 应该约 10Hz  
rostopic hz /imu/data     # 应该约 50Hz
```

## ✅ 可以验证的信息

### 1. **RTK GNSS 工作状态**
- **位置精度**：GPS经纬度 → 本地坐标系转换
- **速度测量**：地面速度（节 → 米/秒转换）
- **航向精度**：地面航向角（0-360度）
- **数据频率**：约1Hz的稳定更新
- **数据有效性**：`$GNRMC`语句的'A'有效位检查

**验证方法：**
```bash
# 查看原始RTK数据
rostopic echo /rtk/raw -n 5

# 应该看到：
# latitude_deg: 29.9984123
# longitude_deg: 122.1603456  
# ground_speed_mps: 1.234
# course_over_ground_deg: 87.5
```

### 2. **IMU 姿态传感器状态**
- **航向角**：从四元数提取的yaw角
- **角速度**：三轴角速度，特别是z轴（偏航）
- **线性加速度**：三轴加速度（包括重力）
- **数据完整性**：四元数非零验证
- **更新频率**：通常50Hz高频更新

**验证方法：**
```bash
# 查看IMU详细数据
rostopic echo /imu/data -n 1

# 在诊断工具中会看到：
# 🧭 IMU #0156: Yaw: 87.2°, AngVel_Z: 0.045 rad/s, Accel: (0.12, -9.79, 0.08) m/s²
```

### 3. **坐标系转换验证**
- **GPS→本地坐标**：经纬度转换为米制坐标
- **航向角统一**：转换为"东为0度，逆时针为正"
- **原点基准**：基于设定的湖泊坐标系原点
- **速度分解**：全局速度→本地坐标系速度分量

**验证方法：**
```bash
# 查看融合后的状态
rostopic echo /boat_A/state

# 重点检查：
# pose.pose.position: {x: 45.67, y: 12.34, z: 0.0}  # 本地坐标
# pose.pose.orientation: {...}  # 统一后的航向四元数
# twist.twist.linear: {x: 1.2, y: 0.3, z: 0.0}  # 速度分量
```

### 4. **系统健康状态**
- **传感器超时检测**：2秒无数据报警
- **数据质量评估**：解析错误统计
- **通信状态**：ROS话题连接状态
- **坐标系一致性**：不同传感器数据对比

## 🔧 异常排查指南

### **问题1：RTK无数据 `❌ RTK: No data received yet`**

**可能原因：**
- RTK设备未连接或串口地址错误
- 串口权限问题
- RTK设备未获得有效定位

**排查步骤：**
```bash
# 1. 检查设备连接
ls /dev/ttyUSB*  # 应该看到 /dev/ttyUSB0 等设备

# 2. 检查权限
sudo chmod 666 /dev/ttyUSB0

# 3. 手动测试串口
cat /dev/ttyUSB0  # 应该看到NMEA语句流

# 4. 检查RTK状态
# RTK设备指示灯应显示已定位状态（通常绿灯）
```

**解决方案：**
- 更换串口地址：`roslaunch ... rtk_port:=/dev/ttyUSB1`
- 等待RTK获得卫星定位（室外空旷环境，等待2-5分钟）
- 检查RTK设备电源和天线连接

### **问题2：IMU无数据 `❌ IMU: No data received yet`**

**可能原因：**
- Pixhawk未正确连接到ROS
- IMU话题名称不匹配
- Pixhawk固件或配置问题

**排查步骤：**
```bash
# 1. 检查话题列表
rostopic list | grep imu

# 2. 检查是否有其他IMU话题
rostopic list | grep -i imu
# 可能是 /mavros/imu/data 而不是 /imu/data

# 3. 手动查看IMU数据
rostopic echo /mavros/imu/data -n 1
```

**解决方案：**
- 确认Pixhawk连接：`roslaunch mavros px4.launch`
- 修改话题订阅地址（如果需要从`/imu/data`改为`/mavros/imu/data`）
- 检查Pixhawk IMU校准状态

### **问题3：坐标转换异常 `坐标值过大或NaN`**

**可能原因：**
- 原点坐标设置错误
- RTK数据中经纬度格式异常
- 数学计算溢出

**排查步骤：**
```bash
# 1. 检查原始RTK数据格式
rostopic echo /rtk/raw -n 3

# 2. 验证原点设置
rosparam get /state_estimator_node/origin_latitude
rosparam get /state_estimator_node/origin_longitude

# 3. 手动计算验证
# 如果RTK显示 lat=30.0, lon=122.0，原点为29.999, 122.000
# 那么本地坐标应该约为 (0, 111)米
```

**解决方案：**
- 重新测量并设置准确的湖泊坐标系原点
- 确认RTK数据格式符合预期
- 检查数值范围是否合理

### **问题4：状态发布频率异常**

**可能原因：**
- 系统负载过高
- ROS节点阻塞
- 传感器数据不稳定

**排查步骤：**
```bash
# 1. 检查系统负载
htop

# 2. 检查ROS节点状态
rosnode info /state_estimator_node

# 3. 检查话题频率
rostopic hz /boat_A/state  # 应该接近10Hz
```

### **问题5：传感器数据质量异常**

**症状表现：**
- RTK位置跳跃
- IMU航向角异常
- 速度计算错误

**排查方法：**
```bash
# 使用诊断工具持续监控
rosrun multi_boat_control sensor_diagnostic.py

# 观察数据是否：
# - RTK位置连续变化（不应跳跃）
# - IMU航向角合理（-180°到180°）
# - 速度值符合实际运动状态
```

## 📊 正常运行的标志

### **健康系统的输出示例：**
```
✅ RTK: Operating normally
✅ IMU: Operating normally  
📊 Sensor Status: RTK ✅ | IMU ✅ | State publishing at 10Hz

🛰️  RTK #0123: GPS(29.9984123, 122.1603456) -> Local(45.67, 12.34m), Speed: 1.23 m/s, Course: 87.5°
🧭 IMU #0456: Yaw: 87.2°, AngVel_Z: 0.045 rad/s, Accel: (0.12, -9.79, 0.08) m/s²
```

### **关键指标：**
- RTK更新率：0.5-2 Hz
- IMU更新率：20-100 Hz  
- 状态发布率：10 Hz
- 坐标转换：GPS变化对应合理的本地坐标变化
- 航向一致性：RTK和IMU航向角相近（考虑校准偏移）

**系统就绪标准：所有传感器显示✅，数据流稳定，无异常报警。此时可以进入Phase 2的协同控制开发！**




# 🔧 接口调整与频率影响分析

## 📍 接口调整位置指南

### **RTK接口调整**

#### **1. 串口地址调整**
**位置1：Launch文件参数** (推荐)
```bash
# 临时调整 - 启动时指定
roslaunch multi_boat_control boat_state_estimation.launch rtk_port:=/dev/ttyUSB1

# 或者修改 launch/boat_state_estimation.launch 文件中：
<param name="port" value="/dev/ttyUSB1" />  # 改为实际串口地址
```

**位置2：代码默认值**
```python
# 在 scripts/rtk_node.py 中：
self.port = rospy.get_param('~port', '/dev/ttyACM0')  # 修改默认值
```

**常见RTK串口地址：**
- `/dev/ttyUSB0`, `/dev/ttyUSB1` - USB转串口适配器
- `/dev/ttyACM0`, `/dev/ttyACM1` - USB CDC设备
- `/dev/ttyAMA0` - 树莓派硬件串口

#### **2. 波特率调整**
**位置1：Launch文件**
```xml
<param name="baudrate" value="230400" />  # 改为实际波特率
```

**位置2：代码默认值**
```python
# 在 scripts/rtk_node.py 中：
self.baudrate = rospy.get_param('~baudrate', 230400)  # 修改默认值
```

**常见RTK波特率：**
- `115200` - 标准配置
- `230400` - 高频率输出
- `460800` - 超高频配置
- `38400` - 低速配置

### **IMU接口调整**

#### **话题名称调整**
**位置：代码中的订阅者**
```python
# 在 scripts/state_estimator_node.py 中：
# 当前订阅：
self.imu_sub = rospy.Subscriber('/imu/data', Imu, self.imu_callback)

# 常见的需要调整为：
self.imu_sub = rospy.Subscriber('/mavros/imu/data', Imu, self.imu_callback)
# 或
self.imu_sub = rospy.Subscriber('/pixhawk/imu', Imu, self.imu_callback)
```

**常见IMU话题名称：**
- `/imu/data` - 通用IMU话题
- `/mavros/imu/data` - MAVROS标准话题
- `/pixhawk/imu/data` - Pixhawk专用话题
- `/fcu/imu` - 飞控IMU话题

#### **检查实际话题名称：**
```bash
# 1. 查看所有IMU相关话题
rostopic list | grep -i imu

# 2. 查看话题详细信息
rostopic info /mavros/imu/data

# 3. 确认消息类型
rostopic type /mavros/imu/data  # 应该是 sensor_msgs/Imu
```

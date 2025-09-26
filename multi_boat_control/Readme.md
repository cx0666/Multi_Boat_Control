# Multi-Boat Cooperative Control System

## 项目概述

本项目是一个基于ROS的多艇协同包围控制系统，旨在将经过MATLAB仿真验证的分布式协同控制算法部署到真实的无人艇硬件平台。

### 系统架构

采用**完全分布式架构**，每艘无人艇运行三个核心ROS节点：

1. **`state_estimator_node`** - "感知者"：融合传感器数据，发布自身状态
2. **`surrounding_controller_node`** - "决策者"：运行协同控制算法 (Phase 2)
3. **`control_interface_node`** - "执行者"：转换指令发送给硬件 (Phase 2)

## Phase 1: 状态估计与发布

本阶段实现单艇的状态估计与发布功能，包括：

### 功能模块

#### RTK Node (`rtk_node.py`)
- **职责**：从RTK的USB串口读取NMEA数据，解析并发布
- **输入**：USB串口 `/dev/ttyUSB0` (115200波特率)
- **输出**：`/rtk/raw` 话题 (`multi_boat_control/RTK` 消息)
- **特点**：严格遵循接口文档的解析逻辑，处理 `$GNRMC` 语句

#### State Estimator Node (`state_estimator_node.py`)
- **职责**：融合RTK和IMU数据，发布校准后的艇身状态
- **输入**：`/rtk/raw`, `/imu/data`
- **输出**：`/boat_A/state` 话题 (`nav_msgs/Odometry` 消息)
- **特点**：
  - GPS坐标转换为本地坐标系
  - 航向校准（统一到"东为0度，逆时针为正"）
  - 10Hz稳定发布频率
  - 通过ROS参数配置校准参数

### 文件结构

```
multi_boat_control/
├── package.xml                 # ROS包配置
├── CMakeLists.txt             # 构建配置
├── README.md                  # 本文档
├── msg/
│   └── RTK.msg               # RTK自定义消息
├── scripts/
│   ├── rtk_node.py           # RTK数据读取节点
│   ├── state_estimator_node.py  # 状态估计节点
│   └── sensor_diagnostic.py # 传感器诊断工具
└── launch/
    ├── boat_state_estimation.launch      # 生产环境启动文件
    ├── test_boat_state_estimation.launch # 测试启动文件  
    └── sensor_monitor.launch            # 传感器监控专用启动文件
```

## 安装与使用

### 1. 构建ROS包

```bash
# 在ROS工作空间中
cd ~/catkin_ws/src
# 复制项目文件到此处
cd ~/catkin_ws
catkin_make
source devel/setup.bash
```

### 2. 启动系统

#### 生产环境 (连接真实硬件)
```bash
roslaunch multi_boat_control boat_state_estimation.launch
```

#### 测试环境 (包含调试工具)
```bash
roslaunch multi_boat_control test_boat_state_estimation.launch debug:=true
```

#### 传感器监控模式 (专门用于验证RTK和IMU状态)
```bash
roslaunch multi_boat_control sensor_monitor.launch
```

#### 自定义RTK串口
```bash
roslaunch multi_boat_control boat_state_estimation.launch rtk_port:=/dev/ttyUSB1
```

### 3. 验证系统运行

```bash
# 查看RTK原始数据
rostopic echo /rtk/raw

# 查看融合后的状态信息
rostopic echo /boat_A/state

# 查看话题列表
rostopic list
```

### 4. 传感器状态监控

#### 使用专用诊断工具 (推荐)
```bash
# 启动传感器诊断工具，实时显示RTK和IMU状态
rosrun multi_boat_control sensor_diagnostic.py
```

#### 系统日志中的传感器状态
- ✅ 正常工作：`RTK: Operating normally` / `IMU: Operating normally`
- ❌ 数据超时：`RTK: Data timeout` / `IMU: Data timeout` 
- 📊 状态摘要：每30秒报告一次传感器状态

#### 手动检查传感器数据
```bash
# 检查RTK数据频率
rostopic hz /rtk/raw

# 检查IMU数据频率  
rostopic hz /imu/data

# 查看IMU详细信息
rostopic echo /imu/data -n 1
```

## 配置参数

### RTK Node 参数
- `~port`: RTK串口地址 (默认: `/dev/ttyUSB0`)
- `~baudrate`: 波特率 (默认: `115200`)

### State Estimator Node 参数
- `~origin_latitude`: 坐标系原点纬度 (默认: `29.9983979`)
- `~origin_longitude`: 坐标系原点经度 (默认: `122.1602789`)
- `~rtk_heading_offset_deg`: RTK航向校准偏移 (默认: `0.0`)
- `~imu_heading_offset_deg`: IMU航向校准偏移 (默认: `0.0`)

## 消息格式

### RTK 消息 (`multi_boat_control/RTK`)
```
Header header
float64 latitude_deg          # 纬度（度）
float64 longitude_deg         # 经度（度）  
float64 ground_speed_mps      # 地面速度（米/秒）
float64 course_over_ground_deg # 地面航向（度）
```

### 状态消息 (`nav_msgs/Odometry`)
- **位置**：本地坐标系 (x, y) 坐标，单位米
- **方向**：四元数表示，统一到"东为0度，逆时针为正"坐标系
- **速度**：本地坐标系线速度分量

## 坐标系说明

- **GPS坐标系**：WGS84经纬度
- **本地坐标系**：以指定原点为基准，东向为X正方向，北向为Y正方向
- **航向角表示**：东为0度，逆时针为正（-180°到180°）

## 故障排除

### 常见问题
1. **串口权限问题**：
   ```bash
   sudo chmod 666 /dev/ttyUSB0
   # 或将用户加入dialout组
   sudo usermod -a -G dialout $USER
   ```

2. **没有RTK数据**：
   - 检查串口连接和设备地址
   - 确认RTK设备正常工作，输出NMEA格式数据
   - 检查波特率配置

3. **坐标转换异常**：
   - 确认原点坐标参数设置正确
   - 检查RTK数据的有效性（数据字段'A'状态）

## 开发说明

### 设计原则
- **第一性原理**：直接解决问题本质，职责分离
- **高效与简洁**：快速验证核心算法，避免过度设计
- **忠实于仿真**：严格按照MATLAB仿真算法实现
- **接口驱动**：严格遵循硬件接口文档

### 下一阶段 (Phase 2)
将实现协同控制算法节点(`surrounding_controller_node`)和硬件接口节点(`control_interface_node`)。

## 依赖项

- ROS (Melodic/Noetic)
- Python 3
- pyserial
- tf (ROS transform library)
- 标准ROS消息包：std_msgs, geometry_msgs, nav_msgs, sensor_msgs
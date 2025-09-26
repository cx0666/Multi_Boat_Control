# 完整的无人艇状态消息
# 组合RTK GPS数据和IMU朝向角信息，用于协同控制

Header header

# GPS/RTK定位信息
float64 latitude                 # 纬度（度）WGS84坐标系
float64 longitude               # 经度（度）WGS84坐标系  
float64 ground_speed_mps        # 地面速度（米/秒）
float64 course_over_ground_deg  # GPS航向角（度，真北基准）
bool gps_fix_valid              # GPS定位解算有效性

# 姿态信息（磁北坐标系）
# 重要说明：当前使用磁北坐标系（0°=磁北，90°=磁东，180°=磁南，270°=磁西）
# TODO: 后续可通过magnetic_declination参数转换为真北或数学坐标系
float64 heading_magnetic_deg    # 磁航向角 0-360°（磁北为基准，顺时针为正）
bool heading_valid              # 朝向角数据有效性

# 数据质量与时间戳
time rtk_timestamp              # RTK数据采集时间戳
time heading_timestamp          # 朝向角数据采集时间戳
float64 magnetic_declination    # 磁偏角（度，预留用于坐标系转换）

# 数据来源标识
string rtk_source              # RTK数据来源（如"RTK_GPS"）
string heading_source          # 朝向角来源（如"Pixhawk_IMU"）
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
RTK Node - RTK数据读取与发布
职责: 从RTK的USB串口读取原始NMEA语句，解析$GNRMC数据，发布为/rtk/raw话题
"""

import rospy
import serial
from multi_boat_control.msg import RTK
from std_msgs.msg import Header


class RTKNode:
    def __init__(self):
        """初始化RTK节点"""
        rospy.init_node('rtk_node', anonymous=True)
        
        # 获取ROS参数
        self.port = rospy.get_param('~port', '/dev/ttyUSB0')
        self.baudrate = rospy.get_param('~baudrate', 115200)
        
        # 创建发布者
        self.rtk_pub = rospy.Publisher('/rtk/raw', RTK, queue_size=10)
        
        # 初始化串口
        self.serial_connection = None
        self.init_serial()
        
        rospy.loginfo(f"RTK Node initialized with port: {self.port}, baudrate: {self.baudrate}")
        
    def init_serial(self):
        """初始化串口连接"""
        try:
            self.serial_connection = serial.Serial(
                port=self.port, 
                baudrate=self.baudrate, 
                timeout=1
            )
            rospy.loginfo(f"Successfully opened serial port: {self.port}")
        except serial.SerialException as e:
            rospy.logerr(f"无法打开串口 {self.port}: {e}")
            rospy.signal_shutdown("Serial port initialization failed")
    
    def parse_gnrmc_data(self, decoded_line):
        """
        解析$GNRMC数据 - 严格遵循接口使用说明.md v1.1
        Args:
            decoded_line: 解码后的NMEA语句字符串
        Returns:
            RTK message object or None if parsing fails
        """
        try:
            # 清理输入数据
            cleaned_line = decoded_line.strip()
            if not cleaned_line.startswith('$GNRMC'):
                return None
                
            # 按逗号分割数据
            data = cleaned_line.split(',')
            
            # 检查是否为$GNRMC语句且数据有效
            if len(data) >= 12 and data[0] == '$GNRMC' and data[2] == 'A':
                
                # 解析纬度 (Latitude) - 'ddmm.mmmm'格式
                if data[3] and data[4]:  # 确保数据存在
                    lat_ddmm = float(data[3])
                    lat_deg_int = int(lat_ddmm / 100)
                    lat_min_frac = (lat_ddmm - lat_deg_int * 100) / 60.0
                    latitude_deg = lat_deg_int + lat_min_frac
                    if data[4] == 'S':  # 如果是南纬，则为负
                        latitude_deg = -latitude_deg
                else:
                    return None
                
                # 解析经度 (Longitude) - 'dddmm.mmmm'格式  
                if data[5] and data[6]:  # 确保数据存在
                    lon_dddmm = float(data[5])
                    lon_deg_int = int(lon_dddmm / 100)
                    lon_min_frac = (lon_dddmm - lon_deg_int * 100) / 60.0
                    longitude_deg = lon_deg_int + lon_min_frac
                    if data[6] == 'W':  # 如果是西经，则为负
                        longitude_deg = -longitude_deg
                else:
                    return None
                
                # 解析地面速度 (Knots -> m/s)
                if data[7]:
                    speed_knots = float(data[7])
                    ground_speed_mps = speed_knots * 0.514444  # 1节 = 0.514444 m/s
                else:
                    ground_speed_mps = 0.0
                
                # 解析地面航向 (Course over ground, 度)
                if data[8]:
                    course_over_ground_deg = float(data[8])
                else:
                    course_over_ground_deg = 0.0
                
                # 创建RTK消息
                rtk_msg = RTK()
                rtk_msg.header = Header()
                rtk_msg.header.stamp = rospy.Time.now()
                rtk_msg.header.frame_id = "rtk"
                rtk_msg.latitude_deg = latitude_deg
                rtk_msg.longitude_deg = longitude_deg
                rtk_msg.ground_speed_mps = ground_speed_mps
                rtk_msg.course_over_ground_deg = course_over_ground_deg
                
                return rtk_msg
            
            return None
            
        except (IndexError, ValueError) as e:
            rospy.logwarn(f"RTK解析错误: {e}, 原始数据: {decoded_line.strip()}")
            return None
    
    def run(self):
        """主运行循环"""
        if not self.serial_connection:
            rospy.logerr("Serial connection not available")
            return
            
        rospy.loginfo("RTK Node started, reading data...")
        
        while not rospy.is_shutdown():
            try:
                # 读取串口数据
                line = self.serial_connection.readline()
                
                if line:
                    # 鲁棒的数据解码和清理
                    try:
                        # 尝试多种解码方式，忽略无效字节
                        try:
                            decoded_line = line.decode('utf-8')
                        except UnicodeDecodeError:
                            # 如果UTF-8失败，尝试忽略错误或使用latin-1
                            try:
                                decoded_line = line.decode('utf-8', errors='ignore')
                            except:
                                decoded_line = line.decode('latin-1', errors='ignore')
                        
                        # 清理数据：移除非打印字符，只保留NMEA句子
                        cleaned_line = ''.join(char for char in decoded_line if ord(char) >= 32 or char in '\r\n')
                        
                        # 查找NMEA句子（以$开头）
                        if '$' in cleaned_line:
                            # 提取从$开始的部分
                            nmea_start = cleaned_line.find('$')
                            cleaned_line = cleaned_line[nmea_start:]
                            
                            rtk_msg = self.parse_gnrmc_data(cleaned_line)
                            
                            if rtk_msg is not None:
                                # 发布RTK数据
                                self.rtk_pub.publish(rtk_msg)
                                # RTK数据输出现在由State Estimator负责（融合航向角信息）
                                rospy.logdebug(f"RTK raw data: Lat={rtk_msg.latitude_deg:.7f}, "
                                             f"Lon={rtk_msg.longitude_deg:.7f}, "
                                             f"Speed={rtk_msg.ground_speed_mps:.3f} m/s, "
                                             f"Course={rtk_msg.course_over_ground_deg:.1f}°")
                        
                    except Exception as e:
                        rospy.logwarn(f"Data processing error: {e}, raw data: {line[:50]}...")
                        continue
                        
            except Exception as e:
                rospy.logerr(f"Unexpected error in RTK node: {e}")
                continue
    
    def shutdown(self):
        """清理资源"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            rospy.loginfo("RTK serial connection closed")


if __name__ == '__main__':
    try:
        node = RTKNode()
        node.run()
    except rospy.ROSInterruptException:
        rospy.loginfo("RTK Node interrupted")
    finally:
        if 'node' in locals():
            node.shutdown()
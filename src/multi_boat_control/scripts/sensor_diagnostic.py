#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sensor Diagnostic Tool - 传感器诊断工具
用于测试和显示RTK和IMU传感器的工作状态
"""

import rospy
import math
from multi_boat_control.msg import RTK
from sensor_msgs.msg import Imu
import tf.transformations as tf_trans


class SensorDiagnostic:
    def __init__(self):
        """初始化传感器诊断工具"""
        rospy.init_node('sensor_diagnostic', anonymous=True)
        
        # 传感器状态
        self.rtk_count = 0
        self.imu_count = 0
        self.rtk_last_data = None
        self.imu_last_data = None
        
        # 创建订阅者
        self.rtk_sub = rospy.Subscriber('/rtk/raw', RTK, self.rtk_callback)
        self.imu_sub = rospy.Subscriber('/imu/data', Imu, self.imu_callback)
        
        # 创建状态报告定时器
        self.report_timer = rospy.Timer(rospy.Duration(3.0), self.print_status)
        
        rospy.loginfo("=== Sensor Diagnostic Tool Started ===")
        rospy.loginfo("Monitoring RTK (/rtk/raw) and IMU (/imu/data) topics...")
        rospy.loginfo("Press Ctrl+C to stop")
    
    def rtk_callback(self, msg):
        """RTK数据回调"""
        self.rtk_count += 1
        self.rtk_last_data = msg
        
        # 计算本地坐标 (用于显示)
        if hasattr(self, 'origin_lat'):
            x, y = self.gps_to_xy(msg.latitude_deg, msg.longitude_deg, 
                                  self.origin_lat, self.origin_lon)
        else:
            self.origin_lat = 29.9983979
            self.origin_lon = 122.1602789
            x, y = self.gps_to_xy(msg.latitude_deg, msg.longitude_deg,
                                  self.origin_lat, self.origin_lon)
        
        rospy.loginfo(f"🛰️  RTK #{self.rtk_count:04d}: "
                     f"GPS({msg.latitude_deg:.7f}, {msg.longitude_deg:.7f}) -> "
                     f"Local({x:.2f}, {y:.2f}m), "
                     f"Speed: {msg.ground_speed_mps:.2f} m/s, "
                     f"Course: {msg.course_over_ground_deg:.1f}°")
    
    def imu_callback(self, msg):
        """IMU数据回调"""
        self.imu_count += 1
        self.imu_last_data = msg
        
        # 提取航向角
        if (msg.orientation.w != 0 or msg.orientation.x != 0 or 
            msg.orientation.y != 0 or msg.orientation.z != 0):
            
            _, _, yaw = tf_trans.euler_from_quaternion([
                msg.orientation.x, msg.orientation.y, 
                msg.orientation.z, msg.orientation.w
            ])
            yaw_deg = math.degrees(yaw)
            
            # 提取角速度
            angular_vel_z = msg.angular_velocity.z
            
            # 提取加速度
            accel_x = msg.linear_acceleration.x
            accel_y = msg.linear_acceleration.y
            accel_z = msg.linear_acceleration.z
            
            rospy.loginfo(f"🧭 IMU #{self.imu_count:04d}: "
                         f"Yaw: {yaw_deg:.1f}°, "
                         f"AngVel_Z: {angular_vel_z:.3f} rad/s, "
                         f"Accel: ({accel_x:.2f}, {accel_y:.2f}, {accel_z:.2f}) m/s²")
        else:
            rospy.logwarn(f"🧭 IMU #{self.imu_count:04d}: ❌ Zero quaternion - check IMU calibration")
    
    def gps_to_xy(self, lat, lon, origin_lat, origin_lon):
        """GPS转本地坐标"""
        R = 6378137.0
        lat1 = math.radians(origin_lat)
        lon1 = math.radians(origin_lon)
        lat2 = math.radians(lat)
        lon2 = math.radians(lon)
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        x = R * dlon * math.cos(lat1)
        y = R * dlat
        
        return x, y
    
    def print_status(self, event):
        """定期打印状态摘要"""
        current_time = rospy.Time.now()
        
        # RTK状态
        rtk_status = "✅ Working" if self.rtk_count > 0 else "❌ No Data"
        rtk_hz = self.rtk_count / max(current_time.to_sec() - self.start_time.to_sec(), 1.0)
        
        # IMU状态  
        imu_status = "✅ Working" if self.imu_count > 0 else "❌ No Data"
        imu_hz = self.imu_count / max(current_time.to_sec() - self.start_time.to_sec(), 1.0)
        
        rospy.loginfo("=" * 60)
        rospy.loginfo(f"📊 SENSOR STATUS SUMMARY")
        rospy.loginfo(f"   RTK:  {rtk_status} | Count: {self.rtk_count:04d} | Rate: {rtk_hz:.1f} Hz")
        rospy.loginfo(f"   IMU:  {imu_status} | Count: {self.imu_count:04d} | Rate: {imu_hz:.1f} Hz")
        
        if self.rtk_last_data:
            rospy.loginfo(f"   Last RTK: Lat={self.rtk_last_data.latitude_deg:.7f}, "
                         f"Lon={self.rtk_last_data.longitude_deg:.7f}")
        
        if self.imu_last_data and (self.imu_last_data.orientation.w != 0 or 
                                   self.imu_last_data.orientation.x != 0 or
                                   self.imu_last_data.orientation.y != 0 or 
                                   self.imu_last_data.orientation.z != 0):
            _, _, yaw = tf_trans.euler_from_quaternion([
                self.imu_last_data.orientation.x, self.imu_last_data.orientation.y,
                self.imu_last_data.orientation.z, self.imu_last_data.orientation.w
            ])
            rospy.loginfo(f"   Last IMU: Yaw={math.degrees(yaw):.1f}°")
        
        rospy.loginfo("=" * 60)
    
    def run(self):
        """运行诊断工具"""
        self.start_time = rospy.Time.now()
        try:
            rospy.spin()
        except KeyboardInterrupt:
            rospy.loginfo("\n=== Sensor Diagnostic Finished ===")
            rospy.loginfo(f"Total RTK messages: {self.rtk_count}")
            rospy.loginfo(f"Total IMU messages: {self.imu_count}")


if __name__ == '__main__':
    try:
        diagnostic = SensorDiagnostic()
        diagnostic.run()
    except rospy.ROSInterruptException:
        rospy.loginfo("Sensor Diagnostic interrupted")
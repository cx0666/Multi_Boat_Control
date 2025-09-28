#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
IMU Simulator - IMU数据模拟器
仅用于测试时模拟IMU数据，当没有真实IMU连接时使用
"""

import rospy
import math
from sensor_msgs.msg import Imu
from geometry_msgs.msg import Quaternion, Vector3
from std_msgs.msg import Header
import tf.transformations as tf_trans


class IMUSimulator:
    def __init__(self):
        """初始化IMU模拟器"""
        rospy.init_node('imu_simulator', anonymous=True)
        
        # 创建发布者
        self.imu_pub = rospy.Publisher('/imu/data', Imu, queue_size=10)
        
        # 模拟参数
        self.current_heading = 0.0  # 当前模拟航向 (弧度)
        self.heading_rate = 0.1     # 航向变化率 (弧度/秒)
        
        # 创建定时器，以50Hz发布IMU数据
        self.timer = rospy.Timer(rospy.Duration(0.02), self.publish_imu_data)
        
        rospy.loginfo("IMU Simulator started - Publishing simulated IMU data at 50Hz")
    
    def publish_imu_data(self, event):
        """发布模拟的IMU数据"""
        current_time = rospy.Time.now()
        
        # 更新模拟航向 (简单的正弦波)
        self.current_heading += self.heading_rate * 0.02
        simulated_yaw = 0.5 * math.sin(self.current_heading)  # ±0.5弧度范围
        
        # 创建IMU消息
        imu_msg = Imu()
        imu_msg.header = Header()
        imu_msg.header.stamp = current_time
        imu_msg.header.frame_id = "imu_link"
        
        # 设置方向 (只设置yaw，其他为0)
        quaternion = tf_trans.quaternion_from_euler(0, 0, simulated_yaw)
        imu_msg.orientation = Quaternion(
            x=quaternion[0],
            y=quaternion[1],
            z=quaternion[2],
            w=quaternion[3]
        )
        
        # 设置角速度 (模拟)
        imu_msg.angular_velocity = Vector3(
            x=0.0,
            y=0.0,
            z=self.heading_rate * math.cos(self.current_heading) * 0.5
        )
        
        # 设置线性加速度 (模拟重力)
        imu_msg.linear_acceleration = Vector3(
            x=0.0,
            y=0.0,
            z=9.81
        )
        
        # 设置协方差矩阵 (模拟不确定性)
        imu_msg.orientation_covariance = [0.1, 0.0, 0.0,
                                         0.0, 0.1, 0.0,
                                         0.0, 0.0, 0.05]  # yaw方向精度更高
        
        imu_msg.angular_velocity_covariance = [0.01, 0.0, 0.0,
                                              0.0, 0.01, 0.0,
                                              0.0, 0.0, 0.005]
        
        imu_msg.linear_acceleration_covariance = [0.1, 0.0, 0.0,
                                                 0.0, 0.1, 0.0,
                                                 0.0, 0.0, 0.1]
        
        # 发布消息
        self.imu_pub.publish(imu_msg)
        
        rospy.logdebug(f"Published simulated IMU data: yaw={math.degrees(simulated_yaw):.1f}°")


if __name__ == '__main__':
    try:
        simulator = IMUSimulator()
        rospy.spin()
    except rospy.ROSInterruptException:
        rospy.loginfo("IMU Simulator interrupted")
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
End-to-End Integration Tester
端到端集成测试节点

Purpose: 验证完整的"感知->决策->执行"闭环链路
Architecture: /boat_state (感知) -> P Controller (决策) -> cmd_vel (执行)

严格遵循绝对简洁原则：仅实现航向角闭环控制，零冗余功能
Author: Multi-Boat Team
"""

import rospy
import threading
from geometry_msgs.msg import Twist
from multi_boat_control.msg import BoatState


class EndToEndTester:
    """
    最简化航向角闭环控制器
    职责：验证从状态感知到电机执行的完整链路
    """
    
    def __init__(self):
        rospy.init_node('end_to_end_tester', log_level=rospy.INFO)
        rospy.loginfo("=== End-to-End Integration Tester Starting ===")
        
        # P控制器参数（硬编码，安全值）
        self.kp = 0.5  # 比例增益
        
        # 状态变量
        self.current_heading = None
        self.target_heading = 0.0
        self.data_lock = threading.Lock()
        
        # ROS接口
        self.boat_state_sub = rospy.Subscriber('/boat_state', BoatState, self.state_callback, queue_size=1)
        self.cmd_vel_pub = rospy.Publisher('/control_interface_node/cmd_vel', Twist, queue_size=1)
        
        # 启动用户输入线程
        self.shutdown_flag = False
        self.input_thread = threading.Thread(target=self.input_loop)
        self.input_thread.daemon = True
        self.input_thread.start()
        
        rospy.loginfo("=== End-to-End Tester Ready ===")
    
    def state_callback(self, msg):
        """处理船只状态消息"""
        if msg.heading_valid:
            with self.data_lock:
                self.current_heading = msg.heading_magnetic_deg
            self.compute_and_publish_control()
        else:
            rospy.logwarn("Received invalid heading data")
    
    def normalize_angle_error(self, target, current):
        """
        计算角度误差，正确处理回绕问题
        返回 [-180, 180] 范围内的误差
        """
        error = target - current
        while error > 180:
            error -= 360
        while error < -180:
            error += 360
        return error
    
    def compute_and_publish_control(self):
        """计算并发布控制指令（核心P控制器）"""
        with self.data_lock:
            if self.current_heading is None:
                return
            
            # 计算角度误差
            error = self.normalize_angle_error(self.target_heading, self.current_heading)
            
            # P控制器
            yaw_rate = self.kp * error
            
            # 创建并发布Twist消息
            cmd = Twist()
            cmd.linear.x = 0.0  # 无前进运动
            cmd.angular.z = yaw_rate
            
            self.cmd_vel_pub.publish(cmd)
            
            rospy.logdebug("Control: target=%.1f°, current=%.1f°, error=%.1f°, yaw_rate=%.4f", 
                          self.target_heading, self.current_heading, error, yaw_rate)
    
    def input_loop(self):
        """用户输入循环（在当前终端中运行）"""
        rospy.loginfo("Enter target heading (0-360 degrees, magnetic north):")
        
        while not rospy.is_shutdown() and not self.shutdown_flag:
            try:
                user_input = input("Target heading (0-360°): ").strip()
                
                try:
                    target = float(user_input)
                    if 0 <= target <= 360:
                        with self.data_lock:
                            self.target_heading = target
                        rospy.loginfo("New target heading: %.1f° (magnetic north)", target)
                        
                        if self.current_heading is not None:
                            error = self.normalize_angle_error(target, self.current_heading)
                            rospy.loginfo("Current: %.1f°, Error: %.1f°", self.current_heading, error)
                    else:
                        print("Error: Heading must be between 0 and 360 degrees")
                        
                except ValueError:
                    print("Error: Please enter a valid number")
                    
            except (EOFError, KeyboardInterrupt):
                rospy.loginfo("Input interrupted, shutting down...")
                self.shutdown_flag = True
                rospy.signal_shutdown("User interrupt")
                break
    
    def run(self):
        """主运行循环"""
        try:
            rospy.spin()
        except KeyboardInterrupt:
            pass
        finally:
            # 发送停止指令
            stop_cmd = Twist()
            self.cmd_vel_pub.publish(stop_cmd)
            rospy.loginfo("Stop command sent")


def main():
    try:
        tester = EndToEndTester()
        tester.run()
    except rospy.ROSInterruptException:
        pass


if __name__ == '__main__':
    main()
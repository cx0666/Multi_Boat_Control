#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Network Monitor Node - 网络通信验证节点

职责：验证多艇间的状态通信是否正常工作
功能：订阅所有艇的boat_state消息，打印接收信息和数据时效性

严格遵循简洁原则：仅实现消息接收和日志打印，无其他功能
"""

import rospy
from multi_boat_control.msg import BoatState


class NetworkMonitor:
    """
    网络监控节点 - 验证多艇通信
    
    为每个已知的艇创建独立订阅者，确保能够准确识别消息来源
    """
    
    def __init__(self):
        """初始化网络监控节点"""
        rospy.init_node('network_monitor', log_level=rospy.INFO)
        rospy.loginfo("=== Network Monitor Node Starting ===")
        
        # 已知的艇名列表
        self.boat_names = ['boat1', 'boat2', 'target']
        
        # 为每个艇创建独立的订阅者
        self.subscribers = {}
        for boat_name in self.boat_names:
            topic_name = f'/{boat_name}/boat_state'
            # 修复闭包问题：使用functools.partial或者定义独立的回调函数
            def create_callback(name):
                return lambda msg: self.boat_state_callback(msg, name)
            
            self.subscribers[boat_name] = rospy.Subscriber(
                topic_name,
                BoatState,
                create_callback(boat_name),
                queue_size=10
            )
            rospy.loginfo(f"Subscribed to: {topic_name}")
        
        rospy.loginfo("Network Monitor ready for multi-boat communication validation")
    
    def boat_state_callback(self, msg, boat_name):
        """
        处理艇状态消息的回调函数
        
        Args:
            msg (BoatState): 艇状态消息
            boat_name (str): 艇名称
        """
        # 计算消息时效性
        current_time = rospy.Time.now()
        message_time = msg.header.stamp
        age_seconds = (current_time - message_time).to_sec()
        
        # 打印格式化日志（按要求的格式）
        rospy.loginfo("Received state from '%s'. Age: %.2f seconds.", 
                     boat_name, age_seconds)
    
    def run(self):
        """运行网络监控节点"""
        try:
            rospy.spin()
        except KeyboardInterrupt:
            rospy.loginfo("Network Monitor shutting down...")


def main():
    """主入口函数"""
    try:
        monitor = NetworkMonitor()
        monitor.run()
    except rospy.ROSInterruptException:
        pass


if __name__ == '__main__':
    main()
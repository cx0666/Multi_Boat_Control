#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Device Checker - 设备状态检查工具

功能：
1. 检查串口设备是否存在和可访问
2. 验证设备独占访问
3. 检测设备冲突
4. 提供设备健康状态报告

在boat节点启动前运行，确保设备可用性
"""

import os
import sys
import time
import fcntl
import serial
import rospy
from std_msgs.msg import Bool, String


class DeviceChecker:
    """设备检查器"""
    
    def __init__(self):
        """初始化设备检查器"""
        rospy.init_node('device_checker', log_level=rospy.INFO)
        
        # 获取参数
        self.boat_id = rospy.get_param('~boat_id', 'unknown')
        self.rtk_device = rospy.get_param('~rtk_device', '/dev/ttyUSB0')
        self.pixhawk_device = rospy.get_param('~pixhawk_device', '/dev/ttyUSB1')
        self.check_exclusive = rospy.get_param('~check_exclusive_access', True)
        
        rospy.loginfo(f"=== Device Checker for {self.boat_id} ===")
        rospy.loginfo(f"RTK Device: {self.rtk_device}")
        rospy.loginfo(f"Pixhawk Device: {self.pixhawk_device}")
        
        # 发布器
        self.status_pub = rospy.Publisher(f'~device_status', String, queue_size=1)
        self.rtk_status_pub = rospy.Publisher(f'~rtk_device_ok', Bool, queue_size=1)
        self.pixhawk_status_pub = rospy.Publisher(f'~pixhawk_device_ok', Bool, queue_size=1)
        
        # 执行检查
        self.run_checks()
    
    def check_device_exists(self, device_path):
        """检查设备是否存在"""
        if not os.path.exists(device_path):
            rospy.logerr(f"❌ Device not found: {device_path}")
            return False
        
        if not os.access(device_path, os.R_OK | os.W_OK):
            rospy.logerr(f"❌ Device not accessible: {device_path}")
            return False
        
        rospy.loginfo(f"✅ Device exists and accessible: {device_path}")
        return True
    
    def check_device_exclusive_access(self, device_path):
        """检查设备是否可以独占访问"""
        if not self.check_exclusive:
            return True
        
        try:
            # 尝试打开设备进行独占访问测试
            with open(device_path, 'r+b') as device_file:
                try:
                    # 尝试获取独占锁
                    fcntl.flock(device_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    rospy.loginfo(f"✅ Device available for exclusive access: {device_path}")
                    fcntl.flock(device_file.fileno(), fcntl.LOCK_UN)
                    return True
                except (IOError, OSError) as e:
                    rospy.logerr(f"❌ Device busy (already in use): {device_path} - {e}")
                    return False
                    
        except Exception as e:
            rospy.logerr(f"❌ Failed to check exclusive access for {device_path}: {e}")
            return False
    
    def check_serial_device(self, device_path, device_type):
        """检查串口设备的详细状态"""
        rospy.loginfo(f"🔍 Checking {device_type} device: {device_path}")
        
        # 基本存在性检查
        if not self.check_device_exists(device_path):
            return False
        
        # 独占访问检查
        if not self.check_device_exclusive_access(device_path):
            return False
        
        # 尝试串口连接测试
        try:
            if device_type == 'RTK':
                baudrate = 115200
            elif device_type == 'Pixhawk':
                baudrate = 921600
            else:
                baudrate = 115200
            
            # 短暂连接测试
            with serial.Serial(device_path, baudrate, timeout=1) as ser:
                time.sleep(0.1)  # 短暂等待
                rospy.loginfo(f"✅ {device_type} serial connection test passed: {device_path}")
                return True
                
        except serial.SerialException as e:
            rospy.logerr(f"❌ {device_type} serial connection failed: {device_path} - {e}")
            return False
        except Exception as e:
            rospy.logerr(f"❌ Unexpected error testing {device_type} device: {device_path} - {e}")
            return False
    
    def get_device_info(self, device_path):
        """获取设备详细信息"""
        try:
            import serial.tools.list_ports
            
            ports = serial.tools.list_ports.comports()
            for port in ports:
                if port.device == device_path:
                    info = {
                        'device': port.device,
                        'description': port.description or 'Unknown',
                        'hwid': port.hwid or 'Unknown',
                        'vid': port.vid,
                        'pid': port.pid,
                        'serial_number': port.serial_number,
                        'manufacturer': port.manufacturer or 'Unknown'
                    }
                    return info
            
            # 如果没找到，返回基本信息
            return {
                'device': device_path,
                'description': 'Generic Serial Device',
                'exists': os.path.exists(device_path)
            }
            
        except Exception as e:
            rospy.logwarn(f"Failed to get device info for {device_path}: {e}")
            return {'device': device_path, 'error': str(e)}
    
    def run_checks(self):
        """运行所有设备检查"""
        rospy.loginfo("🚀 Starting device checks...")
        
        # 检查RTK设备
        rtk_ok = False
        if self.rtk_device and self.rtk_device != '/dev/null':
            rtk_info = self.get_device_info(self.rtk_device)
            rospy.loginfo(f"📡 RTK Device Info: {rtk_info}")
            rtk_ok = self.check_serial_device(self.rtk_device, 'RTK')
        else:
            rospy.loginfo("📡 RTK device check skipped (disabled)")
            rtk_ok = True
        
        # 检查Pixhawk设备
        pixhawk_ok = False
        if self.pixhawk_device and self.pixhawk_device != '/dev/null':
            pixhawk_info = self.get_device_info(self.pixhawk_device)
            rospy.loginfo(f"🚁 Pixhawk Device Info: {pixhawk_info}")
            pixhawk_ok = self.check_serial_device(self.pixhawk_device, 'Pixhawk')
        else:
            rospy.loginfo("🚁 Pixhawk device check skipped (disabled)")
            pixhawk_ok = True
        
        # 发布状态
        self.publish_status(rtk_ok, pixhawk_ok)
        
        # 总结报告
        self.print_summary(rtk_ok, pixhawk_ok)
        
        # 如果有设备问题，提供建议
        if not (rtk_ok and pixhawk_ok):
            self.provide_troubleshooting_advice()
    
    def publish_status(self, rtk_ok, pixhawk_ok):
        """发布设备状态"""
        # 发布详细状态
        if rtk_ok and pixhawk_ok:
            status_msg = "ALL_DEVICES_OK"
        elif rtk_ok:
            status_msg = "RTK_OK_PIXHAWK_FAILED"
        elif pixhawk_ok:
            status_msg = "RTK_FAILED_PIXHAWK_OK"
        else:
            status_msg = "ALL_DEVICES_FAILED"
        
        self.status_pub.publish(String(data=status_msg))
        self.rtk_status_pub.publish(Bool(data=rtk_ok))
        self.pixhawk_status_pub.publish(Bool(data=pixhawk_ok))
        
        rospy.loginfo(f"📊 Device status published: {status_msg}")
    
    def print_summary(self, rtk_ok, pixhawk_ok):
        """打印检查摘要"""
        print("\n" + "="*60)
        print(f"📋 Device Check Summary for {self.boat_id}")
        print("="*60)
        print(f"📡 RTK Device ({self.rtk_device}): {'✅ OK' if rtk_ok else '❌ FAILED'}")
        print(f"🚁 Pixhawk Device ({self.pixhawk_device}): {'✅ OK' if pixhawk_ok else '❌ FAILED'}")
        print(f"🎯 Overall Status: {'✅ ALL OK' if (rtk_ok and pixhawk_ok) else '❌ ISSUES DETECTED'}")
        print("="*60)
    
    def provide_troubleshooting_advice(self):
        """提供故障排除建议"""
        print("\n🔧 Troubleshooting Advice:")
        print("1. Check physical connections:")
        print("   - Ensure USB cables are properly connected")
        print("   - Try different USB ports")
        print("   - Check for loose connections")
        print()
        print("2. Check device permissions:")
        print("   sudo chmod 666 /dev/ttyUSB*")
        print("   sudo usermod -a -G dialout $USER")
        print()
        print("3. Check for device conflicts:")
        print("   lsof /dev/ttyUSB*")
        print("   ps aux | grep ttyUSB")
        print()
        print("4. List available devices:")
        print("   ls -la /dev/ttyUSB*")
        print("   dmesg | grep ttyUSB")
        print()
        print("5. Check device mapping:")
        print("   python3 serial_device_mapper.py --list")


def main():
    """主函数"""
    try:
        checker = DeviceChecker()
        rospy.loginfo("Device checker completed")
        
        # 保持节点运行一段时间以发布状态
        rospy.sleep(2.0)
        
    except rospy.ROSInterruptException:
        rospy.loginfo("Device checker interrupted")
    except Exception as e:
        rospy.logerr(f"Device checker failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

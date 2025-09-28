#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Control Interface Node - "执行者" (The Executor)

Enhanced version based on reference motion_control.py architecture.
This node serves as the complete bridge between ROS control system and Pixhawk hardware,
integrating:
- Vehicle connection and initialization (from motion_control.py)
- IMU data publishing (from motion_control.py + __init__.py)
- Velocity command execution (from circle.py)
- Heading data publishing for state estimation

Architecture: Uses ExtendedVehicle class instead of composition pattern
Key Responsibilities:
1. Connect to Pixhawk and maintain connection
2. Initialize autopilot (GUIDED mode + ARM)
3. Publish IMU and heading data for state estimation
4. Execute velocity commands from ROS
5. Monitor system health and handle reconnection

Based on: motion_control.py, circle.py, __init__.py references
Author: Multi-Boat Team
Version: 2.0.0
"""

import rospy
import time
import threading
import argparse
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool, Float64
from sensor_msgs.msg import Imu

# Import our extended vehicle class
from vehicle_extensions import create_extended_vehicle, ExtendedVehicle

try:
    from dronekit import VehicleMode
    from pymavlink import mavutil
except ImportError as e:
    rospy.logerr("Failed to import dronekit/pymavlink: %s", e)
    raise e


class ControlInterfaceNode:
    """
    Enhanced Control Interface Node using ExtendedVehicle.
    
    This implementation follows the proven architecture from motion_control.py
    while integrating the extended capabilities for multi-boat coordination.
    """
    
    def __init__(self):
        """Initialize the control interface node."""
        rospy.init_node('control_interface_node', log_level=rospy.INFO)
        rospy.loginfo("=== Enhanced Control Interface Node Starting ===")
        
        # Configuration from ROS parameters
        self.connect_string = rospy.get_param('~connect_string', '/dev/ttyUSB0')
        self.baud_rate = rospy.get_param('~baud_rate', 921600)
        self.connection_timeout = rospy.get_param('~connection_timeout', 60)
        self.max_init_retries = rospy.get_param('~max_init_retries', 5)
        self.publish_rate = rospy.get_param('~publish_rate', 10.0)  # Hz
        
        # Safety limits (generous, assuming upper layer handles fine control)
        self.max_forward_speed = rospy.get_param('~max_forward_speed', 4.0)   # m/s
        self.min_forward_speed = rospy.get_param('~min_forward_speed', -1.0)  # m/s
        self.max_yaw_rate = rospy.get_param('~max_yaw_rate', 2.0)        # rad/s
        self.min_yaw_rate = rospy.get_param('~min_yaw_rate', -2.0)       # rad/s
        
        rospy.loginfo("Configuration:")
        rospy.loginfo("  Connect: %s @ %d baud", self.connect_string, self.baud_rate)
        rospy.loginfo("  Safety: vx∈[%.1f,%.1f]m/s, yaw_rate∈[%.1f,%.1f]rad/s", 
                     self.min_forward_speed, self.max_forward_speed,
                     self.min_yaw_rate, self.max_yaw_rate)
        
        # Vehicle connection
        self.vehicle = None
        self.connected = False
        self.initialized = False
        
        # Threading control
        self.should_shutdown = False
        self.connection_lock = threading.Lock()
        self.command_lock = threading.Lock()
        
        # ROS interfaces
        self.cmd_vel_sub = None
        self.status_pub = rospy.Publisher('~status', Bool, queue_size=1)
        
        # Internal publisher for state estimator
        self.heading_pub = rospy.Publisher('/boat/heading', Float64, queue_size=1)
        
        # Connect and initialize vehicle
        self.connect_to_vehicle()
        
        if self.connected and self.initialized:
            self.setup_ros_interfaces()
            self.start_publishing_threads()
            rospy.loginfo("=== Control Interface Node Ready ===")
            
            # 立即尝试输出一次航向角数据用于测试
            if self.vehicle and self.vehicle.heading is not None:
                rospy.loginfo("🧭 Pixhawk航向角: %.1f° (磁北基准, DroneKit获取) - 初始读取", 
                            self.vehicle.heading)
            else:
                rospy.loginfo("🧭 等待Pixhawk航向角数据... (可能需要几秒钟)")
        else:
            rospy.logerr("Initialization failed. Node shutting down.")
            rospy.signal_shutdown("Vehicle initialization failed")
    
    def connect_to_vehicle(self):
        """
        Connect to vehicle using ExtendedVehicle class.
        
        Based on motion_control.py connection pattern with enhanced error handling.
        """
        max_attempts = 3
        
        for attempt in range(1, max_attempts + 1):
            rospy.loginfo("Connection attempt %d/%d to %s", 
                         attempt, max_attempts, self.connect_string)
            
            try:
                # Use our extended vehicle creation function
                self.vehicle = create_extended_vehicle(
                    self.connect_string,
                    baud_rate=self.baud_rate,
                    wait_ready=True,
                    timeout=self.connection_timeout
                )
                
                rospy.loginfo("✓ Vehicle connected successfully")
                
                # Setup ROS publishers for the vehicle
                self.vehicle.setup_ros_publishers("boat/")
                
                self.connected = True
                
                # Initialize the boat after successful connection
                if self.initialize_boat():
                    self.initialized = True
                    return
                else:
                    rospy.logwarn("Connected but initialization failed, retrying...")
                    self.disconnect_vehicle()
                    
            except Exception as e:
                rospy.logerr("Connection attempt %d failed: %s", attempt, str(e))
                if self.vehicle:
                    try:
                        self.vehicle.close()
                    except:
                        pass
                    self.vehicle = None
                
                if attempt < max_attempts:
                    rospy.loginfo("Waiting 5 seconds before next attempt...")
                    time.sleep(5)
        
        rospy.logerr("All connection attempts failed")
        self.connected = False
        self.initialized = False
    
    def disconnect_vehicle(self):
        """Safely disconnect from vehicle."""
        if self.vehicle:
            try:
                rospy.loginfo("Disconnecting from vehicle...")
                self.vehicle.close()
            except Exception as e:
                rospy.logwarn("Error during disconnection: %s", e)
            finally:
                self.vehicle = None
                self.connected = False
                self.initialized = False
    
    def initialize_boat(self):
        """
        Initialize boat following motion_control.py arm_and_go pattern.
        
        Sequence:
        1. Wait for vehicle to be armable
        2. Set GUIDED mode
        3. ARM the vehicle
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.vehicle:
            rospy.logerr("Cannot initialize: no vehicle connection")
            return False
        
        rospy.loginfo("Starting boat initialization sequence...")
        
        for attempt in range(1, self.max_init_retries + 1):
            rospy.loginfo("Initialization attempt %d/%d", attempt, self.max_init_retries)
            
            try:
                # Step 1: Wait for armable (from motion_control.py)
                rospy.loginfo("Step 1: Waiting for vehicle to be armable...")
                timeout = 0
                while not self.vehicle.is_armable and timeout < 30:
                    rospy.loginfo("  Waiting for armable... (%ds)", timeout)
                    time.sleep(1)
                    timeout += 1
                
                if not self.vehicle.is_armable:
                    rospy.logwarn("  ✗ Vehicle not armable after 30s (attempt %d)", attempt)
                    continue
                
                rospy.loginfo("  ✓ Vehicle is armable")
                
                # Step 2: Set GUIDED mode (from motion_control.py)
                rospy.loginfo("Step 2: Setting GUIDED mode...")
                self.vehicle.mode = VehicleMode("GUIDED")
                
                timeout = 0
                while self.vehicle.mode.name != "GUIDED" and timeout < 10:
                    rospy.loginfo("  Waiting for GUIDED mode... (current: %s)", 
                                self.vehicle.mode.name)
                    time.sleep(1)
                    timeout += 1
                
                if self.vehicle.mode.name != "GUIDED":
                    rospy.logwarn("  ✗ Failed to set GUIDED mode (attempt %d)", attempt)
                    continue
                
                rospy.loginfo("  ✓ Mode set to GUIDED")
                
                # Step 3: ARM the vehicle (from motion_control.py)
                rospy.loginfo("Step 3: Arming vehicle...")
                self.vehicle.armed = True
                
                timeout = 0
                while not self.vehicle.armed and timeout < 10:
                    rospy.loginfo("  Waiting for arming... (%ds)", timeout)
                    time.sleep(1)
                    timeout += 1
                
                if not self.vehicle.armed:
                    rospy.logwarn("  ✗ Failed to arm vehicle (attempt %d)", attempt)
                    continue
                
                rospy.loginfo("  ✓ Vehicle armed successfully")
                rospy.loginfo("🎉 Boat initialization completed!")
                return True
                
            except Exception as e:
                rospy.logerr("Exception during initialization attempt %d: %s", attempt, e)
                time.sleep(2)
        
        rospy.logerr("❌ All initialization attempts failed")
        return False
    
    def setup_ros_interfaces(self):
        """Setup ROS subscriber for velocity commands."""
        rospy.loginfo("Setting up ROS interfaces...")
        
        self.cmd_vel_sub = rospy.Subscriber(
            '~cmd_vel',
            Twist,
            self.cmd_vel_callback,
            queue_size=1
        )
        
        rospy.loginfo("✓ ROS interfaces configured")
    
    def start_publishing_threads(self):
        """
        Start publishing threads for IMU and heading data.
        
        Based on motion_control.py threading approach.
        """
        rospy.loginfo("Starting data publishing threads...")
        
        # IMU publishing thread
        self.imu_thread = threading.Thread(target=self.imu_publishing_loop)
        self.imu_thread.daemon = True
        self.imu_thread.start()
        
        # Heading publishing thread  
        self.heading_thread = threading.Thread(target=self.heading_publishing_loop)
        self.heading_thread.daemon = True
        self.heading_thread.start()
        
        # Connection monitoring thread
        self.monitor_thread = threading.Thread(target=self.connection_monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        rospy.loginfo("✓ Publishing threads started")
    
    def imu_publishing_loop(self):
        """
        IMU data publishing loop.
        
        Publishes sensor_msgs/Imu at the configured rate.
        Based on motion_control.py imu_msg_pub function.
        """
        rate = rospy.Rate(self.publish_rate)
        
        while not rospy.is_shutdown() and not self.should_shutdown:
            try:
                if self.vehicle and self.connected:
                    self.vehicle.publish_imu_data()
                    
                rate.sleep()
                
            except Exception as e:
                rospy.logwarn("Error in IMU publishing loop: %s", e)
                time.sleep(0.1)  # Brief pause on error
    
    def heading_publishing_loop(self):
        """
        Heading data publishing loop for state estimator.
        
        Publishes Float64 heading data at configured rate.
        Note: Heading is in magnetic north coordinate system (0°=North, 90°=East)
        """
        rate = rospy.Rate(self.publish_rate)
        rospy.loginfo("🧭 航向角发布线程已启动，等待Pixhawk数据...")
        
        # 立即尝试获取一次航向角数据
        try:
            if self.vehicle and self.connected and self.vehicle.heading is not None:
                rospy.loginfo("🧭 Pixhawk航向角: %.1f° (磁北基准, DroneKit获取) - 线程启动时读取", 
                            self.vehicle.heading)
        except:
            pass
        
        while not rospy.is_shutdown() and not self.should_shutdown:
            try:
                if self.vehicle and self.connected:
                    if self.vehicle.heading is not None:
                        heading_msg = Float64()
                        heading_msg.data = float(self.vehicle.heading)  # Magnetic north, 0-360°
                        self.heading_pub.publish(heading_msg)
                        
                        # 航向角数据已由State Estimator输出，这里只做调试输出
                        rospy.logdebug("🧭 Pixhawk航向角: %.1f° (磁北基准, DroneKit获取)", 
                                    self.vehicle.heading)
                    else:
                        rospy.logwarn_throttle(5, "🧭 Pixhawk航向角数据不可用 (vehicle.heading=None)")
                else:
                    rospy.logwarn_throttle(5, "🧭 等待Pixhawk连接...")
                    
                rate.sleep()
                
            except Exception as e:
                rospy.logwarn("Error in heading publishing loop: %s", e)
                time.sleep(0.1)
    
    def connection_monitoring_loop(self):
        """
        Connection health monitoring loop with automatic reconnection.
        
        Based on motion_control.py connection management approach.
        """
        rate = rospy.Rate(1.0)  # Check every 1 second
        
        while not rospy.is_shutdown() and not self.should_shutdown:
            try:
                # Publish node status
                status_msg = Bool()
                status_msg.data = self.connected and self.initialized
                self.status_pub.publish(status_msg)
                
                # Check connection health
                if self.vehicle and self.connected:
                    try:
                        # Test connection by accessing vehicle attribute
                        _ = self.vehicle.armed
                    except Exception as e:
                        rospy.logwarn("Connection health check failed: %s", e)
                        self.attempt_reconnection()
                
                rate.sleep()
                
            except Exception as e:
                rospy.logwarn("Error in monitoring loop: %s", e)
                time.sleep(1.0)
    
    def cmd_vel_callback(self, msg):
        """
        Handle velocity command messages.
        
        Args:
            msg (geometry_msgs/Twist): Velocity command
        """
        if not (self.connected and self.initialized):
            rospy.logwarn("Received cmd_vel but vehicle not ready")
            return
        
        with self.command_lock:
            # Extract commands
            vx = float(msg.linear.x)
            yaw_rate = float(msg.angular.z)
            
            # Apply safety limits
            vx = max(self.min_forward_speed, min(vx, self.max_forward_speed))
            yaw_rate = max(self.min_yaw_rate, min(yaw_rate, self.max_yaw_rate))
            
            # Send command using ExtendedVehicle method
            try:
                self.vehicle.send_body_ned_velocity(vx, yaw_rate)
                rospy.logdebug("Executed cmd_vel: vx=%.2f m/s, yaw_rate=%.2f rad/s", 
                              vx, yaw_rate)
                
            except Exception as e:
                rospy.logerr("Failed to execute velocity command: %s", e)
                self.attempt_reconnection()
    
    def attempt_reconnection(self):
        """Attempt to reconnect to the vehicle."""
        with self.connection_lock:
            if not self.connected:
                return  # Already reconnecting
            
            rospy.logwarn("Attempting vehicle reconnection...")
            self.disconnect_vehicle()
            time.sleep(2)
            
            self.connect_to_vehicle()
            
            if self.connected and self.initialized:
                rospy.loginfo("✓ Vehicle reconnection successful")
            else:
                rospy.logerr("✗ Vehicle reconnection failed")
    
    def shutdown(self):
        """Clean shutdown procedure."""
        rospy.loginfo("Control Interface Node shutting down...")
        self.should_shutdown = True
        
        # Send stop command
        if self.connected and self.initialized:
            try:
                rospy.loginfo("Sending stop command...")
                with self.command_lock:
                    self.vehicle.send_body_ned_velocity(0.0, 0.0)
                time.sleep(0.5)
            except Exception as e:
                rospy.logwarn("Error sending stop command: %s", e)
        
        # Disconnect vehicle
        self.disconnect_vehicle()
        rospy.loginfo("✓ Control Interface Node shutdown complete")
    
    def run(self):
        """Main execution loop."""
        try:
            # Keep node alive
            rospy.spin()
            
        except KeyboardInterrupt:
            rospy.loginfo("Keyboard interrupt received")
        except Exception as e:
            rospy.logerr("Unexpected error: %s", e)
        finally:
            self.shutdown()


def main():
    """Main entry point."""
    try:
        node = ControlInterfaceNode()
        node.run()
        return 0
        
    except rospy.ROSInterruptException:
        rospy.loginfo("ROS interrupt received")
        return 0
    except Exception as e:
        rospy.logerr("Fatal error: %s", e)
        return 1


if __name__ == '__main__':
    exit(main())
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Vehicle Extensions Module

This module extends the standard DroneKit Vehicle class with additional
functionality needed for multi-boat control, specifically:
1. RAW_IMU data access (learned from __init__.py reference)
2. ROS integration capabilities
3. Enhanced error handling and connection management

Key additions:
- raw_imu property for linear acceleration data
- ROS publisher integration
- Thread-safe vehicle operations

Based on: reference __init__.py modifications
Author: Multi-Boat Team
Version: 1.0.0
"""

import rospy
import threading
import time

# ROS message imports
try:
    from geometry_msgs.msg import Vector3
    from sensor_msgs.msg import Imu
    from std_msgs.msg import Float64, Bool
    from tf.transformations import quaternion_from_euler
    rospy.logdebug("ROS message imports successful")
except ImportError as e:
    rospy.logerr("Failed to import ROS messages: %s", e)
    raise e

# DroneKit imports
try:
    from dronekit import Vehicle, connect
    from pymavlink import mavutil
    rospy.logdebug("DroneKit imports successful")
except ImportError as e:
    rospy.logerr("Failed to import dronekit/pymavlink: %s", e)
    print("Error: dronekit or pymavlink not installed.")
    print("Install with: pip3 install dronekit pymavlink")
    raise e


class ExtendedVehicle(Vehicle):
    """
    Extended Vehicle class with additional IMU capabilities and ROS integration.
    
    This class extends the standard DroneKit Vehicle to add:
    - RAW_IMU message monitoring (from reference __init__.py)
    - ROS publisher integration for IMU data
    - Enhanced connection management
    - Thread-safe operations
    """
    
    def __init__(self, handler):
        """Initialize the extended vehicle."""
        super(ExtendedVehicle, self).__init__(handler)
        
        # Initialize extended IMU attributes (from reference __init__.py)
        self._xacc = None
        self._yacc = None  
        self._zacc = None
        self._xgyro = None
        self._ygyro = None
        self._zgyro = None
        
        # Setup RAW_IMU message monitoring
        self._setup_raw_imu_monitoring()
        
        # ROS integration
        self._ros_publishers = {}
        self._ros_initialized = False
        
        rospy.loginfo("Extended Vehicle initialized with RAW_IMU support")
    
    def _setup_raw_imu_monitoring(self):
        """
        Setup RAW_IMU message monitoring.
        
        This implementation is directly adapted from the reference __init__.py,
        adding the ability to access raw acceleration data from Pixhawk.
        """
        @self.on_message('RAW_IMU')
        def raw_imu_listener(vehicle, name, msg):
            """Handle RAW_IMU messages from autopilot."""
            try:
                # Convert from milliG to m/s² (factor of 100 from reference)
                self._xacc = msg.xacc / 100.0
                self._yacc = msg.yacc / 100.0
                self._zacc = msg.zacc / 100.0
                
                # Optional: store gyro data for future use
                self._xgyro = msg.xgyro
                self._ygyro = msg.ygyro  
                self._zgyro = msg.zgyro
                
                # Notify listeners of raw_imu updates
                self.notify_attribute_listeners('raw_imu', self.raw_imu)
                
            except Exception as e:
                rospy.logwarn_throttle(5, "Error processing RAW_IMU message: %s", e)
    
    @property
    def raw_imu(self):
        """
        Current linear acceleration as a three-element list [xacc, yacc, zacc] (in m/s²).
        
        This property provides access to raw acceleration data from the autopilot's
        IMU, directly adapted from reference __init__.py implementation.
        
        Returns:
            list: [x_accel, y_accel, z_accel] in m/s², or [None, None, None] if not available
        """
        return [self._xacc, self._yacc, self._zacc]
    
    def setup_ros_publishers(self, node_name_prefix=""):
        """
        Setup ROS publishers for vehicle data.
        
        Args:
            node_name_prefix (str): Prefix for topic names (e.g., "boat1_")
        """
        if self._ros_initialized:
            rospy.logwarn("ROS publishers already initialized")
            return
        
        try:
            # IMU data publisher (compatible with sensor_msgs/Imu)
            self._ros_publishers['imu'] = rospy.Publisher(
                f'{node_name_prefix}imu/data', 
                Imu, 
                queue_size=1
            )
            
            # Heading data publisher
            self._ros_publishers['heading'] = rospy.Publisher(
                f'{node_name_prefix}heading', 
                Float64, 
                queue_size=1
            )
            
            # Connection status publisher
            self._ros_publishers['connected'] = rospy.Publisher(
                f'{node_name_prefix}connected', 
                Bool, 
                queue_size=1
            )
            
            self._ros_initialized = True
            rospy.loginfo("ROS publishers initialized for extended vehicle")
            
        except Exception as e:
            rospy.logerr("Failed to setup ROS publishers: %s", e)
            raise e
    
    def publish_imu_data(self):
        """
        Publish IMU data to ROS topic.
        
        This method creates and publishes a sensor_msgs/Imu message containing:
        - Orientation (from vehicle.attitude)
        - Angular velocity (from vehicle.attitude rates)  
        - Linear acceleration (from raw_imu)
        
        Based on: reference motion_control.py imu_msg_pub function
        """
        if not self._ros_initialized:
            rospy.logwarn("ROS publishers not initialized, cannot publish IMU data")
            return
        
        try:
            # Create IMU message
            imu_msg = Imu()
            
            # Header
            imu_msg.header.stamp = rospy.Time.now()
            imu_msg.header.frame_id = "base_link"
            
            # Orientation (from attitude)
            if self.attitude:
                roll = self.attitude.roll
                pitch = self.attitude.pitch  
                yaw = self.attitude.yaw
                
                # Convert to quaternion
                quat = quaternion_from_euler(roll, pitch, yaw)
                imu_msg.orientation.x = quat[0]
                imu_msg.orientation.y = quat[1]
                imu_msg.orientation.z = quat[2]
                imu_msg.orientation.w = quat[3]
                
                # Angular velocity - 从RAW_IMU获取陀螺仪数据
                # 使用ExtendedVehicle中监听的RAW_IMU陀螺仪数据
                if self._xgyro is not None and self._ygyro is not None and self._zgyro is not None:
                    # 将陀螺仪数据从毫弧度/秒转换为弧度/秒
                    imu_msg.angular_velocity.x = self._xgyro / 1000.0
                    imu_msg.angular_velocity.y = self._ygyro / 1000.0
                    imu_msg.angular_velocity.z = self._zgyro / 1000.0
                else:
                    # 如果没有陀螺仪数据，设置为0（安全默认值）
                    imu_msg.angular_velocity.x = 0.0
                    imu_msg.angular_velocity.y = 0.0
                    imu_msg.angular_velocity.z = 0.0
            
            # Linear acceleration (from raw_imu)
            raw_accel = self.raw_imu
            if raw_accel[0] is not None:
                imu_msg.linear_acceleration.x = raw_accel[0]
                imu_msg.linear_acceleration.y = raw_accel[1]
                imu_msg.linear_acceleration.z = raw_accel[2]
            
            # Publish
            self._ros_publishers['imu'].publish(imu_msg)
            
        except Exception as e:
            rospy.logwarn_throttle(5, "Error publishing IMU data: %s", e)
    
    def publish_heading_data(self):
        """
        Publish magnetic heading data to ROS topic.
        
        Published heading is in magnetic north coordinate system:
        - 0° = Magnetic North
        - 90° = Magnetic East  
        - 180° = Magnetic South
        - 270° = Magnetic West
        """
        if not self._ros_initialized:
            return
        
        try:
            if self.heading is not None:
                heading_msg = Float64()
                heading_msg.data = float(self.heading)  # 0-360 degrees, magnetic north
                self._ros_publishers['heading'].publish(heading_msg)
                
        except Exception as e:
            rospy.logwarn_throttle(5, "Error publishing heading data: %s", e)
    
    def publish_connection_status(self):
        """Publish vehicle connection status."""
        if not self._ros_initialized:
            return
        
        try:
            status_msg = Bool()
            # Check if vehicle is connected (heartbeat within 5 seconds)
            status_msg.data = (hasattr(self, 'last_heartbeat') and 
                              self.last_heartbeat is not None and 
                              self.last_heartbeat < 5.0)
            self._ros_publishers['connected'].publish(status_msg)
            
        except Exception as e:
            rospy.logwarn_throttle(10, "Error publishing connection status: %s", e)
    
    def send_body_ned_velocity(self, vx, yaw_rate):
        """
        Send velocity command in body NED frame.
        
        This implementation uses the verified parameters from circle.py reference,
        ensuring compatibility with Pixhawk autopilot.
        
        Args:
            vx (float): Forward velocity (m/s), positive = forward
            yaw_rate (float): Yaw rate (rad/s), positive = clockwise
        """
        try:
            # Use verified type_mask from circle.py reference
            verified_type_mask = 1479
            
            msg = self.message_factory.set_position_target_local_ned_encode(
                0,       # time_boot_ms (not used)
                0, 0,    # target system, target component  
                mavutil.mavlink.MAV_FRAME_BODY_NED,  # coordinate frame
                verified_type_mask,  # type_mask (verified working value)
                0, 0, 0,             # x, y, z positions (not used)
                vx, 0, 0,            # vx, vy, vz velocity in m/s
                0, 0, 0,             # x, y, z acceleration (not used)
                0, yaw_rate          # yaw, yaw_rate (rad, rad/s)
            )
            
            # Send command to vehicle
            self.send_mavlink(msg)
            
            rospy.logdebug("Sent body NED velocity: vx=%.2f m/s, yaw_rate=%.2f rad/s", 
                          vx, yaw_rate)
            
        except Exception as e:
            rospy.logerr("Failed to send body NED velocity command: %s", e)
            raise e


def create_extended_vehicle(connect_string, baud_rate=921600, wait_ready=True, timeout=60):
    """
    Create and return an ExtendedVehicle instance.
    
    This function handles the connection process and returns a properly
    initialized ExtendedVehicle with all extensions enabled.
    
    Args:
        connect_string (str): Connection string (e.g., '/dev/ttyAMA0')
        baud_rate (int): Serial baud rate
        wait_ready (bool): Wait for vehicle to be ready
        timeout (int): Connection timeout in seconds
        
    Returns:
        ExtendedVehicle: Connected and initialized extended vehicle instance
        
    Raises:
        Exception: If connection fails
    """
    try:
        rospy.loginfo("Connecting to vehicle on: %s at %d baud", connect_string, baud_rate)
        
        # Connect using standard dronekit.connect()
        vehicle = connect(
            connect_string,
            baud=baud_rate, 
            wait_ready=wait_ready,
            timeout=timeout,
            vehicle_class=ExtendedVehicle  # Use our extended class
        )
        
        rospy.loginfo("✓ Successfully connected to ExtendedVehicle")
        return vehicle
        
    except Exception as e:
        rospy.logerr("✗ Failed to create extended vehicle: %s", e)
        raise e
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
State Estimator Node - "融合估计者" (Fusion Estimator)

Refactored version that combines RTK GPS data with heading information
from the control interface node to provide complete boat state estimation.

Key Changes from Phase 1:
- Removed direct IMU handling (now handled by control_interface_node)
- Added heading data subscription from control_interface_node
- Publishes complete BoatState message combining RTK + heading
- Enhanced data synchronization and quality checking

Data Flow:
RTK GPS → rtk_node → /rtk_data → state_estimator_node
Pixhawk → control_interface_node → /boat/heading → state_estimator_node
                                                     ↓
                                             /boat_state (complete state)

Author: Multi-Boat Team  
Version: 2.0.0 (Phase 2 - Integrated State Estimation)
"""

import rospy
import threading
import time
from std_msgs.msg import Float64
from multi_boat_control.msg import RTK, BoatState


class StateEstimatorNode:
    """
    Enhanced State Estimator that fuses RTK and heading data.
    
    This node combines high-precision RTK GPS data with magnetic heading
    information to provide complete 3DOF state estimation (x, y, heading)
    for multi-boat coordination.
    """
    
    def __init__(self):
        """Initialize the state estimator node."""
        rospy.init_node('state_estimator_node', log_level=rospy.INFO)
        rospy.loginfo("=== State Estimator Node (Phase 2) Starting ===")
        
        # Configuration parameters
        self.publish_rate = rospy.get_param('~publish_rate', 10.0)  # Hz
        self.max_data_age = rospy.get_param('~max_data_age', 1.0)   # seconds
        self.require_both_sources = rospy.get_param('~require_both_sources', True)
        
        # Data quality thresholds
        self.min_gps_accuracy = rospy.get_param('~min_gps_accuracy', 2.0)  # meters
        self.heading_timeout = rospy.get_param('~heading_timeout', 2.0)    # seconds
        
        rospy.loginfo("Configuration:")
        rospy.loginfo("  Publish rate: %.1f Hz", self.publish_rate)
        rospy.loginfo("  Max data age: %.1f s", self.max_data_age)
        rospy.loginfo("  Require both sources: %s", self.require_both_sources)
        
        # Data storage with thread safety
        self.data_lock = threading.Lock()
        self.latest_rtk = None
        self.latest_heading = None
        self.rtk_timestamp = None
        self.heading_timestamp = None
        
        # ROS interfaces
        self.setup_ros_interfaces()
        
        # Publishing thread
        self.should_shutdown = False
        self.publishing_thread = threading.Thread(target=self.publishing_loop)
        self.publishing_thread.daemon = True
        self.publishing_thread.start()
        
        rospy.loginfo("=== State Estimator Node Ready ===")
    
    def setup_ros_interfaces(self):
        """Setup ROS subscribers and publishers."""
        rospy.loginfo("Setting up ROS interfaces...")
        
        # Subscribers
        self.rtk_sub = rospy.Subscriber(
            '/rtk_data', 
            RTK, 
            self.rtk_callback,
            queue_size=1
        )
        
        self.heading_sub = rospy.Subscriber(
            '/boat/heading', 
            Float64, 
            self.heading_callback,
            queue_size=1
        )
        
        # Publisher for complete boat state
        self.state_pub = rospy.Publisher(
            '/boat_state', 
            BoatState, 
            queue_size=1
        )
        
        rospy.loginfo("✓ ROS interfaces configured")
        rospy.loginfo("  Subscribing to: /rtk_data, /boat/heading")
        rospy.loginfo("  Publishing to: /boat_state")
    
    def rtk_callback(self, msg):
        """
        Handle RTK GPS data messages.
        
        Args:
            msg (RTK): RTK GPS data message
        """
        with self.data_lock:
            self.latest_rtk = msg
            self.rtk_timestamp = rospy.Time.now()
            
            rospy.logdebug("RTK data received: lat=%.6f, lon=%.6f, speed=%.2f m/s", 
                          msg.latitude, msg.longitude, msg.ground_speed_mps)
    
    def heading_callback(self, msg):
        """
        Handle heading data from control interface node.
        
        Args:
            msg (Float64): Magnetic heading in degrees (0-360, North=0)
        """
        with self.data_lock:
            self.latest_heading = msg.data
            self.heading_timestamp = rospy.Time.now()
            
            rospy.logdebug("Heading data received: %.1f° (magnetic north)", msg.data)
    
    def check_data_quality(self):
        """
        Check data quality and freshness.
        
        Returns:
            tuple: (rtk_valid, heading_valid, combined_valid)
        """
        current_time = rospy.Time.now()
        
        # Check RTK data quality
        rtk_valid = False
        if self.latest_rtk and self.rtk_timestamp:
            age = (current_time - self.rtk_timestamp).to_sec()
            rtk_valid = (age < self.max_data_age and 
                        self.latest_rtk.gps_fix_valid)
        
        # Check heading data quality  
        heading_valid = False
        if self.latest_heading is not None and self.heading_timestamp:
            age = (current_time - self.heading_timestamp).to_sec()
            heading_valid = age < self.heading_timeout
        
        # Combined validity
        if self.require_both_sources:
            combined_valid = rtk_valid and heading_valid
        else:
            combined_valid = rtk_valid or heading_valid
        
        return rtk_valid, heading_valid, combined_valid
    
    def create_boat_state_message(self):
        """
        Create a complete BoatState message from available data.
        
        Returns:
            BoatState: Complete boat state message, or None if insufficient data
        """
        with self.data_lock:
            rtk_valid, heading_valid, combined_valid = self.check_data_quality()
            
            if not combined_valid:
                return None
            
            # Create message
            state_msg = BoatState()
            state_msg.header.stamp = rospy.Time.now()
            state_msg.header.frame_id = "boat_base_link"
            
            # Fill RTK data (if available)
            if rtk_valid and self.latest_rtk:
                state_msg.latitude = self.latest_rtk.latitude
                state_msg.longitude = self.latest_rtk.longitude
                state_msg.ground_speed_mps = self.latest_rtk.ground_speed_mps
                state_msg.course_over_ground_deg = self.latest_rtk.course_over_ground_deg
                state_msg.gps_fix_valid = self.latest_rtk.gps_fix_valid
                state_msg.rtk_timestamp = self.rtk_timestamp
                state_msg.rtk_source = "RTK_GPS"
            else:
                # Invalid RTK data
                state_msg.latitude = 0.0
                state_msg.longitude = 0.0
                state_msg.ground_speed_mps = 0.0
                state_msg.course_over_ground_deg = 0.0
                state_msg.gps_fix_valid = False
                state_msg.rtk_timestamp = rospy.Time(0)
                state_msg.rtk_source = "INVALID"
            
            # Fill heading data (if available)
            if heading_valid and self.latest_heading is not None:
                # Important: Heading is in magnetic north coordinate system
                # 0° = Magnetic North, 90° = Magnetic East, etc.
                state_msg.heading_magnetic_deg = self.latest_heading
                state_msg.heading_valid = True
                state_msg.heading_timestamp = self.heading_timestamp
                state_msg.heading_source = "Pixhawk_IMU"
            else:
                # Invalid heading data
                state_msg.heading_magnetic_deg = 0.0
                state_msg.heading_valid = False
                state_msg.heading_timestamp = rospy.Time(0)
                state_msg.heading_source = "INVALID"
            
            # Coordinate system metadata
            # TODO: Add magnetic declination lookup based on GPS position
            state_msg.magnetic_declination = 0.0  # Placeholder for future implementation
            
            return state_msg
    
    def publishing_loop(self):
        """
        Main publishing loop for boat state data.
        
        Publishes complete boat state at the configured rate.
        """
        rate = rospy.Rate(self.publish_rate)
        
        # Statistics for monitoring
        publish_count = 0
        last_stats_time = time.time()
        
        while not rospy.is_shutdown() and not self.should_shutdown:
            try:
                # Create and publish state message
                state_msg = self.create_boat_state_message()
                
                if state_msg:
                    self.state_pub.publish(state_msg)
                    publish_count += 1
                    
                    rospy.logdebug("Published boat state: lat=%.6f, lon=%.6f, heading=%.1f°", 
                                  state_msg.latitude, state_msg.longitude, 
                                  state_msg.heading_magnetic_deg)
                else:
                    rospy.logdebug("Insufficient data for state publication")
                
                # Periodic statistics
                current_time = time.time()
                if current_time - last_stats_time > 10.0:  # Every 10 seconds
                    rtk_valid, heading_valid, combined_valid = self.check_data_quality()
                    rospy.loginfo("State Estimator Status: RTK=%s, Heading=%s, Combined=%s, Rate=%.1f Hz",
                                 rtk_valid, heading_valid, combined_valid, 
                                 publish_count / (current_time - last_stats_time))
                    publish_count = 0
                    last_stats_time = current_time
                
                rate.sleep()
                
            except Exception as e:
                rospy.logwarn("Error in publishing loop: %s", e)
                time.sleep(0.1)
    
    def shutdown(self):
        """Clean shutdown procedure."""
        rospy.loginfo("State Estimator Node shutting down...")
        self.should_shutdown = True
        
        # Wait for publishing thread to finish
        if self.publishing_thread.is_alive():
            self.publishing_thread.join(timeout=2.0)
        
        rospy.loginfo("✓ State Estimator Node shutdown complete")
    
    def run(self):
        """Main execution loop."""
        try:
            # Node stays alive to process callbacks
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
        node = StateEstimatorNode()
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
cmake_minimum_required(VERSION 3.0.2)
project(multi_boat_control)

find_package(catkin REQUIRED COMPONENTS
  rospy
  std_msgs
  geometry_msgs
  nav_msgs
  sensor_msgs
  message_generation
)

catkin_python_setup()

## Generate messages in the 'msg' folder
add_message_files(
  FILES
  RTK.msg
  BoatState.msg
)

## Generate added messages and services with any dependencies listed here
generate_messages(
  DEPENDENCIES
  std_msgs
  geometry_msgs
)

catkin_package(
  CATKIN_DEPENDS 
    rospy 
    std_msgs 
    geometry_msgs 
    nav_msgs 
    sensor_msgs 
    message_runtime
)

include_directories(
  ${catkin_INCLUDE_DIRS}
)

## Mark executable scripts (Python etc.) for installation
# catkin_install_python(PROGRAMS
#   scripts/rtk_node.py
#   scripts/state_estimator_node.py
#   scripts/sensor_diagnostic.py
#   scripts/control_interface_node.py
#   scripts/vehicle_extensions.py
#   DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
# )
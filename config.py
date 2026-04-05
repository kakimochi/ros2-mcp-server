"""
Configuration parameters for the ROS2 MCP Server.
"""

# Message buffering configuration
MAX_BUFFER_SIZE = 100  # Maximum messages per subscription
DEFAULT_BUFFER_SIZE = 10  # Default buffer size for new subscriptions

# Publishing configuration
PUBLISH_RATE_HZ = 10  # Rate for duration-based publishing (Hz)

# Image encoding configuration
DEFAULT_IMAGE_ENCODING = "jpeg"  # Default image encoding format
IMAGE_QUALITY = 85  # JPEG quality (0-100)

# Supported message types (pre-validated for common use)
SUPPORTED_MESSAGE_TYPES = [
    "geometry_msgs/msg/Twist",
    "geometry_msgs/msg/Point",
    "geometry_msgs/msg/Pose",
    "geometry_msgs/msg/PoseArray",
    "std_msgs/msg/String",
    "std_msgs/msg/Int32",
    "std_msgs/msg/Float64",
    "std_msgs/msg/Bool",
    "sensor_msgs/msg/Image",
    "nav_msgs/msg/Odometry",
]

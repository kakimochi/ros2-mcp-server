"""
Utility functions for converting between ROS2 messages and JSON/base64 formats.
Enables dynamic message handling for the MCP server.
"""

import importlib
import base64
import io
from typing import Any, Dict, Optional, Type
import numpy as np

try:
    from cv_bridge import CvBridge
    import cv2
    CV_BRIDGE_AVAILABLE = True
except ImportError:
    CV_BRIDGE_AVAILABLE = False

from rosidl_runtime_py import message_to_ordereddict, set_message_fields
from rosidl_runtime_py.utilities import get_message


def import_message_type(msg_type_str: str) -> Optional[Type]:
    """
    Dynamically import a ROS2 message type from its string representation.
    
    Args:
        msg_type_str: Message type in format 'package/msg/MessageType'
                     (e.g., 'geometry_msgs/msg/Twist')
    
    Returns:
        Message class if successful, None otherwise
    
    Example:
        >>> Twist = import_message_type('geometry_msgs/msg/Twist')
        >>> msg = Twist()
    """
    try:
        return get_message(msg_type_str)
    except (ModuleNotFoundError, AttributeError, ValueError) as e:
        print(f"Error importing message type '{msg_type_str}': {e}")
        return None


def ros_message_to_dict(msg: Any) -> Dict:
    """
    Convert a ROS2 message to a JSON-serializable dictionary.
    
    Args:
        msg: ROS2 message instance
    
    Returns:
        Dictionary representation of the message
    
    Example:
        >>> from geometry_msgs.msg import Twist
        >>> twist = Twist()
        >>> twist.linear.x = 1.0
        >>> ros_message_to_dict(twist)
        {'linear': {'x': 1.0, 'y': 0.0, 'z': 0.0}, ...}
    """
    return message_to_ordereddict(msg)


def dict_to_ros_message(data: Dict, msg_class: Type) -> Any:
    """
    Convert a dictionary to a ROS2 message instance.
    
    Args:
        data: Dictionary with message field values
        msg_class: ROS2 message class to instantiate
    
    Returns:
        Populated ROS2 message instance
    
    Example:
        >>> from geometry_msgs.msg import Twist
        >>> data = {'linear': {'x': 1.0}, 'angular': {'z': 0.5}}
        >>> msg = dict_to_ros_message(data, Twist)
    """
    msg = msg_class()
    set_message_fields(msg, data)
    return msg


def get_message_fields(msg_class: Type) -> Dict[str, str]:
    """
    Inspect a ROS2 message class and return its field names and types.
    Useful for providing guidance to LLMs on message structure.
    
    Args:
        msg_class: ROS2 message class
    
    Returns:
        Dictionary mapping field names to type descriptions
    
    Example:
        >>> from geometry_msgs.msg import Twist
        >>> get_message_fields(Twist)
        {'linear': 'geometry_msgs/Vector3', 'angular': 'geometry_msgs/Vector3'}
    """
    fields = {}
    msg_instance = msg_class()
    
    # Get slots (field names) and types
    if hasattr(msg_class, 'get_fields_and_field_types'):
        fields = msg_class.get_fields_and_field_types()
    
    return fields


def ros_image_to_base64(img_msg: Any, encoding: str = 'jpeg', quality: int = 85) -> str:
    """
    Convert a ROS2 sensor_msgs/Image to base64-encoded string.
    Suitable for sending to vision-capable LLMs.
    
    Args:
        img_msg: sensor_msgs/msg/Image message
        encoding: Output format ('jpeg' or 'png')
        quality: JPEG quality (0-100), ignored for PNG
    
    Returns:
        Base64-encoded image string with data URI prefix
    
    Example:
        >>> base64_img = ros_image_to_base64(image_msg)
        >>> # Can be embedded in HTML: <img src="{base64_img}" />
    """
    if not CV_BRIDGE_AVAILABLE:
        raise ImportError("cv_bridge and opencv-python are required for image conversion. "
                         "Install with: pip install opencv-python")
    
    bridge = CvBridge()
    
    try:
        # Convert ROS Image to OpenCV format
        cv_image = bridge.imgmsg_to_cv2(img_msg, desired_encoding='bgr8')
        
        # Encode to JPEG or PNG
        if encoding.lower() == 'jpeg':
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
            _, buffer = cv2.imencode('.jpg', cv_image, encode_param)
            mime_type = 'image/jpeg'
        elif encoding.lower() == 'png':
            _, buffer = cv2.imencode('.png', cv_image)
            mime_type = 'image/png'
        else:
            raise ValueError(f"Unsupported encoding: {encoding}. Use 'jpeg' or 'png'.")
        
        # Convert to base64
        base64_str = base64.b64encode(buffer).decode('utf-8')
        
        # Return with data URI prefix for direct embedding
        return f"data:{mime_type};base64,{base64_str}"
    
    except Exception as e:
        raise RuntimeError(f"Failed to convert ROS image to base64: {e}")


def base64_to_ros_image(base64_str: str, encoding: str = 'bgr8') -> Any:
    """
    Convert a base64-encoded image string to ROS2 sensor_msgs/Image.
    
    Args:
        base64_str: Base64-encoded image (with or without data URI prefix)
        encoding: ROS image encoding (default: 'bgr8')
    
    Returns:
        sensor_msgs/msg/Image message
    
    Example:
        >>> img_msg = base64_to_ros_image(base64_string)
        >>> image_pub.publish(img_msg)
    """
    if not CV_BRIDGE_AVAILABLE:
        raise ImportError("cv_bridge and opencv-python are required for image conversion.")
    
    bridge = CvBridge()
    
    try:
        # Remove data URI prefix if present
        if ',' in base64_str and base64_str.startswith('data:'):
            base64_str = base64_str.split(',', 1)[1]
        
        # Decode base64 to bytes
        img_bytes = base64.b64decode(base64_str)
        
        # Convert to numpy array
        nparr = np.frombuffer(img_bytes, np.uint8)
        
        # Decode to OpenCV image
        cv_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if cv_image is None:
            raise ValueError("Failed to decode image from base64")
        
        # Convert to ROS Image message
        ros_image = bridge.cv2_to_imgmsg(cv_image, encoding=encoding)
        
        return ros_image
    
    except Exception as e:
        raise RuntimeError(f"Failed to convert base64 to ROS image: {e}")


def format_topic_list(topic_names_and_types: list) -> str:
    """
    Format topic list for LLM consumption.
    
    Args:
        topic_names_and_types: List of tuples (topic_name, [msg_types])
    
    Returns:
        Formatted string describing available topics
    """
    if not topic_names_and_types:
        return "No topics available"
    
    output = "Available ROS2 Topics:\n"
    output += "=" * 60 + "\n"
    
    for topic_name, msg_types in sorted(topic_names_and_types):
        # Usually there's one type per topic
        msg_type_str = ", ".join(msg_types)
        output += f"- {topic_name}\n"
        output += f"  Type: {msg_type_str}\n"
    
    return output

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from fastmcp import FastMCP
import asyncio
import threading
import json
import ollama
from collections import deque
from typing import Dict, Any, Optional

# Import local utilities
from message_utils import (
    import_message_type,
    ros_message_to_dict,
    dict_to_ros_message,
    ros_image_to_base64,
    format_topic_list,
    get_message_fields
)
from config import (
    MAX_BUFFER_SIZE,
    DEFAULT_BUFFER_SIZE,
    PUBLISH_RATE_HZ,
    DEFAULT_IMAGE_ENCODING,
    IMAGE_QUALITY
)


class ROS2MCPNode(Node):
    """Dynamic ROS2 MCP Server Node with flexible topic management."""
    
    def __init__(self):
        super().__init__('ros2_mcp_server_node')
        
        # Dynamic publisher management
        self.topic_publishers: Dict[str, Any] = {}
        
        # Dynamic subscriber management
        self.topic_subscribers: Dict[str, Any] = {}
        self.message_buffers: Dict[str, deque] = {}
        self.raw_message_buffers: Dict[str, deque] = {} # New: store actual ROS messages
        self.buffer_locks: Dict[str, threading.Lock] = {}
        
        self.get_logger().info('ROS2 MCP Server node initialized')
        self.get_logger().info('Ready for dynamic topic management')
    
    # ==================== Topic Discovery ====================
    
    async def get_all_topics(self) -> str:
        """
        Get all available ROS2 topics with their types.
        
        Returns:
            Formatted string with topic information
        """
        try:
            topic_names_and_types = self.get_topic_names_and_types()
            return format_topic_list(topic_names_and_types)
        except Exception as e:
            self.get_logger().error(f"Error getting topics: {e}")
            return f"Error: {str(e)}"
    
    async def get_topic_info(self, topic: str) -> str:
        """
        Get detailed information about a specific topic.
        
        Args:
            topic: Topic name
        
        Returns:
            JSON string with topic information
        """
        try:
            topic_names_and_types = self.get_topic_names_and_types()
            
            # Find the topic
            topic_info = None
            for name, types in topic_names_and_types:
                if name == topic:
                    topic_info = {
                        "topic": name,
                        "types": types,
                        "subscribed_in_server": topic in self.topic_subscribers,
                        "has_publisher_in_server": topic in self.topic_publishers
                    }
                    break
            
            if topic_info is None:
                return json.dumps({"error": f"Topic '{topic}' not found"})
            
            # Get publisher and subscriber counts
            pub_count = self.count_publishers(topic)
            sub_count = self.count_subscribers(topic)
            
            topic_info["publisher_count"] = pub_count
            topic_info["subscriber_count"] = sub_count
            
            return json.dumps(topic_info, indent=2)
        
        except Exception as e:
            self.get_logger().error(f"Error getting topic info: {e}")
            return json.dumps({"error": str(e)})
    
    # ==================== Dynamic Publishing ====================
    
    async def publish_message(
        self, 
        topic: str, 
        message_type: str, 
        data: dict,
        duration: float = 0.0
    ) -> str:
        """
        Publish a message to any ROS2 topic.
        
        Args:
            topic: Topic name
            message_type: Message type (e.g., 'geometry_msgs/msg/Twist')
            data: Message data as dictionary
            duration: If > 0, publish repeatedly for this duration
        
        Returns:
            Status message
        """
        try:
            # Import message type
            msg_class = import_message_type(message_type)
            if msg_class is None:
                return f"Error: Could not import message type '{message_type}'"
            
            # Create publisher if it doesn't exist
            if topic not in self.topic_publishers:
                self.topic_publishers[topic] = self.create_publisher(
                    msg_class, topic, 10
                )
                self.get_logger().info(f"Created publisher for topic '{topic}'")
            
            # Create message from dictionary
            msg = dict_to_ros_message(data, msg_class)
            
            # Publish once or repeatedly
            if duration <= 0:
                # One-shot publishing
                self.topic_publishers[topic].publish(msg)
                self.get_logger().info(f"Published to '{topic}': {data}")
                return f"Successfully published to '{topic}'"
            else:
                # Duration-based publishing
                start_time = self.get_clock().now()
                count = 0
                
                while (self.get_clock().now() - start_time).nanoseconds / 1e9 < duration:
                    self.topic_publishers[topic].publish(msg)
                    count += 1
                    await asyncio.sleep(1.0 / PUBLISH_RATE_HZ)
                
                # Publish stop message if it's a Twist
                if message_type == 'geometry_msgs/msg/Twist':
                    stop_msg = msg_class()
                    self.topic_publishers[topic].publish(stop_msg)
                    self.get_logger().info(f"Published stop command to '{topic}'")
                
                self.get_logger().info(
                    f"Published {count} messages to '{topic}' over {duration}s"
                )
                return f"Successfully published to '{topic}' for {duration}s ({count} messages)"
        
        except Exception as e:
            error_msg = f"Error publishing to '{topic}': {str(e)}"
            self.get_logger().error(error_msg)
            return error_msg
    
    # ==================== Dynamic Subscription ====================
    
    async def subscribe_to_topic(
        self, 
        topic: str, 
        message_type: Optional[str] = None,
        buffer_size: int = DEFAULT_BUFFER_SIZE
    ) -> str:
        """
        Subscribe to a ROS2 topic and buffer incoming messages.
        
        Args:
            topic: Topic name
            message_type: Message type (optional, will auto-detect if None)
            buffer_size: Number of recent messages to keep
        
        Returns:
            Status message
        """
        try:
            # Check if already subscribed
            if topic in self.topic_subscribers:
                return f"Already subscribed to '{topic}'"
            
            # Auto-detect message type if not provided
            if message_type is None:
                topic_names_and_types = self.get_topic_names_and_types()
                for name, types in topic_names_and_types:
                    if name == topic:
                        message_type = types[0]
                        break
                
                if message_type is None:
                    return f"Error: Topic '{topic}' not found"
            
            # Import message type
            msg_class = import_message_type(message_type)
            if msg_class is None:
                return f"Error: Could not import message type '{message_type}'"
            
            # Create buffer
            buffer_size = min(buffer_size, MAX_BUFFER_SIZE)
            self.message_buffers[topic] = deque(maxlen=buffer_size)
            self.raw_message_buffers[topic] = deque(maxlen=buffer_size) # New
            self.buffer_locks[topic] = threading.Lock()
            
            # Create subscription with callback
            def callback(msg):
                msg_dict = ros_message_to_dict(msg)
                with self.buffer_locks[topic]:
                    self.message_buffers[topic].append(msg_dict)
                    self.raw_message_buffers[topic].append(msg) # New: store raw message
            
            self.topic_subscribers[topic] = self.create_subscription(
                msg_class,
                topic,
                callback,
                10
            )
            
            self.get_logger().info(
                f"Subscribed to '{topic}' (type: {message_type}, buffer: {buffer_size})"
            )
            return f"Successfully subscribed to '{topic}'"
        
        except Exception as e:
            error_msg = f"Error subscribing to '{topic}': {str(e)}"
            self.get_logger().error(error_msg)
            return error_msg
    
    async def unsubscribe_from_topic(self, topic: str) -> str:
        """
        Unsubscribe from a topic and clear its buffer.
        
        Args:
            topic: Topic name
        
        Returns:
            Status message
        """
        try:
            if topic not in self.topic_subscribers:
                return f"Not subscribed to '{topic}'"
            
            # Destroy subscription
            self.destroy_subscription(self.topic_subscribers[topic])
            del self.topic_subscribers[topic]
            
            # Clear buffer
            if topic in self.message_buffers:
                del self.message_buffers[topic]
            if topic in self.raw_message_buffers: # New
                del self.raw_message_buffers[topic]
            if topic in self.buffer_locks:
                del self.buffer_locks[topic]
            
            self.get_logger().info(f"Unsubscribed from '{topic}'")
            return f"Successfully unsubscribed from '{topic}'"
        
        except Exception as e:
            error_msg = f"Error unsubscribing from '{topic}': {str(e)}"
            self.get_logger().error(error_msg)
            return error_msg
    
    async def get_topic_messages(self, topic: str, count: int = 10) -> str:
        """
        Get buffered messages from a subscribed topic.
        
        Args:
            topic: Topic name
            count: Number of recent messages to retrieve
        
        Returns:
            JSON string with messages
        """
        try:
            if topic not in self.message_buffers:
                return json.dumps({
                    "error": f"Not subscribed to '{topic}'. Call subscribe_topic first."
                })
            
            with self.buffer_locks[topic]:
                messages = list(self.message_buffers[topic])
            
            # Get the most recent 'count' messages
            recent_messages = messages[-count:] if len(messages) > count else messages
            
            result = {
                "topic": topic,
                "message_count": len(recent_messages),
                "total_buffered": len(messages),
                "messages": recent_messages
            }
            
            return json.dumps(result, indent=2)
        
        except Exception as e:
            error_msg = f"Error getting messages from '{topic}': {str(e)}"
            self.get_logger().error(error_msg)
            return json.dumps({"error": error_msg})
    
    # ==================== Vision Support ====================
    
    async def get_camera_image(
        self, 
        topic: str = "/camera/image_raw",
        encoding: str = DEFAULT_IMAGE_ENCODING
    ) -> str:
        """
        Get the latest camera image from a ROS2 topic.
        
        Args:
            topic: Camera topic name
            encoding: Output format ('jpeg' or 'png')
        
        Returns:
            Base64-encoded image or error message
        """
        try:
            # Ensure we're subscribed
            if topic not in self.topic_subscribers:
                # Auto-subscribe
                result = await self.subscribe_to_topic(
                    topic, 
                    message_type="sensor_msgs/msg/Image",
                    buffer_size=1
                )
                if "Error" in result:
                    return json.dumps({"error": result})
                
                # Wait a moment for messages to arrive
                await asyncio.sleep(0.5)
            
            # Get latest message
            if topic not in self.raw_message_buffers or len(self.raw_message_buffers[topic]) == 0:
                return json.dumps({
                    "error": f"No images received yet from '{topic}'. Please wait."
                })
            
            with self.buffer_locks[topic]:
                latest_raw_msg = self.raw_message_buffers[topic][-1]
            
            # Convert ROS image to base64
            try:
                base64_img = ros_image_to_base64(latest_raw_msg, encoding=encoding, quality=IMAGE_QUALITY)
                return base64_img
            except Exception as e:
                return json.dumps({"error": f"Failed to encode image: {str(e)}"})
        
        except Exception as e:
            error_msg = f"Error getting camera image: {str(e)}"
            self.get_logger().error(error_msg)
            return json.dumps({"error": error_msg})
    
    async def describe_image(self, image_b64: str, prompt: str = "Describe this robot camera image for navigation.") -> str:
        """
        Describe an image using the Moondream vision model via Ollama.
        
        Args:
            image_b64: Base64-encoded image string
            prompt: Question or prompt for the vision model
            
        Returns:
            Model's response text
        """
        try:
            # Strip data URI prefix if present (e.g., from message_utils.ros_image_to_base64)
            if image_b64.startswith("data:image"):
                try:
                    image_b64 = image_b64.split(",", 1)[1]
                except IndexError:
                    pass

            self.get_logger().info(f"Processing image with Moondream: {prompt[:50]}...")
            response = ollama.chat(
                model="moondream:1.8b",
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [image_b64]
                }]
            )
            return response['message']['content']
        except Exception as e:
            error_msg = f"Error in vision processing: {str(e)}"
            self.get_logger().error(error_msg)
            return f"Error: {str(e)}"
    
    async def vision_query(
        self, 
        topic: str = "/camera/image_raw",
        prompt: str = "Describe this robot camera image for navigation.",
        encoding: str = DEFAULT_IMAGE_ENCODING
    ) -> str:
        """
        Combined tool to capture an image and query Moondream in one step.
        
        Args:
            topic: Camera topic name
            prompt: Question or prompt for the vision model
            encoding: Image encoding format
            
        Returns:
            Model's descriptive analysis or error
        """
        try:
            # 1. Get the latest camera image
            image_b64 = await self.get_camera_image(topic, encoding)
            
            # Check if get_camera_image returned a JSON error
            if image_b64.startswith('{"error"'):
                return image_b64
                
            # 2. Query Moondream with the captured image
            return await self.describe_image(image_b64, prompt)
            
        except Exception as e:
            error_msg = f"Error in vision query workflow: {str(e)}"
            self.get_logger().error(error_msg)
            return json.dumps({"error": error_msg})
    
    # ==================== Legacy Support ====================
    
    async def send_twist_with_duration(
        self, 
        linear: list[float], 
        angular: list[float], 
        duration: float
    ) -> str:
        """
        Legacy function for backward compatibility with move_robot tool.
        Now uses the new dynamic publishing infrastructure.
        """
        # Convert to dictionary format
        data = {
            "linear": {
                "x": float(linear[0]),
                "y": float(linear[1]) if len(linear) > 1 else 0.0,
                "z": float(linear[2]) if len(linear) > 2 else 0.0
            },
            "angular": {
                "x": float(angular[0]) if len(angular) > 0 else 0.0,
                "y": float(angular[1]) if len(angular) > 1 else 0.0,
                "z": float(angular[2]) if len(angular) > 2 else 0.0
            }
        }
        
        # Use new publish_message method
        return await self.publish_message(
            topic="/cmd_vel",
            message_type="geometry_msgs/msg/Twist",
            data=data,
            duration=duration
        )


def run_ros2_spin(node):
    """Run ROS2 node in separate thread."""
    rclpy.spin(node)


async def main():
    """Main entry point for the MCP server."""
    rclpy.init()
    ros_node = ROS2MCPNode()
    
    # Start ROS2 node in background thread
    ros_thread = threading.Thread(
        target=run_ros2_spin, 
        args=(ros_node,), 
        daemon=True
    )
    ros_thread.start()
    
    # Initialize MCP server
    mcp = FastMCP("ros2-mcp-server")
    
    # ==================== MCP Tools ====================
    
    @mcp.tool()
    async def list_topics() -> str:
        """
        List all available ROS2 topics with their message types.
        Returns formatted string with topic information.
        """
        return await ros_node.get_all_topics()
    
    @mcp.tool()
    async def get_topic_info(topic: str) -> str:
        """
        Get detailed information about a specific topic.
        
        Args:
            topic: Topic name (e.g., '/cmd_vel', '/odom')
        
        Returns:
            JSON with topic metadata
        """
        return await ros_node.get_topic_info(topic)
    
    @mcp.tool()
    async def publish_message(
        topic: str,
        message_type: str,
        data: dict,
        duration: float = 0.0
    ) -> str:
        """
        Publish a message to any ROS2 topic.
        
        Args:
            topic: Topic name (e.g., '/cmd_vel', '/chatter')
            message_type: Message type (e.g., 'geometry_msgs/msg/Twist')
            data: Message data as JSON dictionary
            duration: If > 0, publish repeatedly for this many seconds
        
        Examples:
            Publish velocity command:
            {"topic": "/cmd_vel", "message_type": "geometry_msgs/msg/Twist",
             "data": {"linear": {"x": 0.5}, "angular": {"z": 0.2}}}
            
            Publish string message:
            {"topic": "/chatter", "message_type": "std_msgs/msg/String",
             "data": {"data": "Hello from LLM"}}
        """
        return await ros_node.publish_message(topic, message_type, data, duration)
    
    @mcp.tool()
    async def subscribe_topic(topic: str, buffer_size: int = 10) -> str:
        """
        Subscribe to a ROS2 topic and buffer incoming messages.
        
        Args:
            topic: Topic name to subscribe to
            buffer_size: Number of recent messages to keep (default: 10, max: 100)
        
        Returns:
            Status message
        """
        return await ros_node.subscribe_to_topic(topic, buffer_size=buffer_size)
    
    @mcp.tool()
    async def get_messages(topic: str, count: int = 10) -> str:
        """
        Get buffered messages from a subscribed topic.
        
        Args:
            topic: Topic name
            count: Number of recent messages to retrieve (default: 10)
        
        Returns:
            JSON array of messages
        """
        return await ros_node.get_topic_messages(topic, count)
    
    @mcp.tool()
    async def unsubscribe_topic(topic: str) -> str:
        """
        Unsubscribe from a topic and clear its buffer.
        
        Args:
            topic: Topic name
        
        Returns:
            Status message
        """
        return await ros_node.unsubscribe_from_topic(topic)
    
    @mcp.tool()
    async def get_camera_image(
        topic: str = "/camera/image_raw",
        encoding: str = "jpeg"
    ) -> str:
        """
        Get the latest camera image from a ROS2 topic.
        Returns base64-encoded image for LLM vision processing.
        
        Args:
            topic: Camera topic name (default: '/camera/image_raw')
            encoding: Output format - 'jpeg' or 'png' (default: 'jpeg')
        
        Returns:
            Base64-encoded image string or error message
        
        Note: Topic must be of type sensor_msgs/msg/Image
        """
        return await ros_node.get_camera_image(topic, encoding)
    
    @mcp.tool()
    async def move_robot(
        linear: list[float], 
        angular: list[float], 
        duration: float
    ) -> str:
        """
        Send movement commands to the robot for a specified duration.
        (Legacy tool for backward compatibility)
        
        Args:
            linear: Linear velocity [x, y, z] in m/s
            angular: Angular velocity [x, y, z] in rad/s
            duration: Duration in seconds
        
        Returns:
            Status message
        """
        return await ros_node.send_twist_with_duration(linear, angular, duration)
    
    @mcp.tool()
    async def describe_image(image_b64: str, prompt: str = "Describe this robot camera image for navigation.") -> str:
        """
        Describe an image using the Moondream vision model.
        
        Args:
            image_b64: Base64-encoded image string (e.g. from get_camera_image)
            prompt: What to ask about the image (default description for navigation)
            
        Returns:
            Model's descriptive analysis
        """
        return await ros_node.describe_image(image_b64, prompt)
    
    @mcp.tool()
    async def vision_query(
        topic: str = "/camera/image_raw",
        prompt: str = "Describe this robot camera image for navigation."
    ) -> str:
        """
        Capture an image from a ROS2 topic and describe it using Moondream.
        This combined tool is more efficient than calling capture and describe separately.
        
        Args:
            topic: Camera topic name (default: '/camera/image_raw')
            prompt: What to ask about the image
            
        Returns:
            Model's descriptive analysis
        """
        return await ros_node.vision_query(topic, prompt)
    
    # Run MCP server
    await mcp.run_async()
    
    # Cleanup
    ros_node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

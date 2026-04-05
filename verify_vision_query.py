import asyncio
import os
import sys
import rclpy
from sensor_msgs.msg import Image
import numpy as np
import cv2
from cv_bridge import CvBridge

# Add the directory to path
sys.path.append(os.getcwd())

async def test_vision_query():
    # 1. Setup - Mock image
    image_path = "robot_camera.jpg"
    if not os.path.exists(image_path):
        print(f"Error: {image_path} not found.")
        return

    # Load image and convert to ROS message
    cv_img = cv2.imread(image_path)
    bridge = CvBridge()
    ros_img = bridge.cv2_to_imgmsg(cv_img, encoding="bgr8")

    # 2. Initialize Node
    import importlib.util
    spec = importlib.util.spec_from_file_location("ros2_mcp_server", "ros2-mcp-server.py")
    ros2_mcp_server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ros2_mcp_server)
    ROS2MCPNode = ros2_mcp_server.ROS2MCPNode
    
    rclpy.init()
    node = ROS2MCPNode()
    
    # Manually populate the buffer to simulate a received image
    topic = "/camera/image_raw"
    from collections import deque
    import threading
    node.raw_message_buffers[topic] = deque([ros_img], maxlen=1)
    node.buffer_locks[topic] = threading.Lock()
    node.topic_subscribers[topic] = "mock_subscriber" # Simulate subscription exists
    
    print(f"Testing vision_query logic with simulated image on {topic}...")
    
    # 3. Call vision_query
    prompt = "What objects are on the game board?"
    response = await node.vision_query(topic, prompt)
    
    print("\nVision Query Response:")
    print("-" * 20)
    print(response)
    print("-" * 20)
    
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    asyncio.run(test_vision_query())

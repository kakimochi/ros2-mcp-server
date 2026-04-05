import asyncio
import base64
import os
import sys

# Add the directory to path so we can import message_utils
sys.path.append(os.getcwd())

async def test_describe_image():
    # We'll use the existing robot_camera.jpg
    image_path = "robot_camera.jpg"
    if not os.path.exists(image_path):
        print(f"Error: {image_path} not found.")
        return

    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode('utf-8')

    # Mock the ROS2MCPNode for testing the tool logic
    # In a real scenario, the server would be running.
    # Here we just want to verify the ollama integration via the describe_image method.
    
    import importlib.util
    spec = importlib.util.spec_from_file_location("ros2_mcp_server", "ros2-mcp-server.py")
    ros2_mcp_server = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ros2_mcp_server)
    ROS2MCPNode = ros2_mcp_server.ROS2MCPNode
    import rclpy
    
    rclpy.init()
    node = ROS2MCPNode()
    
    print(f"Testing describe_image with {image_path}...")
    description = await node.describe_image(image_b64, "What do you see in this image?")
    
    print("\nDescription output:")
    print("-" * 20)
    print(description)
    print("-" * 20)
    
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    asyncio.run(test_describe_image())

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from fastmcp import FastMCP
import asyncio
import threading
import os
import time
from datetime import datetime
import rosbag2_py
from rclpy.serialization import serialize_message

class ROS2MCPNode(Node):
    def __init__(self):
        super().__init__('ros2_mcp_server_node')

        # pub / sub
        self.pub_cmd_vel = self.create_publisher(Twist, '/cmd_vel', 10)
        self.sub_odom = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10
        )
        
        self.writer = None
        self.recording = False
        self.latest_cmd_vel = Twist()
        self.latest_odom = None
        self.recording_thread = None
        self.stop_recording_flag = False
        
        self.get_logger().info('ROS2 node initialized')
    
    def odom_callback(self, msg):
        """Callback for /odom topic subscription"""
        self.latest_odom = msg
    
    async def send_twist_with_duration(self, linear: list[float], angular: list[float], duration: float) -> str:
        """指定時間だけTwistメッセージを発行し、その後停止"""
        try:
            # 速度メッセージの作成
            msg = Twist()
            msg.linear.x = float(linear[0])
            msg.linear.y = float(linear[1]) if len(linear) > 1 else 0.0
            msg.linear.z = float(linear[2]) if len(linear) > 2 else 0.0
            msg.angular.x = float(angular[0]) if len(angular) > 0 else 0.0
            msg.angular.y = float(angular[1]) if len(angular) > 1 else 0.0
            msg.angular.z = float(angular[2]) if len(angular) > 2 else 0.0
            
            self.latest_cmd_vel = msg

            # 速度メッセージの発行（10Hzで安定発行）
            start_time = self.get_clock().now()
            duration_sec = duration
            while (self.get_clock().now() - start_time).nanoseconds / 1e9 < duration_sec:
                self.pub_cmd_vel.publish(msg)
                self.get_logger().info(f'Publishing Twist: linear={msg.linear.x}, angular={msg.angular.z}')
                await asyncio.sleep(0.1)  # 10Hz

            # 停止メッセージの発行
            stop_msg = Twist()
            self.latest_cmd_vel = stop_msg
            self.pub_cmd_vel.publish(stop_msg)
            self.get_logger().info('Published stop command')
            return f"Successfully moved for {duration} seconds and stopped"
        except Exception as e:
            self.get_logger().error(f"Error publishing Twist: {str(e)}")
            return f"Error: {str(e)}"
    
    def _record_topics(self):
        """Background thread function to record topics to rosbag2"""
        try:
            writer = rosbag2_py.SequentialWriter()
            
            storage_options = rosbag2_py._storage.StorageOptions(
                uri=self.bag_path,
                storage_id='sqlite3'
            )
            
            converter_options = rosbag2_py._storage.ConverterOptions(
                input_serialization_format='cdr',
                output_serialization_format='cdr'
            )
            
            writer.open(storage_options, converter_options)
            
            cmd_vel_topic_info = rosbag2_py._storage.TopicMetadata(
                name='/cmd_vel',
                type='geometry_msgs/msg/Twist',
                serialization_format='cdr'
            )
            writer.create_topic(cmd_vel_topic_info)
            
            odom_topic_info = rosbag2_py._storage.TopicMetadata(
                name='/odom',
                type='nav_msgs/msg/Odometry',
                serialization_format='cdr'
            )
            writer.create_topic(odom_topic_info)
            
            rate = 0.1  # seconds
            
            self.get_logger().info(f'Started recording to {self.bag_path}')
            
            while not self.stop_recording_flag:
                timestamp = int(time.time_ns())
                
                if self.latest_cmd_vel is not None:
                    writer.write(
                        '/cmd_vel',
                        serialize_message(self.latest_cmd_vel),
                        timestamp
                    )
                
                if self.latest_odom is not None:
                    writer.write(
                        '/odom',
                        serialize_message(self.latest_odom),
                        timestamp
                    )
                
                time.sleep(rate)
            
            writer.reset()
            self.get_logger().info('Stopped recording')
            
        except Exception as e:
            self.get_logger().error(f'Error in recording thread: {str(e)}')
    
    async def start_recording(self) -> str:
        """Start recording /cmd_vel and /odom topics to rosbag2"""
        try:
            if self.recording:
                return "Recording is already in progress"
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.bag_path = f"/tmp/ros2_mcp_recording_{timestamp}"
            os.makedirs(self.bag_path, exist_ok=True)
            
            self.stop_recording_flag = False
            
            self.recording_thread = threading.Thread(target=self._record_topics)
            self.recording_thread.daemon = True
            self.recording_thread.start()
            
            self.recording = True
            return f"Started recording to {self.bag_path}"
            
        except Exception as e:
            self.get_logger().error(f"Error starting recording: {str(e)}")
            return f"Error starting recording: {str(e)}"
    
    async def stop_recording(self) -> str:
        """Stop recording rosbag2"""
        try:
            if not self.recording:
                return "No recording in progress"
            
            self.stop_recording_flag = True
            
            if self.recording_thread:
                self.recording_thread.join(timeout=5.0)
            
            self.recording = False
            return f"Stopped recording. Bag saved to {self.bag_path}"
            
        except Exception as e:
            self.get_logger().error(f"Error stopping recording: {str(e)}")
            return f"Error stopping recording: {str(e)}"

def run_ros2_spin(node):
    rclpy.spin(node)

async def main():
    rclpy.init()
    ros_node = ROS2MCPNode()

    ros_thread = threading.Thread(target=run_ros2_spin, args=(ros_node,), daemon=True)
    ros_thread.start()

    mcp = FastMCP("ros2-mcp-server")

    @mcp.tool()
    async def move_robot(linear: list[float], angular: list[float], duration: float) -> str:
        """Send movement commands to the robot for a specified duration"""
        return await ros_node.send_twist_with_duration(linear, angular, duration)
    
    @mcp.tool()
    async def start_recording() -> str:
        """Start recording /cmd_vel and /odom topics to rosbag2 file in /tmp"""
        return await ros_node.start_recording()
    
    @mcp.tool()
    async def stop_recording() -> str:
        """Stop recording rosbag2 file"""
        return await ros_node.stop_recording()

    # MCP サーバの実行（stdio トランスポート）
    # anyioの代わりに直接asyncioを使用
    await mcp.run_async()

    # clean up
    ros_node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    asyncio.run(main())

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from fastmcp import FastMCP
import asyncio
import threading

class ROS2MCPNode(Node):
    def __init__(self):
        super().__init__('ros2_mcp_server_node')

        # pub / sub
        self.pub_cmd_vel = self.create_publisher(Twist, '/cmd_vel', 10)
        
        self.odom_data = None
        self.sub_odom = self.create_subscription(
            Odometry,
            '/odom',
            self.odom_callback,
            10
        )

        self.get_logger().info('ROS2 node initialized')
        
    def odom_callback(self, msg):
        """オドメトリメッセージのコールバック"""
        self.odom_data = msg
        self.get_logger().debug(f'Received odometry: position=({msg.pose.pose.position.x}, {msg.pose.pose.position.y}, {msg.pose.pose.position.z})')
        
    async def get_position(self) -> dict:
        """ロボットの現在位置を取得する"""
        if self.odom_data is None:
            self.get_logger().warn('Odometry data not available')
            return {
                "position": None,
                "orientation": None,
                "error": "Odometry data not available"
            }
        
        try:
            position = {
                "x": float(self.odom_data.pose.pose.position.x),
                "y": float(self.odom_data.pose.pose.position.y),
                "z": float(self.odom_data.pose.pose.position.z)
            }
            
            orientation = {
                "x": float(self.odom_data.pose.pose.orientation.x),
                "y": float(self.odom_data.pose.pose.orientation.y),
                "z": float(self.odom_data.pose.pose.orientation.z),
                "w": float(self.odom_data.pose.pose.orientation.w)
            }
            
            return {
                "position": position,
                "orientation": orientation,
                "linear_velocity": {
                    "x": float(self.odom_data.twist.twist.linear.x),
                    "y": float(self.odom_data.twist.twist.linear.y),
                    "z": float(self.odom_data.twist.twist.linear.z)
                },
                "angular_velocity": {
                    "x": float(self.odom_data.twist.twist.angular.x),
                    "y": float(self.odom_data.twist.twist.angular.y),
                    "z": float(self.odom_data.twist.twist.angular.z)
                }
            }
        except Exception as e:
            self.get_logger().error(f"Error getting position: {str(e)}")
            return {
                "position": None,
                "orientation": None,
                "error": str(e)
            }

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

            # 速度メッセージの発行（10Hzで安定発行）
            start_time = self.get_clock().now()
            duration_sec = duration
            while (self.get_clock().now() - start_time).nanoseconds / 1e9 < duration_sec:
                self.pub_cmd_vel.publish(msg)
                self.get_logger().info(f'Publishing Twist: linear={msg.linear.x}, angular={msg.angular.z}')
                await asyncio.sleep(0.1)  # 10Hz

            # 停止メッセージの発行
            stop_msg = Twist()
            self.pub_cmd_vel.publish(stop_msg)
            self.get_logger().info('Published stop command')
            return f"Successfully moved for {duration} seconds and stopped"
        except Exception as e:
            self.get_logger().error(f"Error publishing Twist: {str(e)}")
            return f"Error: {str(e)}"

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
    async def get_position() -> dict:
        """Get the current position of the robot"""
        return await ros_node.get_position()

    # MCP サーバの実行（stdio トランスポート）
    # anyioの代わりに直接asyncioを使用
    await mcp.run_async()

    # clean up
    ros_node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    asyncio.run(main())

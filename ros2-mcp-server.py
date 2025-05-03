import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from sensor_msgs.msg import BatteryState
from fastmcp import FastMCP
import asyncio
import threading

class ROS2MCPNode(Node):
    def __init__(self):
        super().__init__('ros2_mcp_server_node')

        # pub / sub
        self.pub_cmd_vel = self.create_publisher(Twist, '/cmd_vel', 10)
        
        self.battery_state = None
        self.battery_sub = self.create_subscription(
            BatteryState,
            '/battery_state',
            self.battery_callback,
            10
        )

        self.get_logger().info('ROS2 node initialized')
        
    def battery_callback(self, msg):
        """バッテリー状態メッセージのコールバック"""
        self.battery_state = msg
        self.get_logger().debug(f'Received battery state: {msg.percentage}%')
        
    async def get_battery_level(self) -> dict:
        """バッテリー残量を取得する"""
        if self.battery_state is None:
            self.get_logger().warn('Battery state not available')
            return {
                "percentage": None,
                "error": "Battery state not available"
            }
        
        try:
            percentage = round(self.battery_state.percentage * 100.0) if self.battery_state.percentage <= 1.0 else self.battery_state.percentage
            
            return {
                "percentage": percentage,
                "voltage": self.battery_state.voltage,
                "temperature": self.battery_state.temperature,
                "current": self.battery_state.current,
                "charge": self.battery_state.charge,
                "capacity": self.battery_state.capacity,
                "design_capacity": self.battery_state.design_capacity,
                "power_supply_status": self.battery_state.power_supply_status,
                "power_supply_health": self.battery_state.power_supply_health,
                "power_supply_technology": self.battery_state.power_supply_technology
            }
        except Exception as e:
            self.get_logger().error(f"Error getting battery level: {str(e)}")
            return {
                "percentage": None,
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
    async def get_battery_level() -> dict:
        """Get the current battery level of the robot in percentage"""
        return await ros_node.get_battery_level()

    # MCP サーバの実行（stdio トランスポート）
    # anyioの代わりに直接asyncioを使用
    await mcp.run_async()

    # clean up
    ros_node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    asyncio.run(main())

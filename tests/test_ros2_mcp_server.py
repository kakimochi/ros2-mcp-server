import unittest
from unittest.mock import MagicMock, patch
import rclpy
from geometry_msgs.msg import Twist

from ros2_mcp_server import ROS2MCPNode

class TestROS2MCPNode(unittest.TestCase):
    
    def setUp(self):
        rclpy.init()
        self.node = ROS2MCPNode()
        
    def tearDown(self):
        self.node.destroy_node()
        rclpy.shutdown()
    
    @patch('rclpy.node.Node.create_publisher')
    def test_init(self, mock_create_publisher):
        node = ROS2MCPNode()
        mock_create_publisher.assert_called_with(Twist, '/cmd_vel', 10)
        node.destroy_node()

if __name__ == '__main__':
    unittest.main()

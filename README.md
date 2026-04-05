# ros2-mcp-server

A **dynamic ROS2 MCP (Model Context Protocol) server** with vision support that enables AI assistants like Claude to interact with any ROS2 topic, discover available topics, subscribe to real-time data streams, and process camera images.

## 🚀 Features

### Core Capabilities
- **Dynamic Topic Management**: Publish to and subscribe from any ROS2 topic at runtime
- **Topic Discovery**: List all available topics with their message types
- **Vision Support**: Process camera images with vision-capable LLMs (Claude Vision, GPT-4V, etc.)
- **Message Buffering**: Subscribe to topics and retrieve recent messages on-demand
- **Flexible Publishing**: One-shot or duration-based publishing to any topic
- **Backward Compatible**: Maintains support for the original `move_robot` tool

### MCP Tools (8 total)
1. `list_topics` - Discover all available ROS2 topics
2. `get_topic_info` - Get detailed information about a specific topic
3. `publish_message` - Publish to any ROS2 topic with any message type  
4. `subscribe_topic` - Subscribe to a topic and buffer messages
5. `get_messages` - Retrieve buffered messages from a subscribed topic
6. `unsubscribe_topic` - Unsubscribe and clear buffer
7. `get_camera_image` - Get base64-encoded camera images for vision LLMs
8. `move_robot` - Legacy tool for robot movement (backward compatible)

## 📋 Prerequisites

- **ROS2**: Humble distribution installed and sourced
- **Python**: Version 3.10 (required for ROS2 Humble compatibility)
- **uv**: Python package manager ([install uv](https://docs.astral.sh/uv/getting-started/installation/))
- **Dependencies**:
  - `rclpy` (installed with ROS2)
  - `cv_bridge` (installed with ROS2)
  - `fastmcp`
  - `numpy`
  - `opencv-python`

## 📦 Installation

1. **Clone the Repository**:
   ```bash
   cd ~/tools  # or your preferred directory
   git clone https://github.com/hawk200545/ros2-mcp-server.git
   cd ros2-mcp-server
   ```

2. **Create Virtual Environment**:
   ```bash
   uv venv --python /usr/bin/python3.10
   ```

3. **Activate the Virtual Environment**:
   ```bash
   source .venv/bin/activate
   ```

4. **Install Dependencies**:
   ```bash
   uv pip install -e .
   ```

## ⚙️ MCP Server Configuration

### For Claude Desktop

1. Open Claude Desktop settings → MCP servers section
2. Add the configuration:

```json
{
  "ros2-mcp-server": {
    "command": "uv",
    "args": [
      "--directory",
      "/home/YOUR_USERNAME/tools/ros2-mcp-server",
      "run",
      "bash",
      "-c",
      "export ROS_LOG_DIR=/tmp && source /opt/ros/humble/setup.bash && python3 ros2-mcp-server.py"
    ],
    "transportType": "stdio"
  }
}
```

**Important**: Replace `/home/YOUR_USERNAME/tools/ros2-mcp-server` with your actual path.

3. Restart Claude Desktop

### For Cline (VSCode Extension)

Same configuration as Claude Desktop. Add to Cline's MCP settings and toggle the server on.

## 💡 Usage Examples

### Example 1: Topic Discovery
**User**: "What ROS2 topics are available?"

**Claude calls**: `list_topics()`

**Result**: Lists all topics like `/cmd_vel`, `/odom`, `/camera/image_raw`, etc.

---

### Example 2: Publish a Setpoint (Drone Hovering)
**User**: "Make the drone hover at position (2, 3, 5)"

**Claude calls**:
```python
publish_message(
    topic="/drone/setpoint",
    message_type="geometry_msgs/msg/Point",
    data={"x": 2.0, "y": 3.0, "z": 5.0}
)
```

**Result**: Publishes the setpoint once. Your PID controller (running separately) handles the real-time control loop.

---

### Example 3: Subscribe and Monitor Position
**User**: "Subscribe to the drone's position and tell me where it is"

**Claude calls**:
```python
# First subscribe
subscribe_topic(topic="/whycon/poses", buffer_size=10)

# Then get messages after a moment
get_messages(topic="/whycon/poses", count=1)
```

**Result**: Returns the latest position data in JSON format.

---

### Example 4: Vision-Based Navigation
**User**: "Look at the camera and tell me what's ahead"

**Claude calls**:
```python
get_camera_image(topic="/camera/image_raw", encoding="jpeg")
```

**Result**: Returns base64-encoded image. Claude Vision analyzes it and reports:
> "I can see an indoor corridor with clear path ahead. There's a red marker on the left wall about 3 meters away."

---

### Example 5: Move Robot (Backward Compatible)
**User**: "Move the robot forward at 0.3 m/s for 3 seconds"

**Claude calls**:
```python
move_robot(
    linear=[0.3, 0.0, 0.0],
    angular=[0.0, 0.0, 0.0],
    duration=3.0
)
```

**Result**: Robot moves forward for 3 seconds, then stops.

---

## 🎯 LLM as High-Level Controller

### Recommended Architecture

```mermaid
graph LR
    A[LLM via MCP] -->|Setpoints| B[/drone/setpoint]
    C[/whycon/poses] -->|Position| D[pico_controller_PID.py]
    B --> D
    D -->|50+ Hz| E[/rc_command]
    E --> F[Drone]
    F -->|Feedback| C
```

**Key Principle**: The LLM publishes **setpoints** (waypoints), not real-time control commands. Your existing PID controller handles the fast closed-loop control.

#### Why This Works
- **LLM Speed**: 500-2000ms inference time ❌ Too slow for real-time control
- **PID Speed**: < 20ms loop time ✅ Perfect for real-time control
- **Solution**: LLM → Strategic decisions | PID → Tactical execution

### Example Workflow
1. **LLM**: Analyzes camera image, sees target
2. **LLM**: Calculates waypoint, publishes to `/drone/setpoint`
3. **PID Controller**: Continuously reads `/whycon/poses` and `/drone/setpoint`
4. **PID Controller**: Publishes `/rc_command` at 50 Hz to reach setpoint
5. **LLM**: Monitors progress by checking `/whycon/poses` occasionally

## 🧪 Testing

### With TurtleBot3 Gazebo Simulator

```bash
# Terminal 1: Launch simulator
export TURTLEBOT3_MODEL=burger
ros2 launch turtlebot3_gazebo turtlebot3_world.launch.py

# Terminal 2: Start MCP server (if testing manually)
source /opt/ros/humble/setup.bash
cd ~/tools/ros2-mcp-server
source .venv/bin/activate
python3 ros2-mcp-server.py

# Terminal 3: Monitor topics
ros2 topic list
ros2 topic echo /cmd_vel
```

Then use Claude to send commands!

### Test Commands for Claude

```
1. "List all available ROS2 topics"
2. "Subscribe to /odom and show me the robot's current position"
3. "Publish a velocity command to move the robot forward at 0.2 m/s for 5 seconds"
4. "What information is available on the /scan topic?"
```

## 📁 Project Structure

```
ros2-mcp-server/
├── ros2-mcp-server.py    # Main MCP server with ROS2 node
├── message_utils.py       # Message conversion utilities
├── config.py              # Configuration parameters
├── pyproject.toml         # Project dependencies
├── .python-version        # Python version specification
└── README.md              # This file
```

## 🔧 Supported Message Types

The server dynamically handles message types, with pre-validated support for:

- `geometry_msgs/msg/Twist` - Robot velocity control
- `geometry_msgs/msg/Point` - 3D coordinates (setpoints)
- `geometry_msgs/msg/Pose` - Position + orientation
- `geometry_msgs/msg/PoseArray` - Multiple poses (e.g., `/whycon/poses`)
- `std_msgs/msg/String` - Text messages
- `std_msgs/msg/Int32`, `Float64`, `Bool` - Primitive types
- `sensor_msgs/msg/Image` - Camera images (base64 encoding)
- `nav_msgs/msg/Odometry` - Robot pose and velocity

**Any ROS2 message type can be used** - just specify the full type string (e.g., `'custom_msgs/msg/MyMessage'`).

## 🐛 Troubleshooting

### ROS2 Logging Errors
If you see logging directory errors:
```bash
export ROS_LOG_DIR=/tmp
```

### Python Version Mismatch
Ensure you're using Python 3.10:
```bash
python3 --version  # Should show 3.10.x
```

### Import Errors
If message types can't be imported, ensure the package is sourced:
```bash
source /opt/ros/humble/setup.bash
```

### Vision/Image Errors
```bash
# Ensure cv_bridge is available
python3 -c "from cv_bridge import CvBridge"

# Install opencv if needed
uv pip install opencv-python
```

### MCP Connection Issues
- Check Claude/Cline logs for connection errors
- Verify the path in MCP configuration is correct
- Ensure ROS2 is sourced in the startup command
- Check that port isn't blocked by firewall

## 🗺️ Roadmap

### Phase 1: ✅ Complete
- Dynamic topic publishing/subscribing
- Topic discovery
- Vision support (base64 images)
- Message buffering

### Phase 2: Performance Optimization (Planned)
- Message compression for large data
- Selective buffering with filters
- Rate limiting for high-frequency topics

### Phase 3: Multi-Robot Support (Planned)
- Robot namespace handling
- Multiple ROS2 domain IDs

### Phase 4: Full ROS2 Ecosystem (Planned)
- Service calls
- Action clients
- Parameter management

## 📄 License

```
MIT License

Copyright (c) 2025 kakimochi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Note: This project uses [FastMCP](https://github.com/jlowin/fastmcp) (Apache License 2.0).

## 🙏 Acknowledgments

- Built with [FastMCP](https://github.com/jlowin/fastmcp) and [ROS2](https://docs.ros.org)
- Original project by [kakimochi](https://github.com/kakimochi/ros2-mcp-server)
- Enhanced with dynamic topic management and vision support

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

---

**Happy robot controlling with LLMs! 🤖🧠**

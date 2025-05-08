
export ROS_LOG_DIR=/tmp
uv run --python 3.10 bash -c "source /opt/ros/humble/setup.bash && python3 $(pwd)/ros2-mcp-server.py"

FROM osrf/ros:humble-desktop

# Set non-interactive installation mode
ENV DEBIAN_FRONTEND=noninteractive

# Update and install additional dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-vcstool \
    git \
    && rm -rf /var/lib/apt/lists/*

# Update rosdep (init is already done in the base image)
RUN rosdep update

# Set up ROS environment
RUN echo "source /opt/ros/humble/setup.bash" >> ~/.bashrc

# Create a workspace for testing
WORKDIR /ros2_ws
RUN mkdir -p /ros2_ws/src

# Install Python dependencies
RUN python3 -m pip install --upgrade pip && \
    python3 -m pip install uv fastmcp numpy flake8

# Set the entrypoint
ENTRYPOINT ["/bin/bash", "-c"]
CMD ["source /opt/ros/humble/setup.bash && bash"]

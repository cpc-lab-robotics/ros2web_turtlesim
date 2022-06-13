# ros2web_turtlesim


ROS2Web must be installed before you attempt to install ros2web_turtlesim.

### ROS2Web
https://github.com/cpc-lab-robotics/ros2web


# Install
```zsh
cd ros2_ws/src
git clone https://github.com/cpc-lab-robotics/ros2web_turtlesim
colcon build --symlink-install
. ./install/local_setup.zsh
```

# Usage

```zsh
ros2 web server
```

After starting up the server, try accessing this URL.

http://localhost:8080/ros2web/turtlesim
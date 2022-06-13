from typing import List

import importlib.resources
import yaml

from ros2web.api import WebPackage
from ros2web.api import RouteTableDef, Request
from ros2web.api import WidgetEvent
from ros2web.api import ProcessEvent
from ros2web.api.models import Param

import launch.logging
from rclpy.parameter import Parameter
from turtlesim.msg import Pose
from geometry_msgs.msg import Twist
from std_srvs.srv import Empty

with importlib.resources.path("ros2web_turtlesim", "data") as path:
    CONFIG_FILE_PATH = path.joinpath("config.yml")

routes = RouteTableDef()


class ROS2WebTurtlesim(WebPackage):

    def __init__(self) -> None:
        init_state = {
            'launch_button_label': 'START',
            'params': [],
            'disable': True,
            'node_name': 'turtlesim',
            'x': [5],
            'y': [5],
        }
        
        super().__init__(
            init_state=init_state,
            routes=routes,
        )
        self.__config = None
        self.__logger = launch.logging.get_logger('ROS2WebTurtlesim')
        
        try:
            with open(CONFIG_FILE_PATH, 'r') as yml:
                self.__config = yaml.safe_load(yml)
        except yaml.YAMLError as e:
            self.__logger.error(f'(YAML) :{e}')
        
        self.__process = None

    @routes.page
    async def page(self, request: Request):
        return self.__config['page']

    async def on_startup(self):
        self.bind('color_param', 'on_change', self.on_change_param)
        self.bind("launch_button", "on_click", self.launch_handler)
        self.bind("clear_button", "on_click", self.clear_handler)
        self.bind("reset_button", "on_click", self.rest_handler)
        self.bind("joystick", "on_move", self.joystick_handler)
        
        # Publisher
        self._publisher = self.ros_node.create_publisher(
            Twist, 'turtle1/cmd_vel', 10)
        
        # Subscription
        self._subscription = self.ros_node.create_subscription(
            Pose, 'turtle1/pose', self.subscribe_pose, 10)
        
        # Service
        self._clear_service = self.ros_node.create_client(Empty, 'clear')
        self._reset_service = self.ros_node.create_client(Empty, 'reset')
    
    async def on_shutdown(self):
        self.ros_node.destroy_publisher(self._publisher)
        self.ros_node.destroy_subscription(self._subscription)
        self.ros_node.destroy_client(self._clear_service)
        self.ros_node.destroy_client(self._reset_service)
        
    async def launch_handler(self, event: WidgetEvent):

        if self.__process is None:
            try:
                self.__process = await self.ros2.run(
                    package="turtlesim",
                    executable="turtlesim_node",
                    on_start=self.on_start,
                    on_exit=self.on_exit,
                    on_stdout=self.on_stdout,
                    on_stderr=self.on_stderr,
                )
            except Exception as e:
                self.__logger.error(e)

            if self.__process is not None:
                self.set_state(
                    {'launch_button_label': 'STOP', 'disable': False})
                await self._get_param()

        else:
            self.__process.shutdown()

    async def on_start(self, event: ProcessEvent):
        pass

    async def on_exit(self, event: ProcessEvent):
        self.set_state({'launch_button_label': 'START', 'disable': True})
        self.__process = None

    async def on_stdout(self, event: ProcessEvent):
        # text = event.text.decode()
        # self.__logger.info("on_stdout: {}".format(text))
        pass

    async def on_stderr(self, event: ProcessEvent):
        # text = event.text.decode()
        # self.__logger.info("on_stderr: {}".format(text))
        pass
    
    async def clear_handler(self, event: WidgetEvent):
        request = Empty.Request()
        while not self._clear_service.wait_for_service(timeout_sec=1.0):
            self.__logger.info('service not available, waiting again...')
        await self._clear_service.call_async(request)

    async def rest_handler(self, event: WidgetEvent):
        request = Empty.Request()
        while not self._reset_service.wait_for_service(timeout_sec=1.0):
            self.__logger.info('service not available, waiting again...')
        await self._reset_service.call_async(request)

    async def joystick_handler(self, event: WidgetEvent):
        
        value = event.value
        direction = value.get('direction')
        distance = value.get('distance')
        scale = 0.02 * abs(distance)

        angular = 0
        linear = 0
        if direction == 'FORWARD':
            linear = 1.0
        elif direction == 'RIGHT':
            angular = -1.0
        elif direction == 'LEFT':
            angular = 1.0
        elif direction == 'BACKWARD':
            linear = -1.0

        twist = Twist()
        twist.angular.z = scale * angular
        twist.linear.x = scale * linear

        try:
            self._publisher.publish(twist)
        except Exception as e:
            self.__logger.error(e)

    async def _get_param(self):
        node_name = self.state['node_name']
        param_names = ["background_b", "background_g", "background_r"]
        params = await self.ros2.param.get(node_name, param_names)
        self.set_state({'params': params})

    def subscribe_pose(self, msg: Pose):
        self.set_state({'x': [msg.x], 'y': [msg.y] })

    async def on_change_param(self, event: WidgetEvent):
        parameters = []
        param_names = []
        param: Param = event.value

        param_names.append(param.name)
        parameter = Parameter(
            param.name, Parameter.Type.INTEGER, param.value)
        parameters.append(parameter)

        node_name = self.state['node_name']
        await self.ros2.param.set(node_name, parameters)

        prev_params: List[Param] = self.state['params']
        params = [param if prev_param.id == param.id else prev_param
                  for prev_param in prev_params]
        self.set_state({'params': params})
        

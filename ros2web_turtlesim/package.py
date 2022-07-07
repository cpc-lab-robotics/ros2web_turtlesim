from typing import Dict

from ros2web.api import Plugin
from ros2web.api import RouteTableDef, Request
from ros2web.api import WidgetEvent
from ros2web.api import ProcessEvent
from ros2web.api.models import Param

import launch.logging
from turtlesim.msg import Pose
from geometry_msgs.msg import Twist
from std_srvs.srv import Empty
from rclpy.parameter import Parameter

routes = RouteTableDef()


class ROS2WebPackage(Plugin):

    def __init__(self, config: Dict) -> None:
        init_state = {
            'node_name': 'turtlesim',
            'disable': True,
            'launch_button_label': 'START',
            'params': [],
            'x': [5],
            'y': [5],
        }

        super().__init__(
            init_state=init_state,
            routes=routes,
        )
        self.__config = config
        self.__logger = launch.logging.get_logger('ros2web_turtlesim')
        self.__process = None

    @routes.page
    async def page(self, request: Request):
        return self.__config['page']

    async def on_startup(self):
        self.bind('param_config', 'on_change', self.on_change_param)
        self.bind("launch_button", "on_click", self.launch_handler)
        self.bind("service_button", "on_click", self.service_handler)
        self.bind("joystick", "on_change", self.joystick_handler)

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
        if self.__process:
            self.__process.shutdown()

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
                    # on_stdout=self.on_stdout,
                    # on_stderr=self.on_stderr,
                )
            except Exception as e:
                self.__logger.error(e)

            if self.__process is not None:
                self.set_state(
                    {'launch_button_label': 'STOP', 'disable': False})
                await self.get_param()
        else:
            self.__process.shutdown()

    async def on_start(self, event: ProcessEvent):
        pass

    async def on_exit(self, event: ProcessEvent):
        self.set_state({'launch_button_label': 'START',
                       'disable': True, 'params': []})
        self.__process = None

    async def on_stdout(self, event: ProcessEvent):
        # text = event.text.decode()
        # self.__logger.info("on_stdout: {}".format(text))
        pass

    async def on_stderr(self, event: ProcessEvent):
        # text = event.text.decode()
        # self.__logger.info("on_stderr: {}".format(text))
        pass

    async def service_handler(self, event: WidgetEvent):
        value = event.value
        index = value.get('index')
        label = value.get('label')

        if index == 0:
            request = Empty.Request()
            while not self._clear_service.wait_for_service(timeout_sec=1.0):
                self.__logger.info('service not available, waiting again...')
            await self._clear_service.call_async(request)
        elif index == 1:
            request = Empty.Request()
            while not self._reset_service.wait_for_service(timeout_sec=1.0):
                self.__logger.info('service not available, waiting again...')
            await self._reset_service.call_async(request)

    async def joystick_handler(self, event: WidgetEvent):
        value = event.value
        event_type = value.get('type')
        if event_type != 'move':
            return

        x = value.get('x')
        y = value.get('y')
        scale = 3
        twist = Twist()
        twist.linear.x = float(y)/50 * scale
        twist.angular.z = float(x)/50 * scale * -1
        try:
            self._publisher.publish(twist)
        except Exception as e:
            self.__logger.error(e)

    def subscribe_pose(self, msg: Pose):
        prev_x = self.state['x'][0]
        prev_y = self.state['y'][0]

        x = round(msg.x, 2)
        y = round(msg.y, 2)
        
        if prev_x != x or prev_y != y:
            self.set_state({'x': [x], 'y': [y]})

    async def get_param(self):
        node_name = self.state['node_name']
        param_names = ["background_b", "background_g", "background_r"]
        params = await self.ros2.param.get(node_name, param_names)
        self.set_state({'params': params})

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

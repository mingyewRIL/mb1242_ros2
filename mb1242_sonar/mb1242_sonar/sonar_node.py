#!/usr/bin/env python3
"""
ROS 2 Node for MB1242 4-Sensor Ultrasonic Array
Reads formatted array string: "[d1, d2, d3, d4]"
Publishes to a single topic: /sonar/ranges (mb1242_msgs/msg/SonarArray)
"""

import rclpy
from rclpy.node import Node
from mb1242_msgs.msg import SonarArray
import serial
import re


class MB1242ArrayNode(Node):
    def __init__(self):
        super().__init__('mb1242_array_node')

        self.declare_parameter('port', '/dev/ttyACM0')
        self.declare_parameter('baudrate', 115200)

        port = self.get_parameter('port').get_parameter_value().string_value
        baud = self.get_parameter('baudrate').get_parameter_value().integer_value

        try:
            self.ser = serial.Serial(port, baud, timeout=1.0)
            self.get_logger().info(f"Connected to STM32 on {port} @ {baud}")
        except serial.SerialException as e:
            self.get_logger().error(f"Cannot open serial port {port}: {e}")
            raise SystemExit(e)

        # Single publisher for all 4 channels
        self.publisher_ = self.create_publisher(SonarArray, '/sonar/ranges', 10)

        # 30 Hz polling timer
        self.timer = self.create_timer(0.033, self.poll_serial)

    def poll_serial(self):
        if not hasattr(self, 'ser') or not self.ser.is_open:
            return

        try:
            if self.ser.in_waiting > 0:
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                match = re.search(r'\[\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\]', line)
                if not match:
                    return

                # Convert cm readings into meters
                d_cm = [int(match.group(i)) for i in range(1, 5)]

                msg = SonarArray()
                msg.r1 = d_cm[0] / 100.0
                msg.r2 = d_cm[1] / 100.0
                msg.r3 = d_cm[2] / 100.0
                msg.r4 = d_cm[3] / 100.0

                self.publisher_.publish(msg)

        except serial.SerialException:
            try:
                self.ser.reset_input_buffer()
            except Exception:
                pass
        except Exception as e:
            self.get_logger().warn(f"Serial read error: {e}")

    def destroy_node(self):
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MB1242ArrayNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
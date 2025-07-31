"""
Provides various definitions pertaining to a Cync TCP packet and its parsed version.
"""

from enum import Enum
from functools import reduce


class ParsedMessage:
    def __init__(self, message_type, is_response: bool, device_id, data, version, command_code=None):
        self.message_type = message_type
        self.command_code = command_code
        self.is_response = is_response
        self.version = version
        self.device_id = device_id
        self.data = data


class ParsedInnerFrame:
    def __init__(self, command_type, data):
        self.command_type = command_type
        self.data = data


class MessageType(Enum):
    LOGIN = 1
    HANDSHAKE = 2
    SYNC = 4
    PIPE = 7
    PIPE_SYNC = 8
    PROBE = 10
    PING = 13
    DISCONNECT = 14


class PipeCommandCode(Enum):
    SET_POWER_STATE = 0xd0
    SET_BRIGHTNESS = 0xd2
    SET_COLOR = 0xe2
    DEVICE_STATUS = 0xdb
    COMBO_CONTROL = 0xf0
    QUERY_DEVICE_STATUS_PAGES = 0x52


class PipeDirection(Enum):
    REQUEST = 0xf8
    RESPONSE = 0xf9
    ANNOUNCE = 0xfa


def generate_zero_bytes(length: int):
    return bytearray([0 for _ in range(length)])


def generate_checksum(byte_array: bytearray) -> int:
    return reduce(lambda acc, byte: (acc + byte) % 256, byte_array)

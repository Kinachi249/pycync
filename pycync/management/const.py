from enum import Enum


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

PROTOCOL_VERSION = 3

PIPE_PACKET_REQUEST = 0xf8
PIPE_PACKET_RESPONSE = 0xf9
PIPE_PACKET_ANNOUNCE = 0xfa
"""Module responsible for building outbound Cync TCP packets."""

import threading

from . import inner_packet_builder
from .packet import MessageType, PipeDirection, generate_zero_bytes

PROTOCOL_VERSION = 3

_packet_counter = 1
_packet_counter_lock = threading.Lock()


def build_login_request_packet(authorize_string: str, user_id: int):
    version = PROTOCOL_VERSION

    version_byte = version.to_bytes(1, "big")
    user_id_bytes = user_id.to_bytes(4, "big")
    user_auth_length_bytes = len(authorize_string).to_bytes(2, "big")
    user_auth_bytes = bytes(authorize_string, "ascii")
    suffix_bytes = bytes.fromhex("00001e")

    payload = version_byte + user_id_bytes + user_auth_length_bytes + user_auth_bytes + suffix_bytes
    header = _generate_header(MessageType.LOGIN.value, False, payload)

    return header + payload


def build_state_query_request_packet(device_id: int):
    device_id_bytes = device_id.to_bytes(4, "big")
    packet_counter = _get_and_increment_packet_counter()
    packet_counter_bytes = packet_counter.to_bytes(2, "big")

    pipe_packet = inner_packet_builder.build_query_device_inner_packet(PipeDirection.REQUEST.value)

    payload = device_id_bytes + packet_counter_bytes + generate_zero_bytes(1) + pipe_packet
    header = _generate_header(MessageType.PIPE.value, False, payload)

    return header + payload


def build_power_state_request_packet(device_id: int, standalone_mesh_id: int, is_on: bool):
    device_id_bytes = device_id.to_bytes(4, "big")
    packet_counter = _get_and_increment_packet_counter()
    packet_counter_bytes = packet_counter.to_bytes(2, "big")

    pipe_packet = inner_packet_builder.build_power_state_inner_packet(PipeDirection.REQUEST.value, standalone_mesh_id,
                                                                      is_on)

    payload = device_id_bytes + packet_counter_bytes + generate_zero_bytes(1) + pipe_packet
    header = _generate_header(MessageType.PIPE.value, False, payload)

    return header + payload


def build_brightness_request_packet(device_id: int, standalone_mesh_id: int, brightness: int):
    device_id_bytes = device_id.to_bytes(4, "big")
    packet_counter = _get_and_increment_packet_counter()
    packet_counter_bytes = packet_counter.to_bytes(2, "big")

    pipe_packet = inner_packet_builder.build_brightness_inner_packet(PipeDirection.REQUEST.value, standalone_mesh_id,
                                                                     brightness)

    payload = device_id_bytes + packet_counter_bytes + generate_zero_bytes(1) + pipe_packet
    header = _generate_header(MessageType.PIPE.value, False, payload)

    return header + payload


def build_color_temp_request_packet(device_id: int, standalone_mesh_id: int, color_temp: int):
    device_id_bytes = device_id.to_bytes(4, "big")
    packet_counter = _get_and_increment_packet_counter()
    packet_counter_bytes = packet_counter.to_bytes(2, "big")

    pipe_packet = inner_packet_builder.build_color_temp_inner_packet(PipeDirection.REQUEST.value, standalone_mesh_id,
                                                                     color_temp)

    payload = device_id_bytes + packet_counter_bytes + generate_zero_bytes(1) + pipe_packet
    header = _generate_header(MessageType.PIPE.value, False, payload)

    return header + payload


def build_rgb_request_packet(device_id: int, standalone_mesh_id: int, rgb: tuple[int, int, int]):
    device_id_bytes = device_id.to_bytes(4, "big")
    packet_counter = _get_and_increment_packet_counter()
    packet_counter_bytes = packet_counter.to_bytes(2, "big")

    pipe_packet = inner_packet_builder.build_rgb_inner_packet(PipeDirection.REQUEST.value, standalone_mesh_id, rgb)

    payload = device_id_bytes + packet_counter_bytes + generate_zero_bytes(1) + pipe_packet
    header = _generate_header(MessageType.PIPE.value, False, payload)

    return header + payload


def build_probe_request_packet(device_id: int):
    device_id_bytes = device_id.to_bytes(4, "big")
    packet_counter = _get_and_increment_packet_counter()
    packet_counter_bytes = packet_counter.to_bytes(2, "big")

    payload = device_id_bytes + packet_counter_bytes + generate_zero_bytes(1) + bytearray.fromhex('02')
    header = _generate_header(MessageType.PROBE.value, False, payload)

    return header + payload


def _generate_header(message_type: int, is_response: bool, payload_bytes: bytes):
    info_byte = (message_type << 4) + PROTOCOL_VERSION
    if is_response:
        info_byte += 8  # Set bit 4 to 1 if this is a response. Bit 4 is an "is_response" flag bit.

    info_byte = info_byte.to_bytes(1, "big")
    payload_size = len(payload_bytes).to_bytes(4, "big")
    return info_byte + payload_size


def _get_and_increment_packet_counter():
    with _packet_counter_lock:
        global _packet_counter
        counter_value = _packet_counter
        _packet_counter = (_packet_counter + 1) % 65536

        return counter_value

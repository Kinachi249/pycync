import threading

from .const import MESSAGE_TYPE_LOGIN, PROTOCOL_VERSION, MESSAGE_TYPE_PIPE, PIPE_PACKET_REQUEST, \
    QUERY_DEVICE_STATUS_PAGES, MESSAGE_TYPE_PROBE
from .builder_utils import generate_zero_bytes
from .pipe_packet_builder import build_pipe_packet

_packet_counter = 1
_packet_counter_lock = threading.Lock()

def _generate_header(message_type: int, is_response: bool, payload_bytes: bytes):
    info_byte = (message_type << 4) + PROTOCOL_VERSION
    if is_response:
        info_byte += 8 # Set bit 4 to 1 if this is a response. Bit 4 is an "is_response" flag bit.

    info_byte = info_byte.to_bytes(1, "big")
    payload_size = len(payload_bytes).to_bytes(4, "big")
    return info_byte + payload_size

def build_login_request_packet(authorize_string: str, user_id: int):
    version = PROTOCOL_VERSION

    version_byte = version.to_bytes(1, "big")
    user_id_bytes = user_id.to_bytes(4, "big")
    user_auth_length_bytes = len(authorize_string).to_bytes(2, "big")
    user_auth_bytes = bytearray(authorize_string, "ascii")
    suffix_bytes = bytearray.fromhex("00001e")

    payload = version_byte + user_id_bytes + user_auth_length_bytes + user_auth_bytes + suffix_bytes
    header = _generate_header(MESSAGE_TYPE_LOGIN, False, payload)

    return header + payload

def build_state_query_request_packet(device_id: int):
    device_id_bytes = device_id.to_bytes(4, "big")
    packet_counter = _get_and_increment_packet_counter()
    packet_counter_bytes = packet_counter.to_bytes(2, "big")

    limit = bytearray.fromhex("ffff") #Update all devices
    offset = bytearray.fromhex("0000") #Start at the beginning

    packet_command_arguments = generate_zero_bytes(2) + limit + offset
    pipe_packet = build_pipe_packet(QUERY_DEVICE_STATUS_PAGES, PIPE_PACKET_REQUEST,
                                                packet_command_arguments)

    payload = device_id_bytes + packet_counter_bytes + generate_zero_bytes(1) + pipe_packet
    header = _generate_header(MESSAGE_TYPE_PIPE, False, payload)

    return header + payload

def build_probe_request_packet(device_id: int):
    device_id_bytes = device_id.to_bytes(4, "big")
    packet_counter = _get_and_increment_packet_counter()
    packet_counter_bytes = packet_counter.to_bytes(2, "big")

    payload = device_id_bytes + packet_counter_bytes + generate_zero_bytes(1) + bytearray.fromhex('02')
    header = _generate_header(MESSAGE_TYPE_PROBE, False, payload)

    return header + payload

def _get_and_increment_packet_counter():
    with _packet_counter_lock:
        global _packet_counter
        counter_value = _packet_counter
        _packet_counter = (_packet_counter + 1) % 65536

        return counter_value
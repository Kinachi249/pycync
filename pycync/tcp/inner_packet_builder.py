"""
Module responsible for building 'inner' packet frames, typically seen on PIPE and PIPE_SYNC type TCP messages.
Because not every packet includes an inner frame, and the fact that these inner packets use a different
endianness, constructing these inner frames is handled in this separate module.
"""

import threading

from .packet import PipeCommandCode, generate_checksum, generate_zero_bytes

_INNER_PACKET_DELIMITER = bytearray.fromhex("7e")

_inner_packet_counter = 257  # Starts at 0x0101
_inner_packet_counter_lock = threading.Lock()


def build_query_device_inner_packet(pipe_direction):
    sequence_bytes = _get_and_increment_sequence_bytes()
    packet_direction_bytes = pipe_direction.to_bytes(1, "little")

    limit = bytearray.fromhex("ffff")  # Update all devices
    offset = bytearray.fromhex("0000")  # Start at the beginning

    command_bytes = generate_zero_bytes(2) + limit + offset

    return _compile_final_packet(sequence_bytes, packet_direction_bytes,
                                 PipeCommandCode.QUERY_DEVICE_STATUS_PAGES.value, command_bytes)


def build_power_state_inner_packet(pipe_direction, standalone_mesh_id, is_on):
    command_code = PipeCommandCode.SET_POWER_STATE.value
    sequence_bytes = _get_and_increment_sequence_bytes()
    packet_direction_bytes = pipe_direction.to_bytes(1, "little")

    mesh_id_bytes = standalone_mesh_id.to_bytes(2, 'little')
    command_code_bytes = command_code.to_bytes(1, "little")
    extra_command_bytes = bytearray.fromhex("1102")
    is_on_bytes = is_on.to_bytes(1, "little")

    command_bytes = (generate_zero_bytes(1) +
                     mesh_id_bytes +
                     command_code_bytes +
                     extra_command_bytes +
                     is_on_bytes +
                     generate_zero_bytes(2))

    return _compile_final_packet(sequence_bytes, packet_direction_bytes, command_code, command_bytes)


def build_brightness_inner_packet(pipe_direction, standalone_mesh_id, brightness):
    command_code = PipeCommandCode.SET_BRIGHTNESS.value
    sequence_bytes = _get_and_increment_sequence_bytes()
    packet_direction_bytes = pipe_direction.to_bytes(1, "little")

    mesh_id_bytes = standalone_mesh_id.to_bytes(2, 'little')
    command_code_bytes = command_code.to_bytes(1, "little")
    extra_command_bytes = bytearray.fromhex("1102")
    brightness_bytes = brightness.to_bytes(1, "little")

    command_bytes = (generate_zero_bytes(1) +
                     mesh_id_bytes +
                     command_code_bytes +
                     extra_command_bytes +
                     brightness_bytes)

    return _compile_final_packet(sequence_bytes, packet_direction_bytes, command_code, command_bytes)


def build_color_temp_inner_packet(pipe_direction, standalone_mesh_id, color_temp):
    command_code = PipeCommandCode.SET_COLOR.value
    sequence_bytes = _get_and_increment_sequence_bytes()
    packet_direction_bytes = pipe_direction.to_bytes(1, "little")

    mesh_id_bytes = standalone_mesh_id.to_bytes(2, 'little')
    command_code_bytes = command_code.to_bytes(1, "little")
    extra_command_bytes = bytearray.fromhex("110205")
    color_temp_bytes = color_temp.to_bytes(1, "little")

    command_bytes = (generate_zero_bytes(1) +
                     mesh_id_bytes +
                     command_code_bytes +
                     extra_command_bytes +
                     color_temp_bytes)

    return _compile_final_packet(sequence_bytes, packet_direction_bytes, command_code, command_bytes)


def build_rgb_inner_packet(pipe_direction, standalone_mesh_id, rgb: tuple[int, int, int]):
    command_code = PipeCommandCode.SET_COLOR.value
    sequence_bytes = _get_and_increment_sequence_bytes()
    packet_direction_bytes = pipe_direction.to_bytes(1, "little")

    mesh_id_bytes = standalone_mesh_id.to_bytes(2, 'little')
    command_code_bytes = command_code.to_bytes(1, "little")
    extra_command_bytes = bytearray.fromhex("110204")
    rgb_bytes = bytearray(rgb)

    command_bytes = (generate_zero_bytes(1) +
                     mesh_id_bytes +
                     command_code_bytes +
                     extra_command_bytes +
                     rgb_bytes)

    return _compile_final_packet(sequence_bytes, packet_direction_bytes, command_code, command_bytes)


def _compile_final_packet(sequence_bytes, pipe_direction_bytes, pipe_command_code, command_bytes) -> bytearray:
    command_code_bytes = pipe_command_code.to_bytes(1, "little")

    if _requires_second_sequence_inserted(pipe_command_code):
        command_bytes = sequence_bytes + command_bytes

    packet_command_arguments_length = len(command_bytes).to_bytes(2, "little")

    packet_command_body = command_code_bytes + packet_command_arguments_length + command_bytes
    checksum = generate_checksum(packet_command_body).to_bytes(1, "little")

    packet_body = (sequence_bytes +
                   pipe_direction_bytes +
                   packet_command_body +
                   checksum)

    encoded_body = _encode_7e_usages(packet_body)

    return _INNER_PACKET_DELIMITER + encoded_body + _INNER_PACKET_DELIMITER


def _requires_second_sequence_inserted(pipe_command):
    return pipe_command in [
        PipeCommandCode.SET_POWER_STATE.value,
        PipeCommandCode.SET_COLOR.value,
        PipeCommandCode.SET_BRIGHTNESS.value,
        PipeCommandCode.COMBO_CONTROL.value
    ]


def _get_and_increment_sequence_bytes():
    with _inner_packet_counter_lock:
        global _inner_packet_counter
        counter_value = _inner_packet_counter
        _inner_packet_counter = _inner_packet_counter + 1 if _inner_packet_counter + 1 < 4294967295 else 257

        return counter_value.to_bytes(4, "little")


def _encode_7e_usages(frame_bytes: bytearray) -> bytearray:
    """
    When sending inner frames, the byte 0x7e is encoded as 0x7d5e if it's within the inner frame,
    so it isn't mistaken for a frame boundary marker.
    """
    return frame_bytes.replace(b"\x7e", b"\x7d\x5e")

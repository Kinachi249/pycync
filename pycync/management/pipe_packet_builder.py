import threading
from functools import reduce

from .builder_utils import generate_zero_bytes

_PIPE_PACKET_DELIMITER = bytearray.fromhex("7e")

_pipe_packet_counter = 257  # Starts at 0x0101
_pipe_packet_counter_lock = threading.Lock()

def build_pipe_packet(pipe_command, pipe_direction, command_argument_bytes):
    # For some reason, they decided to make the inner pipe packets use little endian, while the outer packets use
    # big endian. It's annoying, but it is what it is.
    pipe_packet_counter = _get_and_increment_pipe_packet_counter()
    pipe_packet_counter_bytes = pipe_packet_counter.to_bytes(2, "little")

    pipe_packet_direction = pipe_direction.to_bytes(1, "little")
    command = pipe_command.to_bytes(1, "little")

    packet_command_arguments_length = len(command_argument_bytes).to_bytes(2, "little")

    packet_command_body = command + packet_command_arguments_length + command_argument_bytes
    checksum = _generate_checksum(packet_command_body)

    return (_PIPE_PACKET_DELIMITER +
                    pipe_packet_counter_bytes +
                    generate_zero_bytes(2) +
                    pipe_packet_direction +
                    packet_command_body +
                    checksum +
                    _PIPE_PACKET_DELIMITER)

def _generate_checksum(byte_array):
    return reduce(lambda acc, byte: (acc + byte) % 256, byte_array).to_bytes(1, "little")

def _get_and_increment_pipe_packet_counter():
    # TODO Check to see if this is actually a 4 byte int instead of a short.
    with _pipe_packet_counter_lock:
        global _pipe_packet_counter
        counter_value = _pipe_packet_counter
        _pipe_packet_counter = _pipe_packet_counter + 1 if _pipe_packet_counter + 1 < 65536 else 257

        return counter_value
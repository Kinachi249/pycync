import struct
from .const import MessageType, PipeCommandCode


class ParsedMessage:
    def __init__(self, message_type, is_response, device_id, inner_frame = None):
        self.message_type = message_type
        self.is_response = is_response
        self.device_id = device_id
        self.inner_frame = inner_frame

class ParsedInnerFrame:
    def __init__(self, command_type, direction, data):
        self.command_type = command_type
        self.direction = direction
        self.data = data

def parse_packet(packet: bytearray) -> ParsedMessage:
    packet_type = (packet[0] & 0xF0) >> 4
    is_response = packet[0] & 0x08 >> 3
    packet_length = struct.unpack(">I", packet[1:5])[0]
    packet = packet[5:]

    match packet_type:
        case MessageType.PIPE.value:
            return _parse_pipe_packet(packet, packet_length, is_response)
        case _:
            raise NotImplementedError


def _parse_pipe_packet(packet: bytearray, length, is_response) -> ParsedMessage:
    if len(packet) != length:
        """Provided length is incorrect."""
        raise ValueError("Provided packet length did not match actual packet length")

    device_id = struct.unpack(">I", packet[0:4])[0]
    if length > 7 and packet[7] == 0x7e:
        inner_frame = _parse_inner_packet_frame(packet[7:])
    else:
        raise NotImplementedError

    return ParsedMessage(MessageType.PIPE.value, is_response, device_id, inner_frame)

def _parse_inner_packet_frame(frame_bytes: bytearray) -> ParsedInnerFrame:
    if frame_bytes[0] != 0x7e or frame_bytes[-1] != 0x7e:
        raise ValueError("Invalid delimiters for inner packet frame")

    frame_bytes = frame_bytes[1:-1] # Trim off delimiters
    frame_bytes = _decode_7e_usages(frame_bytes)

    frame_bytes = frame_bytes[4:] # Trim off sequence number, we don't need it

    direction = frame_bytes[0]
    command_code = frame_bytes[1]
    data_length = struct.unpack("<H", frame_bytes[2:4])[0]
    checksum = frame_bytes[-1]
    # TODO verify checksum

    match command_code:
        case PipeCommandCode.QUERY_DEVICE_STATUS_PAGES.value:
            parsed_data = _parse_device_status_pages_command(frame_bytes[4: 4 + data_length])
        case _:
            raise NotImplementedError

    return ParsedInnerFrame(command_code, direction, parsed_data)

def _parse_device_status_pages_command(data_bytes: bytearray) -> dict[int, dict]:
    updated_device_data = {}
    if len(data_bytes) < 5:
        return updated_device_data

    device_count = struct.unpack("<H", data_bytes[4:6])[0]
    trimmed_bytes = data_bytes[6:]

    for i in range(device_count):
        device_data = trimmed_bytes[0:24]

        mesh_id = str(struct.unpack("<H", device_data[0:2])[0])
        is_online = device_data[3]
        is_on = device_data[8]
        brightness = device_data[12]
        color_mode = device_data[16]
        rgb = (device_data[20], device_data[21], device_data[22])

        updated_device_data[mesh_id] = {
            "is_online": is_online,
            "is_on": is_on,
            "brightness": brightness,
            "color_mode": color_mode,
            "rgb": rgb
        }
        trimmed_bytes = trimmed_bytes[24:]

    return updated_device_data

def _decode_7e_usages(frame_bytes: bytearray) -> bytearray:
    """
    When sending inner frames, the byte 7e is encoded as 0x7d5e if it's within the data,
    so it isn't mistaken for a frame delimiter.
    We need to undo that when reading it.
    """
    return frame_bytes.replace(b"\x7d\x5e", b"\x7e")
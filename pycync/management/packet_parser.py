import struct
from .const import MessageType, PipeCommandCode
from .. import CyncDevice
from ..mappings.capabilities import DEVICE_CAPABILITIES, CyncCapability


class ParsedMessage:
    def __init__(self, message_type, is_response, device_id, data, version, command_code = None):
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

class PacketParser:
    def __init__(self, device_list: list[CyncDevice]):
        self._device_list = device_list

    def parse_packet(self, packet: bytearray) -> ParsedMessage:
        packet_type = (packet[0] & 0xF0) >> 4
        is_response = packet[0] & 0x08 >> 3
        version = packet[0] & 0x7
        packet_length = struct.unpack(">I", packet[1:5])[0]
        packet = packet[5:]

        match packet_type:
            case MessageType.PROBE.value:
                return self._parse_probe_packet(packet, packet_length, is_response, version)
            case MessageType.SYNC.value:
                return self._parse_sync_packet(packet, packet_length, is_response, version)
            case MessageType.PIPE.value:
                return self._parse_pipe_packet(packet, packet_length, is_response, version)
            case _:
                raise NotImplementedError

    def _parse_probe_packet(self, packet: bytearray, length, is_response, version) -> ParsedMessage:
        if len(packet) != length:
            """Provided length is incorrect."""
            raise ValueError("Provided packet length did not match actual packet length")

        device_id = struct.unpack(">I", packet[0:4])[0]
        data = packet[4:]

        return ParsedMessage(MessageType.PROBE.value, is_response, device_id, data, version)

    def _parse_sync_packet(self, packet: bytearray, length, is_response, version) -> ParsedMessage:
        if len(packet) != length:
            """Provided length is incorrect."""
            raise ValueError("Provided packet length did not match actual packet length")

        device_id = struct.unpack(">I", packet[0:4])[0]
        device_type = next(device.device_type for device in self._device_list if device.device_id == device_id)
        is_mesh_device = CyncCapability.SIG_MESH in DEVICE_CAPABILITIES[device_type]

        updated_device_data = {}

        if packet[4:7].hex() == '010106' and is_mesh_device:
            packet = packet[7:]
            while len(packet) > 3:
                info_length = struct.unpack(">H", packet[1:3])[0]
                packet = packet[3:info_length + 3]
                mesh_id = packet[0]
                resolved_device_id = next(device.device_id for device in self._device_list if device.isolated_mesh_id == mesh_id)

                updated_device_data[resolved_device_id] = {
                    "is_on": packet[1],
                    "brightness": packet[2],
                    "color_mode": packet[3],
                    "rgb": (packet[4], packet[5], packet[6])
                }
                packet = packet[info_length + 1:]

            return ParsedMessage(MessageType.SYNC.value, is_response, device_id, updated_device_data, version)

        else:
            raise NotImplementedError

    def _parse_pipe_packet(self, packet: bytearray, length, is_response, version) -> ParsedMessage:
        if len(packet) != length:
            """Provided length is incorrect."""
            raise ValueError("Provided packet length did not match actual packet length")

        device_id = struct.unpack(">I", packet[0:4])[0]
        if length > 7 and packet[7] == 0x7e:
            inner_frame = self._parse_inner_packet_frame(packet[7:])
        else:
            raise NotImplementedError

        return ParsedMessage(MessageType.PIPE.value, is_response, device_id, inner_frame.data, version, inner_frame.command_type)

    def _parse_inner_packet_frame(self, frame_bytes: bytearray) -> ParsedInnerFrame:
        if frame_bytes[0] != 0x7e or frame_bytes[-1] != 0x7e:
            raise ValueError("Invalid delimiters for inner packet frame")

        frame_bytes = frame_bytes[1:-1] # Trim off delimiters
        frame_bytes = _decode_7e_usages(frame_bytes)

        frame_bytes = frame_bytes[4:] # Trim off sequence number, we don't need it

        command_code = frame_bytes[1]
        data_length = struct.unpack("<H", frame_bytes[2:4])[0]
        checksum = frame_bytes[-1]
        # TODO verify checksum

        match command_code:
            case PipeCommandCode.QUERY_DEVICE_STATUS_PAGES.value:
                parsed_data = self._parse_device_status_pages_command(frame_bytes[4: 4 + data_length])
            case _:
                raise NotImplementedError

        return ParsedInnerFrame(command_code, parsed_data)

    def _parse_device_status_pages_command(self, data_bytes: bytearray) -> dict[int, dict]:
        updated_device_data = {}
        if len(data_bytes) < 5:
            return updated_device_data

        device_count = struct.unpack("<H", data_bytes[4:6])[0]
        trimmed_bytes = data_bytes[6:]

        for i in range(device_count):
            device_data = trimmed_bytes[0:24]

            mesh_id = struct.unpack("<H", device_data[0:2])[0]
            is_online = device_data[3]
            is_on = device_data[8]
            brightness = device_data[12]
            color_mode = device_data[16]
            rgb = (device_data[20], device_data[21], device_data[22])

            device_id = next(device.device_id for device in self._device_list if device.isolated_mesh_id == mesh_id)

            updated_device_data[device_id] = {
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
    so it isn't mistaken for a frame boundary marker.
    We need to undo that when reading it.
    """
    return frame_bytes.replace(b"\x7d\x5e", b"\x7e")
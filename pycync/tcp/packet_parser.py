"""Module responsible for parsing raw TCP packets received from the Cync server into a more usable format."""

from __future__ import annotations
from typing import TYPE_CHECKING

import struct

from ..devices import device_storage
from ..devices.device_types import DeviceType
from .packet import ParsedMessage, ParsedInnerFrame, MessageType, PipeCommandCode, generate_checksum
from pycync.devices.capabilities import DEVICE_CAPABILITIES, CyncCapability

if TYPE_CHECKING:
    from pycync.devices import CyncDevice


def parse_packet(packet: bytearray, user_id: int) -> ParsedMessage:
    packet_type = (packet[0] & 0xF0) >> 4
    is_response = bool((packet[0] & 0x08) >> 3)
    version = packet[0] & 0x7
    packet_length = struct.unpack(">I", packet[1:5])[0]
    packet = packet[5:]

    if len(packet) != packet_length:
        raise ValueError(
            "Provided packet length did not match actual packet length. Expected: {}, got: {}".format(packet_length,
                                                                                                      len(packet)))

    match packet_type:
        case MessageType.LOGIN.value:
            return ParsedMessage(MessageType.LOGIN.value, is_response, None, None, version)
        case MessageType.PROBE.value:
            return _parse_probe_packet(packet, is_response, version)
        case MessageType.SYNC.value:
            return _parse_sync_packet(packet, is_response, version, user_id)
        case MessageType.PIPE.value:
            return _parse_pipe_packet(packet, packet_length, is_response, version, user_id)
        case MessageType.DISCONNECT.value:
            return ParsedMessage(MessageType.DISCONNECT.value, is_response, user_id, packet[0], version)
        case _:
            raise NotImplementedError


def _parse_probe_packet(packet: bytearray, is_response, version) -> ParsedMessage:
    device_id = struct.unpack(">I", packet[0:4])[0]
    data = packet[4:]

    return ParsedMessage(MessageType.PROBE.value, is_response, device_id, data, version)


def _parse_sync_packet(packet: bytearray, is_response, version, user_id) -> ParsedMessage:
    device_id = struct.unpack(">I", packet[0:4])[0]
    device_list = device_storage.get_associated_home_devices(user_id, device_id)
    device_type = next(device.device_type_id for device in device_list if device.device_id == device_id)
    is_mesh_device = CyncCapability.SIG_MESH in DEVICE_CAPABILITIES[device_type]

    updated_device_data = {}

    if packet[4:7].hex() == '010106' and is_mesh_device:
        packet = packet[7:]
        while len(packet) > 3:
            info_length = struct.unpack(">H", packet[1:3])[0]
            packet = packet[3:info_length + 3]
            mesh_id = packet[0]
            try:
                resolved_device: CyncDevice = next(device for device in device_list if device.isolated_mesh_id == mesh_id)
                if DeviceType.is_light(resolved_device.device_type_id):
                    resolved_device.update_state(bool(packet[1]), packet[2], packet[3], (packet[4], packet[5], packet[6]))
            except StopIteration as ex:
                raise ValueError("Unable to resolve device ID for mesh ID: {}".format(mesh_id)) from ex

            updated_device_data[resolved_device.device_id] = resolved_device
            packet = packet[info_length + 1:]

        return ParsedMessage(MessageType.SYNC.value, is_response, device_id, updated_device_data, version)

    else:
        raise NotImplementedError


def _parse_pipe_packet(packet: bytearray, length, is_response, version, user_id) -> ParsedMessage:
    device_id = struct.unpack(">I", packet[0:4])[0]
    device_list = device_storage.get_associated_home_devices(user_id, device_id)

    if length > 7 and packet[7] == 0x7e:
        inner_frame = _parse_inner_packet_frame(packet[7:], device_list)
    else:
        raise NotImplementedError

    return ParsedMessage(MessageType.PIPE.value, is_response, device_id, inner_frame.data, version,
                         inner_frame.command_type)


def _parse_inner_packet_frame(frame_bytes: bytearray, device_list) -> ParsedInnerFrame:
    if frame_bytes[0] != 0x7e or frame_bytes[-1] != 0x7e:
        raise ValueError("Invalid delimiters for inner packet frame")

    frame_bytes = frame_bytes[1:-1]  # Trim off delimiters
    frame_bytes = _decode_7e_usages(frame_bytes)

    frame_bytes = frame_bytes[4:]  # Trim off sequence number, we don't need it

    command_code = frame_bytes[1]
    data_length = struct.unpack("<H", frame_bytes[2:4])[0]

    frame_checksum = frame_bytes[-1]
    if not _does_checksum_match(frame_bytes[1:-1], frame_checksum):
        raise ValueError("Invalid checksum for inner packet frame")

    match command_code:
        case PipeCommandCode.QUERY_DEVICE_STATUS_PAGES.value:
            parsed_data = _parse_device_status_pages_command(frame_bytes[4: 4 + data_length], device_list)
        case _:
            raise NotImplementedError

    return ParsedInnerFrame(command_code, parsed_data)


def _parse_device_status_pages_command(data_bytes: bytearray, device_list) -> dict[int, CyncDevice]:
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

        try:
            resolved_device: CyncDevice = next(device for device in device_list if device.isolated_mesh_id == mesh_id)
            if DeviceType.is_light(resolved_device.device_type_id):
                resolved_device.update_state(bool(is_on), brightness, color_mode, rgb, bool(is_online))
        except StopIteration as ex:
            raise ValueError("Unable to resolve device ID for mesh ID: {}".format(mesh_id)) from ex

        updated_device_data[resolved_device.device_id] = resolved_device
        trimmed_bytes = trimmed_bytes[24:]

    return updated_device_data


def _decode_7e_usages(frame_bytes: bytearray) -> bytearray:
    """
    When sending inner frames, the byte 0x7e is encoded as 0x7d5e if it's within the inner frame,
    so it isn't mistaken for a frame boundary marker.
    We need to undo that when reading it.
    """
    return frame_bytes.replace(b"\x7d\x5e", b"\x7e")


def _does_checksum_match(data_bytes: bytearray, expected_checksum: int) -> bool:
    checksum_result = generate_checksum(data_bytes)
    return checksum_result == expected_checksum

import pytest

from pycync.devices import CyncDevice
from pycync.management import packet_parser
from pycync.management.tcp_constants import MessageType, PipeCommandCode

TEST_USER_ID = 123456
TEST_HOME_ID = 5432

def test_login_packet():
    login_response = bytearray.fromhex("18000000020000")
    parsed_message = packet_parser.parse_packet(login_response, TEST_USER_ID)

    assert parsed_message.message_type == MessageType.LOGIN.value
    assert parsed_message.version == 0
    assert parsed_message.device_id is None
    assert parsed_message.is_response is True
    assert parsed_message.command_code is None
    assert parsed_message.data is None

def test_probe_packet():
    probe_response = bytearray.fromhex("ab00000149499602D273656E736F7273446174613A5B7B2254797065223A224E6F6E65222C2254656D7065726174757265223A6E756C6C2C2248756D6964697479223A6E756C6C2C22416374697665223A66616C73652C2242617474223A6E756C6C7D2C7B2254797065223A224E6F6E65222C2254656D7065726174757265223A6E756C6C2C2248756D6964697479223A6E756C6C2C22416374697665223A66616C73652C2242617474223A6E756C6C7D2C7B2254797065223A224E6F6E65222C2254656D7065726174757265223A6E756C6C2C2248756D6964697479223A6E756C6C2C22416374697665223A66616C73652C2242617474223A6E756C6C7D2C7B2254797065223A224E6F6E65222C2254656D7065726174757265223A6E756C6C2C2248756D6964697479223A6E756C6C2C22416374697665223A66616C73652C2242617474223A6E756C6C7D5D")
    parsed_message = packet_parser.parse_packet(probe_response, TEST_USER_ID)

    expected_data = bytearray.fromhex("73656E736F7273446174613A5B7B2254797065223A224E6F6E65222C2254656D7065726174757265223A6E756C6C2C2248756D6964697479223A6E756C6C2C22416374697665223A66616C73652C2242617474223A6E756C6C7D2C7B2254797065223A224E6F6E65222C2254656D7065726174757265223A6E756C6C2C2248756D6964697479223A6E756C6C2C22416374697665223A66616C73652C2242617474223A6E756C6C7D2C7B2254797065223A224E6F6E65222C2254656D7065726174757265223A6E756C6C2C2248756D6964697479223A6E756C6C2C22416374697665223A66616C73652C2242617474223A6E756C6C7D2C7B2254797065223A224E6F6E65222C2254656D7065726174757265223A6E756C6C2C2248756D6964697479223A6E756C6C2C22416374697665223A66616C73652C2242617474223A6E756C6C7D5D")

    assert parsed_message.message_type == MessageType.PROBE.value
    assert parsed_message.version == 3
    assert parsed_message.device_id == 1234567890
    assert parsed_message.is_response is True
    assert parsed_message.command_code is None
    assert parsed_message.data == expected_data

def test_pipe_packet(mocker):
    mocked_devices = [
        CyncDevice({"id": 1234}, {"deviceID": 4}, TEST_HOME_ID, None, True),
        CyncDevice({"id": 2345}, {"deviceID": 7}, TEST_HOME_ID, None, True),
        CyncDevice({"id": 3456}, {"deviceID": 2}, TEST_HOME_ID, None, True),
        CyncDevice({"id": 4567}, {"deviceID": 232}, TEST_HOME_ID, None, True),
        CyncDevice({"id": 5678}, {"deviceID": 30}, TEST_HOME_ID, None, True)
    ]
    mocker.patch("pycync.management.device_storage.get_associated_home_devices", return_value=mocked_devices)

    pipe_response = bytearray.fromhex("730000009100000d8002e5007e01010000f9527d5e000500000005000400890100008901010000005000000039000000d796ff0007000001000000010000000000000000fe000000f8383000020000010000000101000000410000001e00000000000000e800000100000001010000005000000039000000000000001e0000010000000101000000500000003900000000000000d17e")
    parsed_message = packet_parser.parse_packet(pipe_response, TEST_USER_ID)

    expected_device_data = {
        1234: {
            'brightness': 80,
            'color_mode': 57,
            'is_on': 1,
            'is_online': 1,
            'rgb': (215, 150, 255)
        },
        2345: {
            'brightness': 0,
            'color_mode': 254,
            'is_on': 0,
            'is_online': 1,
            'rgb': (248, 56, 48)
        },
        3456: {
            'brightness': 65,
            'color_mode': 30,
            'is_on': 1,
            'is_online': 1,
            'rgb': (0, 0, 0)
        },
        4567: {
            'brightness': 80,
            'color_mode': 57,
            'is_on': 1,
            'is_online': 1,
            'rgb': (0, 0, 0)
        },
        5678: {
            'brightness': 80,
            'color_mode': 57,
            'is_on': 1,
            'is_online': 1,
            'rgb': (0, 0, 0)
        }
    }

    assert parsed_message.message_type == MessageType.PIPE.value
    assert parsed_message.version == 3
    assert parsed_message.device_id == 3456
    assert parsed_message.is_response is False
    assert parsed_message.command_code is PipeCommandCode.QUERY_DEVICE_STATUS_PAGES.value
    assert parsed_message.data == expected_device_data

def test_thermostat_sync_packet(mocker):
    mocked_devices = [
        CyncDevice({"id": 3456}, {"deviceID": 2, "deviceType": 224}, TEST_HOME_ID, None, True)
    ]
    mocker.patch("pycync.management.device_storage.get_associated_home_devices", return_value=mocked_devices)

    pipe_response = bytearray.fromhex("430000026700000d8001010657925d73656e736f7273446174613a5b7b2254797065223a22696e7465726e616c222c2254656d7065726174757265223a2237352e3946222c2248756d6964697479223a35302c22416374697665223a747275657d2c7b2254797065223a22736176616e742073656e736f72222c2250696e436f6465223a353332342c2254656d7065726174757265223a2237352e3746222c2248756d6964697479223a34382c22416374697665223a66616c73652c2242617474223a22322e3837227d2c7b2254797065223a22736176616e742073656e736f72222c2250696e436f6465223a353134302c2254656d7065726174757265223a2237352e3246222c2248756d6964697479223a35302c22416374697665223a66616c73652c2242617474223a22322e3930227d2c7b2254797065223a224e6f6e65222c2254656d7065726174757265223a6e756c6c2c2248756d6964697479223a6e756c6c2c22416374697665223a66616c73652c2242617474223a6e756c6c7d2c7b2254797065223a224e6f6e65222c2254656d7065726174757265223a6e756c6c2c2248756d6964697479223a6e756c6c2c22416374697665223a66616c73652c2242617474223a6e756c6c7d2c7b2254797065223a224e6f6e65222c2254656d7065726174757265223a6e756c6c2c2248756d6964697479223a6e756c6c2c22416374697665223a66616c73652c2242617474223a6e756c6c7d2c7b2254797065223a224e6f6e65222c2254656d7065726174757265223a6e756c6c2c2248756d6964697479223a6e756c6c2c22416374697665223a66616c73652c2242617474223a6e756c6c7d5d")

    with pytest.raises(NotImplementedError):
        packet_parser.parse_packet(pipe_response, TEST_USER_ID)

def test_light_sync_packet(mocker):
    mocked_devices = [
        CyncDevice({"id": 2345}, {"deviceID": 7, "deviceType": 137}, TEST_HOME_ID, None, True)
    ]
    mocker.patch("pycync.management.device_storage.get_associated_home_devices", return_value=mocked_devices)

    pipe_response = bytearray.fromhex("430000001a0000092901010606001007014cfef8383001141e000000000000")
    parsed_message = packet_parser.parse_packet(pipe_response, TEST_USER_ID)

    expected_device_data = {
        2345: {
            'brightness': 76,
            'color_mode': 254,
            'is_on': 1,
            'rgb': (248, 56, 48)
        }
    }

    assert parsed_message.message_type == MessageType.SYNC.value
    assert parsed_message.version == 3
    assert parsed_message.device_id == 2345
    assert parsed_message.is_response is False
    assert parsed_message.command_code is None
    assert parsed_message.data == expected_device_data

def test_bad_checksum():
    pipe_response = bytearray.fromhex("730000009100000d8002e5007e01010000f9527d5e000500000005000400890100008901010000005000000039000000d796ff0007000001000000010000000000000000fe000000f8383000020000010000000101000000410000001e00000000000000e800000100000001010000005000000039000000000000001e0000010000000101000000500000003900000000000000127e")

    with pytest.raises(ValueError, match='Invalid checksum for inner packet frame'):
        packet_parser.parse_packet(pipe_response, TEST_USER_ID)

def test_incorrect_length():
    pipe_response = bytearray.fromhex("430000001c0000092901010606001007014cfef8383001141e000000000000")
    with pytest.raises(ValueError, match='Provided packet length did not match actual packet length. Expected: 28, got: 26'):
        packet_parser.parse_packet(pipe_response, TEST_USER_ID)
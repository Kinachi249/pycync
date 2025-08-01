from pycync.tcp import packet_builder
from tests import TEST_USER_ID

TEST_DEVICE_ID = 23456
TEST_DEVICE_MESH_ID = 5

def test_build_login_packet(mocker):
    mocker.patch("pycync.tcp.packet_builder._get_and_increment_packet_counter", return_value=1)

    test_auth_string = "123456789abcdef"
    auth_string_bytes = bytearray(test_auth_string, "ascii").hex()

    login_packet = packet_builder.build_login_request_packet(test_auth_string, TEST_USER_ID)

    assert login_packet == bytearray.fromhex("1300000019030001e240000f" + auth_string_bytes + "00001e")

def test_build_state_query_packet(mocker):
    mocker.patch("pycync.tcp.packet_builder._get_and_increment_packet_counter", return_value=1)
    mocker.patch("pycync.tcp.inner_packet_builder._get_and_increment_sequence_bytes", return_value=int(257).to_bytes(4, "little"))

    state_query_packet = packet_builder.build_state_query_request_packet(TEST_DEVICE_ID)

    assert state_query_packet == bytearray.fromhex("730000001800005ba00001007e01010000f85206000000ffff0000567e")

def test_build_power_state_request_packet(mocker):
    mocker.patch("pycync.tcp.packet_builder._get_and_increment_packet_counter", return_value=1)
    mocker.patch("pycync.tcp.inner_packet_builder._get_and_increment_sequence_bytes", return_value=int(257).to_bytes(4, "little"))

    power_state_request_packet = packet_builder.build_power_state_request_packet(TEST_DEVICE_ID, TEST_DEVICE_MESH_ID, True)

    assert power_state_request_packet == bytearray.fromhex("730000001f00005ba00001007e01010000f8d00d0001010000000500d01102010000c87e")

def test_build_brightness_request_packet(mocker):
    mocker.patch("pycync.tcp.packet_builder._get_and_increment_packet_counter", return_value=1)
    mocker.patch("pycync.tcp.inner_packet_builder._get_and_increment_sequence_bytes", return_value=int(257).to_bytes(4, "little"))

    brightness_request_packet = packet_builder.build_brightness_request_packet(TEST_DEVICE_ID, TEST_DEVICE_MESH_ID, 42)

    assert brightness_request_packet == bytearray.fromhex("730000001d00005ba00001007e01010000f8d20b0001010000000500d211022af37e")

def test_build_color_temp_request_packet(mocker):
    mocker.patch("pycync.tcp.packet_builder._get_and_increment_packet_counter", return_value=1)
    mocker.patch("pycync.tcp.inner_packet_builder._get_and_increment_sequence_bytes", return_value=int(257).to_bytes(4, "little"))

    color_temp_request_packet = packet_builder.build_color_temp_request_packet(TEST_DEVICE_ID, TEST_DEVICE_MESH_ID, 56)

    assert color_temp_request_packet == bytearray.fromhex("730000001e00005ba00001007e01010000f8e20c0001010000000500e211020538277e")

def test_build_rgb_request_packet(mocker):
    mocker.patch("pycync.tcp.packet_builder._get_and_increment_packet_counter", return_value=1)
    mocker.patch("pycync.tcp.inner_packet_builder._get_and_increment_sequence_bytes", return_value=int(257).to_bytes(4, "little"))

    rgb_request_packet = packet_builder.build_rgb_request_packet(TEST_DEVICE_ID, TEST_DEVICE_MESH_ID, (190, 239, 237))

    assert rgb_request_packet == bytearray.fromhex("730000002000005ba00001007e01010000f8e20e0001010000000500e2110204beefed8a7e")

def test_serialized_7e_packet(mocker):
    mocker.patch("pycync.tcp.packet_builder._get_and_increment_packet_counter", return_value=1)
    mocker.patch("pycync.tcp.inner_packet_builder._get_and_increment_sequence_bytes", return_value=int(257).to_bytes(4, "little"))

    power_state_request_packet = packet_builder.build_power_state_request_packet(TEST_DEVICE_ID, 0x7e, True)

    assert power_state_request_packet == bytearray.fromhex("730000002000005ba00001007e01010000f8d00d0001010000007d5e00d01102010000417e")

def test_sequence_generation():
    power_state_request_packet_1 = packet_builder.build_power_state_request_packet(TEST_DEVICE_ID, TEST_DEVICE_MESH_ID, True)
    power_state_request_packet_2 = packet_builder.build_power_state_request_packet(TEST_DEVICE_ID, TEST_DEVICE_MESH_ID, True)
    power_state_request_packet_3 = packet_builder.build_power_state_request_packet(TEST_DEVICE_ID, TEST_DEVICE_MESH_ID, True)
    power_state_request_packet_4 = packet_builder.build_power_state_request_packet(TEST_DEVICE_ID, TEST_DEVICE_MESH_ID, True)
    power_state_request_packet_5 = packet_builder.build_power_state_request_packet(TEST_DEVICE_ID, TEST_DEVICE_MESH_ID, True)

    assert power_state_request_packet_1 == bytearray.fromhex("730000001f00005ba00001007e01010000f8d00d0001010000000500d01102010000c87e")
    assert power_state_request_packet_2 == bytearray.fromhex("730000001f00005ba00002007e02010000f8d00d0002010000000500d01102010000c97e")
    assert power_state_request_packet_3 == bytearray.fromhex("730000001f00005ba00003007e03010000f8d00d0003010000000500d01102010000ca7e")
    assert power_state_request_packet_4 == bytearray.fromhex("730000001f00005ba00004007e04010000f8d00d0004010000000500d01102010000cb7e")
    assert power_state_request_packet_5 == bytearray.fromhex("730000001f00005ba00005007e05010000f8d00d0005010000000500d01102010000cc7e")
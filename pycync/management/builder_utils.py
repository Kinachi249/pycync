from functools import reduce


def generate_zero_bytes(length: int):
    return bytearray([0 for _ in range(length)])

def generate_checksum(byte_array: bytearray) -> int:
    return reduce(lambda acc, byte: (acc + byte) % 256, byte_array)
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from pycync.devices.capabilities import CyncCapability
from pycync.devices.groups import CyncGroup, CyncRoom

DIMMABLE = SimpleNamespace(capabilities=frozenset({CyncCapability.ON_OFF, CyncCapability.DIMMING}))
ON_OFF_ONLY = SimpleNamespace(capabilities=frozenset({CyncCapability.ON_OFF}))


def test_group_capabilities_are_shared_by_all_devices():
    group = CyncGroup("Lamps", 32769, 1, [DIMMABLE, ON_OFF_ONLY])
    assert group.capabilities == frozenset({CyncCapability.ON_OFF})
    assert group.supports_capability(CyncCapability.ON_OFF)
    assert not group.supports_capability(CyncCapability.DIMMING)


def test_empty_group_has_no_capabilities():
    assert CyncGroup("Empty", 32775, 1, []).capabilities == frozenset()


def test_room_capabilities_include_devices_and_non_empty_groups():
    group = CyncGroup("Kitchen Lights", 32777, 1, [DIMMABLE, DIMMABLE])
    room = CyncRoom("Kitchen", 32776, 1, [group, CyncGroup("Empty", 32775, 1, [])], [DIMMABLE])
    assert room.capabilities == DIMMABLE.capabilities
    assert room.supports_capability(CyncCapability.DIMMING)


def test_room_with_only_a_group():
    room = CyncRoom("Office", 32772, 1, [CyncGroup("Office", 32773, 1, [DIMMABLE])], [])
    assert room.capabilities == DIMMABLE.capabilities


@pytest.mark.asyncio
async def test_room_turn_on_and_off_send_one_room_command():
    client = AsyncMock()
    room = CyncRoom("Office", 32772, 1, [CyncGroup("Office", 32773, 1, [DIMMABLE])], [], client)

    await room.turn_on()
    await room.turn_off()

    client.set_power_state.assert_any_await(room, True)
    client.set_power_state.assert_any_await(room, False)
    assert client.set_power_state.await_count == 2

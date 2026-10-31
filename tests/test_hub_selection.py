"""Hub selection for commands: prefer a device that answered the Wi-Fi probe, but don't hold commands for the
30-40 s the first probe answers can take after a (re)connect."""
import asyncio
import time

import pytest

from pycync import CyncLight
from pycync.devices.device_types import DeviceType
from pycync.devices.devices import CyncPlug
from pycync.devices.groups import CyncHome
from pycync.exceptions import NoHubConnectedError
from pycync.tcp import command_client
from pycync.tcp.command_client import CommandClient


def _home(plug_online: bool, plug_wifi: bool):
    plug = CyncPlug(plug_online, plug_wifi, 2345, 15, 5432, "Kitchen Plug", 172, DeviceType.PLUG, "AB", "ID1", "Code")
    bulb = CyncLight(True, False, 1234567890004, 4, 5432, "Bulb", 17, DeviceType.LIGHT, None, None, None)
    return CyncHome("home", 5432, [], [plug, bulb]), plug


def _client(probed: bool) -> CommandClient:
    client = CommandClient.__new__(CommandClient)  # no user or connection needed for hub selection
    client._device_statuses_updated = probed
    return client


@pytest.mark.asyncio
async def test_probed_hub_is_used_immediately():
    home, plug = _home(plug_online=True, plug_wifi=True)
    started = time.monotonic()
    assert await _client(probed=True)._fetch_hub_device(home) is plug
    assert time.monotonic() - started < 0.5


@pytest.mark.asyncio
async def test_falls_back_to_cloud_online_hub_while_probes_pending():
    command_client.HUB_PROBE_WAIT_SECONDS = 0.3
    try:
        home, plug = _home(plug_online=True, plug_wifi=False)
        started = time.monotonic()
        assert await asyncio.wait_for(_client(probed=False)._fetch_hub_device(home), 3) is plug
        assert time.monotonic() - started < 2
    finally:
        command_client.HUB_PROBE_WAIT_SECONDS = 5


@pytest.mark.asyncio
async def test_no_online_hub_raises_after_wait():
    command_client.HUB_PROBE_WAIT_SECONDS = 0.3
    try:
        home, _ = _home(plug_online=False, plug_wifi=False)
        with pytest.raises(NoHubConnectedError):
            await asyncio.wait_for(_client(probed=False)._fetch_hub_device(home), 3)
    finally:
        command_client.HUB_PROBE_WAIT_SECONDS = 5

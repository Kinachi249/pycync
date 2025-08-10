"""
Module containing device type related information.
All info in this module was pulled from the Cync app, and should not be manually modified
unless the changes come directly from the app's information.

Note that just because a device is listed here, does not necessarily mean this library supports it.
This is here to establish a complete list of types so implementing devices in the future has fewer steps.

List last updated from Android app version 6.20.0.54634-60b11b1f5
"""

from enum import Enum


class DeviceType(Enum):
    LIGHT = "Light"
    INDOOR_LIGHT_STRIP = "IndoorLightStrip"
    OUTDOOR_LIGHT_STRIP = "OutdoorLightStrip"
    NEON_LIGHT_STRIP = "NeonLightStrip"
    OUTDOOR_NEON_LIGHT_STRIP = "OutdoorNeonLightStrip"
    CAFE_STRING_LIGHTS = "CafeStringLights"
    DOWNLIGHT = "Downlight"
    UNDERCABINET_FIXTURES = "UndercabinetFixtures"
    LIGHT_TILE = "LightTile"
    PLUG = "Plug"
    SWITCH = "Switch"
    FAN_SPEED_SWITCH = "FanSpeedSwitch"
    WIRE_FREE_SWITCH = "WireFreeSwitch"
    WIRE_FREE_SENSOR = "WireFreeSensor"
    WIRE_FREE_REMOTE = "WireFreeRemote"
    SOL = "Sol"
    C_REACH = "C-Reach"
    THERMOSTAT = "Thermostat"
    CAMERA = "Camera"
    UNKNOWN = "Unknown"

    @classmethod
    def is_light(cls, device_type_code: int) -> bool:
        resolved_type = DEVICE_TYPES.get(device_type_code, DeviceType.UNKNOWN)
        return resolved_type in {cls.LIGHT, cls.INDOOR_LIGHT_STRIP, cls.OUTDOOR_LIGHT_STRIP, cls.NEON_LIGHT_STRIP,
                                 cls.CAFE_STRING_LIGHTS, cls.DOWNLIGHT, cls.UNDERCABINET_FIXTURES, cls.LIGHT_TILE}


DEVICE_TYPES = {
    # FullColorStripGen1Standalone
    8: DeviceType.INDOOR_LIGHT_STRIP,
    # CLifeA19Gen2StandaloneCECTier2
    9: DeviceType.LIGHT,
    # CSleepA19Gen2StandaloneCECTier2
    10: DeviceType.LIGHT,
    # CSleepBR30Gen2StandaloneCECTier2
    11: DeviceType.LIGHT,
    # CLifeA19TCOGen2Standalone
    13: DeviceType.LIGHT,
    # CSleepA19TCOGen2Standalone
    14: DeviceType.LIGHT,
    # CSleepBR30TCOGen2Standalone
    15: DeviceType.LIGHT,
    # CLifeA19Gen2GoogleBundle
    17: DeviceType.LIGHT,
    # CLifeA19Gen2MadeForGoogle
    18: DeviceType.LIGHT,
    # CSleepA19Gen2MadeForGoogle
    19: DeviceType.LIGHT,
    # CSleepBR30Gen2MadeForGoogle
    20: DeviceType.LIGHT,
    # FullColorA19Gen1MadeForGoogle
    21: DeviceType.LIGHT,
    # FullColorBR30Gen1MadeForGoogle
    22: DeviceType.LIGHT,
    # FullColorStripGen1MadeForGoogle
    23: DeviceType.INDOOR_LIGHT_STRIP,
    # CLifeA19Gen2MadeForGoogleCECTier2
    24: DeviceType.LIGHT,
    # CSleepA19Gen2MadeForGoogleCECTier2
    25: DeviceType.LIGHT,
    # CSleepBR30Gen2MadeForGoogleCECTier2
    26: DeviceType.LIGHT,
    # CLifeA19TCOGen2MadeForGoogle
    27: DeviceType.LIGHT,
    # CSleepA19TCOGen2MadeForGoogle
    28: DeviceType.LIGHT,
    # CSleepBR30TCOGen2MadeForGoogle
    29: DeviceType.LIGHT,
    # FullColorA19TCOGen2Standalone
    30: DeviceType.LIGHT,
    # FullColorA19TCOGen2MadeForGoogle
    31: DeviceType.LIGHT,
    # FullColorBR30TCOGen2Standalone
    32: DeviceType.LIGHT,
    # FullColorBR30TCOGen2MadeForGoogle
    33: DeviceType.LIGHT,
    # FullColorStripTCOGen2Standalone
    34: DeviceType.INDOOR_LIGHT_STRIP,
    # FullColorStripTCOGen2MadeForGoogle
    35: DeviceType.INDOOR_LIGHT_STRIP,
    # FourWireSwitchDimmerGen2
    36: DeviceType.SWITCH,
    # FourWireSwitchMotionSensingDimmerGen2
    37: DeviceType.SWITCH,
    # FourWireSwitchCircleGen2
    38: DeviceType.SWITCH,
    # FourWireSwitchPaddleGen2
    39: DeviceType.SWITCH,
    # FourWireSwitchToggleGen2
    40: DeviceType.SWITCH,
    # SingleChipFullColorUnderCabinetBarFixture12InchGen1
    41: DeviceType.UNDERCABINET_FIXTURES,
    # SingleChipFullColorUnderCabinetBarFixture18InchGen1
    42: DeviceType.UNDERCABINET_FIXTURES,
    # SingleChipFullColorUnderCabinetBarFixture24InchGen1
    43: DeviceType.UNDERCABINET_FIXTURES,
    # SingleChipFullColorUnderCabinetPuckFixtureGen1
    44: DeviceType.UNDERCABINET_FIXTURES,
    # SingleChipFullColorRecessedCanRetrofitFixture6InchGen1
    46: DeviceType.DOWNLIGHT,
    # SingleChipFullColorRecessedCanRetrofitFixture6InchGen1NonMatter
    47: DeviceType.DOWNLIGHT,
    # FourWireSwitchDimmerGen1
    48: DeviceType.SWITCH,
    # FourWireSwitchMotionSensingDimmerGen1
    49: DeviceType.SWITCH,
    # FourWireSwitchPaddleGen1
    51: DeviceType.SWITCH,
    # FourWireSwitchToggleGen1
    52: DeviceType.SWITCH,
    # FourWireSwitchCircleGen1
    53: DeviceType.SWITCH,
    # NoNeutralSwitchGen1Dimmer
    55: DeviceType.SWITCH,
    # NoNeutralSwitchGen1MotionSensingDimmer
    56: DeviceType.SWITCH,
    # NoNeutralSwitchGen1SwitchPaddle
    57: DeviceType.SWITCH,
    # NoNeutralSwitchGen1SwitchToggle
    58: DeviceType.SWITCH,
    # NoNeutralSwitchGen1SwitchCircle
    59: DeviceType.SWITCH,
    # FourWireSwitchPaddleTCOGen1
    61: DeviceType.SWITCH,
    # FourWireSwitchToggleTCOGen1
    62: DeviceType.SWITCH,
    # FourWireSwitchCircleTCOGen1
    63: DeviceType.SWITCH,
    # PlugGen1
    64: DeviceType.PLUG,
    # PlugTCOGen2
    65: DeviceType.PLUG,
    # PlugGen2
    66: DeviceType.PLUG,
    # PlugOutdoorGen1
    67: DeviceType.PLUG,
    # SingleChipPlug
    68: DeviceType.PLUG,
    # PlugOutdoorGen2
    69: DeviceType.PLUG,
    # SingleChipFullColorIndoorPremiumLightStrip16ftGen3
    71: DeviceType.INDOOR_LIGHT_STRIP,
    # SingleChipFullColorIndoorPremiumLightStrip32ftGen3
    72: DeviceType.INDOOR_LIGHT_STRIP,
    # SingleChipFullColorOutdoorNeonLightStrip16ft
    73: DeviceType.OUTDOOR_NEON_LIGHT_STRIP,
    # SingleChipFullColorOutdoorNeonLightStrip32ft
    74: DeviceType.OUTDOOR_NEON_LIGHT_STRIP,
    # SingleChipFullColorOutdoorCafeLights24ftGen1
    75: DeviceType.CAFE_STRING_LIGHTS,
    # SingleChipFullColorOutdoorCafeLights48ftGen1
    76: DeviceType.CAFE_STRING_LIGHTS,
    # SolGen1Standalone
    80: DeviceType.SOL,
    # FanSpeedSwitchGen1
    81: DeviceType.FAN_SPEED_SWITCH,
    # CLifeBR30Gen1Standalone
    82: DeviceType.LIGHT,
    # CSleepBR30Gen2Standalone
    83: DeviceType.LIGHT,
    # WireFreeMotionSensor
    96: DeviceType.WIRE_FREE_SENSOR,
    # SingleChipFullColorBulbST19Gen2
    97: DeviceType.LIGHT,
    # SingleChipFullColorBulbG25Gen2
    98: DeviceType.LIGHT,
    # SingleChipSoftWhiteBulbST19Gen2
    99: DeviceType.LIGHT,
    # SingleChipSoftWhiteBulbG25Gen2
    100: DeviceType.LIGHT,
    # SingleChipFullColorBulbBCGen1
    101: DeviceType.LIGHT,
    # SingleChipFullColorBulbBMGen1
    102: DeviceType.LIGHT,
    # SingleChipRevealSoftWhiteBulbA19Gen2
    103: DeviceType.LIGHT,
    # SingleChipFullColorBulbPAR38OutdoorGen2
    104: DeviceType.LIGHT,
    # SingleChipFullColorBulbA21Gen2
    105: DeviceType.LIGHT,
    # SingleChipRevealFullColorBulbA19Gen2
    107: DeviceType.LIGHT,
    # SingleChipRevealFullColorBulbBR30Gen2
    108: DeviceType.LIGHT,
    # SingleChipRevealFullColorBulbA21Gen2
    109: DeviceType.LIGHT,
    # SingleChipFullColorIndoorValueLightStrip16ftGen3
    110: DeviceType.INDOOR_LIGHT_STRIP,
    # PlugOutdoorGen3
    111: DeviceType.PLUG,
    # WireFreeSmartSwitchDimmer
    112: DeviceType.WIRE_FREE_SWITCH,
    # WireFreeSmartSwitchDimmerPlusColorController
    113: DeviceType.WIRE_FREE_SWITCH,
    # WireFreeSmartRemoteDimmer
    114: DeviceType.WIRE_FREE_REMOTE,
    # WireFreeSmartRemoteDimmerPlusColorController
    115: DeviceType.WIRE_FREE_REMOTE,
    # FourWireSwitchDimmerGen3
    116: DeviceType.SWITCH,
    # FourWireSwitchMotionSensingDimmerGen3
    117: DeviceType.SWITCH,
    # FourWireSwitchCircleGen3
    118: DeviceType.SWITCH,
    # FourWireSwitchPaddleGen3
    119: DeviceType.SWITCH,
    # FourWireSwitchToggleGen3
    120: DeviceType.SWITCH,
    # FanSpeedSwitchGen2
    121: DeviceType.FAN_SPEED_SWITCH,
    # ThermostatGen2
    122: DeviceType.THERMOSTAT,
    # SingleChipFullColorIndoorValueLightStrip32ftGen3
    123: DeviceType.INDOOR_LIGHT_STRIP,
    # FourWireSwitchKeypadDimmerGen1
    124: DeviceType.SWITCH,
    # FourWireSwitchPaddleDimmerGen1
    125: DeviceType.SWITCH,
    # DirectConnectSoftWhiteBulbA19
    128: DeviceType.LIGHT,
    # DirectConnectTunableWhiteBulbA19
    129: DeviceType.LIGHT,
    # DirectConnectTunableWhiteBulbBR30
    130: DeviceType.LIGHT,
    # DirectConnectFullColorBulbA19
    131: DeviceType.LIGHT,
    # DirectConnectFullColorBulbBR30
    132: DeviceType.LIGHT,
    # DirectConnectFullColorLightStrip
    133: DeviceType.INDOOR_LIGHT_STRIP,
    # SingleChipSoftWhiteA19
    134: DeviceType.LIGHT,
    # SingleChipTunableWhiteA19
    135: DeviceType.LIGHT,
    # SingleChipTunableWhiteBR30
    136: DeviceType.LIGHT,
    # SingleChipFullColorBulbA19
    137: DeviceType.LIGHT,
    # SingleChipFullColorBulbBR30
    138: DeviceType.LIGHT,
    # SingleChipFullColorIndoorValueLightStripGen2
    139: DeviceType.INDOOR_LIGHT_STRIP,
    # SingleChipFullColorBulbPAR38Outdoor
    140: DeviceType.LIGHT,
    # SingleChipFullColorOutdoorPremiumLightStrip16ftGen2
    141: DeviceType.OUTDOOR_LIGHT_STRIP,
    # SingleChipFullColorWafer4InchGen1
    142: DeviceType.DOWNLIGHT,
    # SingleChipFullColorWafer6InchGen1
    143: DeviceType.DOWNLIGHT,
    # SingleChipTunableWhiteWafer4InchGen1
    144: DeviceType.DOWNLIGHT,
    # SingleChipTunableWhiteWafer6InchGen1
    145: DeviceType.DOWNLIGHT,
    # SingleChipFullColorBulbST19Gen1
    146: DeviceType.LIGHT,
    # SingleChipFullColorBulbG25Gen1
    147: DeviceType.LIGHT,
    # SingleChipSoftWhiteBulbST19Gen1
    148: DeviceType.LIGHT,
    # SingleChipSoftWhiteBulbG25Gen1
    149: DeviceType.LIGHT,
    # SingleChipSoftWhiteBulbBCGen1
    150: DeviceType.LIGHT,
    # SingleChipSoftWhiteBulbBMGen1
    151: DeviceType.LIGHT,
    # SingleChipRevealSoftWhiteBulbA19
    152: DeviceType.LIGHT,
    # SingleChipRevealFullColorBulbA19
    153: DeviceType.LIGHT,
    # SingleChipRevealFullColorBulbBR30
    154: DeviceType.LIGHT,
    # SingleChipFullColorDynamicEffectsBulbA19
    155: DeviceType.LIGHT,
    # SingleChipRevealFullColorBulbA21
    156: DeviceType.LIGHT,
    # SingleChipFullColorDynamicEffectsBulbBR30
    157: DeviceType.LIGHT,
    # SingleChipFullColorIndoorPremiumLightStripGen2
    158: DeviceType.INDOOR_LIGHT_STRIP,
    # SingleChipFullColorOutdoorPremiumLightStrip32ftGen2
    159: DeviceType.OUTDOOR_LIGHT_STRIP,
    # SingleChipFullColorBulbA21
    160: DeviceType.LIGHT,
    # SingleChipRevealFullColorWafer2InchGen1
    161: DeviceType.DOWNLIGHT,
    # SingleChipRevealFullColorGimbalWafer4InchGen1
    162: DeviceType.DOWNLIGHT,
    # SingleChipRevealFullColorGimbalWafer6InchGen1
    163: DeviceType.DOWNLIGHT,
    # SingleChipRevealFullColorHighLumenWafer4InchGen1
    164: DeviceType.DOWNLIGHT,
    # SingleChipRevealFullColorHighLumenWafer6InchGen1
    165: DeviceType.DOWNLIGHT,
    # SingleChipFullColorDynamicEffectsNeonLightStrip10ftGen1
    166: DeviceType.NEON_LIGHT_STRIP,
    # SingleChipFullColorDynamicEffectsNeonLightStrip16ftGen1
    167: DeviceType.NEON_LIGHT_STRIP,
    # SingleChipFullColorDynamicEffectsHexagonLightTileGen1
    168: DeviceType.LIGHT_TILE,
    # SingleChipRevealFullColorWafer4InchGen1
    169: DeviceType.DOWNLIGHT,
    # SingleChipRevealFullColorWafer6InchGen1
    170: DeviceType.DOWNLIGHT,
    # SingleChipFullColorBulbA19Gen3
    171: DeviceType.LIGHT,
    # SingleChipPlugTCOGen1
    172: DeviceType.PLUG,
    # SingleChipFullColorBulbBR30Gen3
    173: DeviceType.LIGHT,
    # SingleChipRevealFullColorWafer4InchGen2
    174: DeviceType.DOWNLIGHT,
    # SingleChipRevealFullColorWafer6InchGen2
    175: DeviceType.DOWNLIGHT,
    # SingleChipRevealFullColorWafer2InchGen2
    177: DeviceType.DOWNLIGHT,
    # SingleChipRevealFullColorHighLumenWafer4InchGen2
    180: DeviceType.DOWNLIGHT,
    # SingleChipRevealFullColorHighLumenWafer6InchGen2
    181: DeviceType.DOWNLIGHT,
    # SingleChipFullColorBulbA19ClearSpiralGen1
    182: DeviceType.LIGHT,
    # ThermostatGen1
    224: DeviceType.THERMOSTAT,
    # CameraIndoorGen1
    240: DeviceType.CAMERA,
    # CameraOutdoorWiredGen1
    241: DeviceType.CAMERA,
    # CameraOutdoorBatteryGen1
    242: DeviceType.CAMERA
}

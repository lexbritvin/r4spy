from r4s.protocol import int_to_arr
from r4s.protocol.commands import RedmondCommand
from r4s.protocol.responses_kettle import ColorSchemeResponse, PaletteConfigResponse, FreshWaterSettingsResponse, \
    FreshWaterResponse, NightLightWorkTimeResponse
from r4s.protocol.responses import ErrorResponse, SuccessResponse


class Cmd48Kettle200(RedmondCommand):
    CODE = 48
    resp_cls = NightLightWorkTimeResponse


class Cmd50SetLights(RedmondCommand):
    CODE = 50
    resp_cls = ErrorResponse

    def __init__(self, light_type):
        self.type = light_type
        # 0x00 - boil light, 0x01 backlight.
        # TODO: Rework.
        if light_type == 0x00:
            self.percent = [0x28, 0x46, 0x64]
        else:
            self.percent = [0x00, 0x32, 0x64]
        self.rgb1 = [0x00, 0x00, 0xff]
        self.rgb2 = [0xff, 0x00, 0x00]
        self.rgb_mid = [0x00, 0xff, 0x00]
        self.brightness = 0x5e

    def to_arr(self):
        data = [self.type]
        data.extend([self.percent[0], self.brightness])
        data.extend(self.rgb1)
        data.extend([self.percent[1], self.brightness])
        data.extend(self.rgb_mid)
        data.extend([self.percent[2], self.brightness])
        data.extend(self.rgb2)
        return data


class Cmd51GetLights(RedmondCommand):
    CODE = 51
    resp_cls = ColorSchemeResponse

    def __init__(self, light_type):
        self.type = light_type

    def to_arr(self):
        return [self.type]


class Cmd52(RedmondCommand):
    CODE = 52
    resp_cls = ErrorResponse

    def __init__(self, secs):
        self.secs = secs

    def to_arr(self):
        return int_to_arr(self.secs, 2)


class Cmd53(RedmondCommand):
    CODE = 53
    resp_cls = PaletteConfigResponse

    def to_arr(self):
        # TODO: Investigate. Can be 0 for boil, 1 for night light, or 200 for both? 1100 1000.
        #  0 and 1 are used only on palette error.
        return [200]

    def parse_resp(self, resp):
        return resp


class CmdU54(RedmondCommand):
    CODE = 54
    resp_cls = SuccessResponse


class Cmd55UseBacklight(RedmondCommand):
    CODE = 55
    resp_cls = ErrorResponse

    def __init__(self, state):
        self.state = 0x01 if state else 0x00

    def to_arr(self):
        # TODO: Not clear.
        return [200, 200, self.state]


class Cmd56(RedmondCommand):
    CODE = 56
    resp_cls = ErrorResponse

    def to_arr(self):
        # Disco functionality.
        return NotImplemented


class Cmd57(RedmondCommand):
    CODE = 57
    resp_cls = ErrorResponse

    def to_arr(self):
        # Disco functionality.
        return NotImplemented


class Cmd81(RedmondCommand):
    CODE = 81
    resp_cls = FreshWaterSettingsResponse

    def __init__(self, state, hours):
        self.state = 0x01 if state else 0x00
        self.hours = hours

    def to_arr(self):
        data = [0] * 16
        data[1] = self.state
        data[2:3] = int_to_arr(self.hours, 2)
        return data


class Cmd82(RedmondCommand):
    CODE = 82
    resp_cls = FreshWaterResponse

    def to_arr(self):
        return [0x00]

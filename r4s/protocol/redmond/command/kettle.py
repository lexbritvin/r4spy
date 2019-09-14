from r4s.protocol import int_to_arr
from r4s.protocol.redmond.command.common import RedmondCommand
from r4s.protocol.redmond.response.kettle import FreshWaterSettingsResponse, FreshWaterResponse


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

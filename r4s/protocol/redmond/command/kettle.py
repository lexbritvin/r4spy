from r4s.protocol import int_to_arr, fahrenheit_to_celsius, float_to_arr
from r4s.protocol.redmond.command.common import RedmondCommand, FullProgram
from r4s.protocol.redmond.response.kettle import FreshWaterSettingsResponse, FreshWaterResponse, \
    BOIL_TIME_RELATIVE_DEFAULT, KettleResponse


class FullKettleProgram(FullProgram):

    def to_arr(self):
        raise NotImplemented


class FullKettle200Program(FullProgram):

    def __init__(self, program, trg_temp, boil_time):
        if not KettleResponse.is_allowed_temp(program, trg_temp):
            raise ValueError('Incorrect temp')
        self.program = program
        self.trg_temp = trg_temp
        self.boil_time = boil_time

    def to_arr(self):
        data = [0] * 16
        data[0] = self.program
        data[2] = self.trg_temp
        data[13] = BOIL_TIME_RELATIVE_DEFAULT + self.boil_time
        return data


class Kettle200AProgram(FullKettle200Program):

    def to_arr(self):
        data = super().to_arr()
        c_temp = fahrenheit_to_celsius(self.trg_temp)
        data[1:3] = float_to_arr(c_temp)[0:2]
        return data


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

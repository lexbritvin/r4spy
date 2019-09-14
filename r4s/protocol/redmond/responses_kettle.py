from r4s.protocol import int_from_bytes, int_to_arr
from r4s.protocol.redmond.responses import RedmondResponse

LIGHT_TYPE_BOIL = 0x00
LIGHT_TYPE_BACKLIGHT = 0x01

MODE_BOIL = 0x00
MODE_HEAT = 0x01
MODE_LIGHT = 0x03

STATE_OFF = 0x00
STATE_ON = 0x02

BOIL_TIME_RELATIVE_DEFAULT = 0x80  # Relative val for boil time.
BOIL_TIME_MAX = 5  # The range according to the App [-5:5].
BOIL_TEMP = 0x00
MAX_TEMP = 90  # According to
MIN_TEMP = 35  # the official App.


class KettleResponse(RedmondResponse):

    @staticmethod
    def is_allowed_temp(mode, trg_temp):
        if mode in [MODE_BOIL, MODE_LIGHT] and trg_temp == BOIL_TEMP:
            return True
        if MIN_TEMP <= trg_temp <= MAX_TEMP:
            return True
        return False


class Kettle170Response(KettleResponse):

    def __init__(self, program, trg_temp, curr_temp, remaining_time_h, remaining_time_min, state):
        if not self.is_allowed_temp(MODE_BOIL, trg_temp):
            raise ValueError("Incorrect target temp {} . Allowed range [{}:{}]"
                             .format(trg_temp, MIN_TEMP, MAX_TEMP))
        self.program = program
        self.trg_temp = trg_temp
        self.curr_temp = curr_temp
        self.remaining_time_h = remaining_time_h
        self.remaining_time_min = remaining_time_min
        self.state = state

    @classmethod
    def from_bytes(cls, data: list):
        return cls(
            program=data[0],
            trg_temp=data[1],
            curr_temp=data[2],
            remaining_time_h=data[5],
            remaining_time_min=data[6],
            state=data[8],
        )

    def to_arr(self):
        data = [0x00] * 8
        data[0] = self.program
        data[1] = self.trg_temp
        data[2] = self.curr_temp
        data[5] = self.remaining_time_h
        data[6] = self.remaining_time_min
        data[8] = self.state
        return data


class Kettle171Response(KettleResponse):
    def __init__(self, program, trg_temp, curr_temp, remaining_time_h, remaining_time_min, heating, state, err):
        if not self.is_allowed_temp(MODE_BOIL, trg_temp):
            raise ValueError("Incorrect target temp {} . Allowed range [{}:{}]"
                             .format(trg_temp, MIN_TEMP, MAX_TEMP))
        self.program = program
        self.trg_temp = trg_temp
        self.curr_temp = curr_temp
        self.remaining_time_h = remaining_time_h
        self.remaining_time_min = remaining_time_min
        self.state = state  # If water was boiled. 0 or 2.
        self.heating = heating
        self.err = err

    @classmethod
    def from_bytes(cls, data: list):
        return cls(
            program=data[0],
            trg_temp=data[2],
            curr_temp=data[10],
            remaining_time_h=data[5],
            remaining_time_min=data[6],
            state=data[8],
            heating=data[7],
            err=data[9],
        )

    def to_arr(self):
        data = [0x00] * 16
        data[0] = self.program
        data[2] = self.trg_temp
        data[10] = self.curr_temp
        data[5] = self.remaining_time_h
        data[6] = self.remaining_time_min
        data[8] = self.state
        data[7] = self.heating
        data[9] = self.err
        return data


class Kettle173Response(KettleResponse):
    def __init__(self, program, trg_temp, curr_temp, remaining_time_h, remaining_time_min, heating, state, err, block):
        if not self.is_allowed_temp(MODE_BOIL, trg_temp):
            raise ValueError("Incorrect target temp {} . Allowed range [{}:{}]"
                             .format(trg_temp, MIN_TEMP, MAX_TEMP))
        self.program = program
        self.trg_temp = trg_temp
        self.curr_temp = curr_temp
        self.remaining_time_h = remaining_time_h
        self.remaining_time_min = remaining_time_min
        self.state = state  # If water was boiled. 0 or 2.
        self.heating = heating
        self.err = err
        self.block = block

    @classmethod
    def from_bytes(cls, data: list):
        return cls(
            program=data[0],
            trg_temp=data[2],
            curr_temp=data[10],
            remaining_time_h=data[5],
            remaining_time_min=data[6],
            state=data[8],
            heating=data[7],
            err=data[9],
            block=data[11],
        )

    def to_arr(self):
        data = [0x00] * 16
        data[0] = self.program
        data[2] = self.trg_temp
        data[10] = self.curr_temp
        data[5] = self.remaining_time_h
        data[6] = self.remaining_time_min
        data[8] = self.state
        data[7] = self.heating
        data[9] = self.err
        data[11] = self.block
        return data


class Kettle200AResponse(KettleResponse):

    def __init__(self, program, trg_temp, is_sound, curr_temp, color_change_period, state, boil_time, err):
        if program not in [MODE_BOIL, MODE_HEAT, MODE_LIGHT]:
            raise ValueError("Incorrect mode {}.".format(program))
        if not self.is_allowed_temp(program, trg_temp):
            raise ValueError("Incorrect target temp {} for mode {}. Allowed range [{}:{}]"
                             .format(trg_temp, program, MIN_TEMP, MAX_TEMP))
        if abs(boil_time) > BOIL_TIME_MAX:
            raise ValueError("Incorrect boil time {} specified. Allowed range [{}:{}]"
                             .format(boil_time, -BOIL_TIME_MAX, BOIL_TIME_MAX))
        self.program = program
        self.trg_temp = trg_temp
        self.is_sound = is_sound
        self.curr_temp = curr_temp
        self.color_change_period = color_change_period
        self.state = state
        self.boil_time = boil_time
        self.err = err

    @classmethod
    def from_bytes(cls, data: list):
        return cls(
            program=data[0],
            trg_temp=data[2],  # TODO: Check code.
            is_sound=data[4],
            curr_temp=data[5],  # TODO: Check code.
            color_change_period=data[6],  # TODO: Check code.
            state=data[8],
            boil_time=data[13] - BOIL_TIME_RELATIVE_DEFAULT,
            err=data[15],
        )

    def to_arr(self):
        data = [0x00] * 16
        data[0] = self.program
        data[2] = self.trg_temp
        data[4] = self.is_sound
        data[5] = self.curr_temp
        data[6] = self.color_change_period
        data[8] = self.state
        data[13] = BOIL_TIME_RELATIVE_DEFAULT + self.boil_time
        data[15] = self.err
        return data


class Kettle200Response(KettleResponse):
    def __init__(self, program, trg_temp, is_blocked, is_sound, curr_temp, color_change_period, state, boil_time, err):
        if program not in [MODE_BOIL, MODE_HEAT, MODE_LIGHT]:
            raise ValueError("Incorrect mode {}.".format(program))
        if not self.is_allowed_temp(program, trg_temp):
            raise ValueError("Incorrect target temp {} for mode {}. Allowed range [{}:{}]"
                             .format(trg_temp, program, MIN_TEMP, MAX_TEMP))
        if abs(boil_time) > BOIL_TIME_MAX:
            raise ValueError("Incorrect boil time {} specified. Allowed range [{}:{}]"
                             .format(boil_time, -BOIL_TIME_MAX, BOIL_TIME_MAX))
        self.program = program
        self.trg_temp = trg_temp
        self.is_blocked = is_blocked
        self.is_sound = is_sound
        self.curr_temp = curr_temp
        self.color_change_period = color_change_period
        self.state = state
        self.boil_time = boil_time
        self.err = err

    @classmethod
    def from_bytes(cls, data: list):
        return cls(
            program=data[0],
            trg_temp=data[2],  # TODO: Check code.
            is_blocked=data[3],
            is_sound=data[4],
            curr_temp=data[5],  # TODO: Check code.
            color_change_period=data[6],  # TODO: Check code.
            state=data[8],
            boil_time=data[13] - BOIL_TIME_RELATIVE_DEFAULT,
            err=data[15],
        )

    def to_arr(self):
        data = [0x00] * 16
        data[0] = self.program
        data[2] = self.trg_temp
        data[3] = self.is_blocked
        data[4] = self.is_sound
        data[5] = self.curr_temp
        data[6] = self.color_change_period
        data[8] = self.state
        data[13] = BOIL_TIME_RELATIVE_DEFAULT + self.boil_time
        data[15] = self.err
        return data


class ColorSchemeResponse(RedmondResponse):

    def __init__(self, scheme_id, color1, color2, color3):
        if len(color1) != 5 or len(color2) != 5 or len(color3) != 5:
            ValueError('Incorrect color config')
        self.id = scheme_id
        self.colors = []
        for color in [color1, color2, color3]:
            self.colors.append({
                'percent': color[0],
                'brightness': color[1],
                'red': color[2],
                'green': color[3],
                'blue': color[4],
            })

    @classmethod
    def from_bytes(cls, data: list):
        return cls(
            scheme_id=data[0],
            color1=data[1:6],
            color2=data[6:11],
            color3=data[11:16],
        )

    def to_arr(self):
        data = [self.id]
        for color in self.colors:
            data.append(color['percent'])
            data.append(color['brightness'])
            data.append(color['red'])
            data.append(color['green'])
            data.append(color['blue'])
        return data


class PaletteConfigResponse(RedmondResponse):

    def __init__(self, light_type, state, palette_num, err):
        self.light_type = light_type  # Boil 0 or night light 1.
        self.state = state
        self.palette_num = palette_num
        self.err = err

    @classmethod
    def from_bytes(cls, data: list):
        return cls(
            light_type=data[0],
            state=data[2],
            palette_num=data[3],
            err=data[4],
        )

    def to_arr(self):
        return [self.light_type, 0, self.state, self.palette_num, self.err]


class FreshWaterSettingsResponse(RedmondResponse):

    def __init__(self, err):
        self.err = err

    @classmethod
    def from_bytes(cls, data: list):
        return cls(
            err=data[1],
        )

    def to_arr(self):
        return [0, self.err]


class FreshWaterResponse(RedmondResponse):

    def __init__(self, state, hours, hours_last_update):
        self.state = state
        self.hours = hours
        self.hours_last_update = hours_last_update

    @classmethod
    def from_bytes(cls, data: list):
        return cls(
            state=data[1],
            hours=int_from_bytes(data[2, 4]),
            hours_last_update=int_from_bytes(data[4, 6]),
        )

    def to_arr(self):
        data = [0] * 16
        data[2:4] = int_to_arr(self.hours, 2)
        data[4:6] = int_to_arr(self.hours_last_update, 2)
        return data


class NightLightWorkTimeResponse(RedmondResponse):

    def __init__(self, time):
        self.time = time

    @classmethod
    def from_bytes(cls, data: list):
        return cls(
            time=data[0],
        )

    def to_arr(self):
        return [self.time, 0]

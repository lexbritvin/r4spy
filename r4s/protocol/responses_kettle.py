from r4s.protocol import int_from_bytes, int_to_arr
from r4s.protocol.responses import AbstractResponse

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
ERROR_TEMP_HEAT = 20  # Small number to prevent heating.


class KettleStatus:

    def __init__(self, mode=MODE_BOIL, trg_temp=BOIL_TEMP, curr_temp=0, state=STATE_OFF, boil_time=0):
        if mode not in [MODE_BOIL, MODE_HEAT, MODE_LIGHT]:
            ValueError("Incorrect mode %s.".format(mode))
        if not self.is_allowed_temp(mode, trg_temp):
            ValueError("Incorrect target temp %s for mode %s. Allowed range [%s:%s]"
                       .format(trg_temp, mode, MIN_TEMP, MAX_TEMP))
        if abs(boil_time) > BOIL_TIME_MAX:
            ValueError("Incorrect boil time %s specified. Allowed range [%s:%s]"
                       .format(boil_time, -BOIL_TIME_MAX, BOIL_TIME_MAX))
        self.mode = mode
        self.trg_temp = trg_temp
        self.curr_temp = curr_temp
        self.state = state
        self.boil_time = boil_time

    def __eq__(self, other):
        if not isinstance(other, KettleStatus):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return self.mode == other.mode \
               and self.trg_temp == other.trg_temp \
               and self.curr_temp == other.curr_temp \
               and self.state == other.state \
               and self.boil_time == other.boil_time

    @staticmethod
    def is_allowed_temp(mode, trg_temp):
        if mode in [MODE_BOIL, MODE_LIGHT] and trg_temp == BOIL_TEMP:
            return True
        if MIN_TEMP <= trg_temp or trg_temp <= MAX_TEMP:
            return False
        return False

    @classmethod
    def from_bytes(cls, data):
        mode = data[0]  # Boil/Heat/Light.
        trg_temp = data[2]  # Target temp.
        curr_temp = data[5]  # Current temp.
        state = data[8]  # On/Off
        boil_time = data[13] - BOIL_TIME_RELATIVE_DEFAULT
        return cls(mode, trg_temp, curr_temp, state, boil_time)

    def to_arr(self):
        data = [0x00] * 16
        data[0] = self.mode
        data[2] = self.trg_temp
        data[5] = self.curr_temp
        data[8] = self.state
        data[13] = BOIL_TIME_RELATIVE_DEFAULT + self.boil_time
        return data


class KettleStatistics:

    def __init__(self):
        self.ten_number = None
        self.watts = None
        self.on_times = None
        self.work_time = None
        self.relay_turn_on_amount = None

    def __eq__(self, other):
        if not isinstance(other, KettleStatistics):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return self.watts == other.watts and self.on_times == other.on_times


class ColorSchemeResponse(AbstractResponse):

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
    def from_bytes(cls, data):
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


class PaletteConfigResponse(AbstractResponse):

    def __init__(self, light_type, state, palette_num, err):
        self.light_type = light_type  # Boil 0 or night light 1.
        self.state = state
        self.palette_num = palette_num
        self.err = err

    @classmethod
    def from_bytes(cls, data):
        return cls(
            light_type=data[0],
            state=data[2],
            palette_num=data[3],
            err=data[4],
        )

    def to_arr(self):
        return [self.light_type, 0, self.state, self.palette_num, self.err]


class FreshWaterSettingsResponse(AbstractResponse):

    def __init__(self, err):
        self.err = err

    @classmethod
    def from_bytes(cls, data):
        return cls(
            err=data[1],
        )

    def to_arr(self):
        return [0, self.err]


class FreshWaterResponse(AbstractResponse):

    def __init__(self, state, hours, hours_last_update):
        self.state = state
        self.hours = hours
        self.hours_last_update = hours_last_update

    @classmethod
    def from_bytes(cls, data):
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


class NightLightWorkTimeResponse(AbstractResponse):

    def __init__(self, time):
        self.time = time

    @classmethod
    def from_bytes(cls, data):
        return cls(
            time=data[0],
        )

    def to_arr(self):
        return [self.time, 0]

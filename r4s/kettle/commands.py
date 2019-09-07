_DATA_BEGIN_BYTE = 0x55
_DATA_END_BYTE = 0xaa

LIGHT_TYPE_BOIL = 0x00
LIGHT_TYPE_BACKLIGHT = 0x01

RESPONSE_SUCCESS = 0x01
RESPONSE_FAIL = 0x00
RESPONSE_NEUTRAL = 0x00

MODE_BOIL = 0x00
MODE_HEAT = 0x01
MODE_LIGHT = 0x03

STATUS_OFF = 0x00
STATUS_ON = 0x02

BOIL_TIME_RELATIVE_DEFAULT = 0x80  # Relative val for boil time.
BOIL_TIME_MAX = 5  # The range according to the App [-5:5].
BOIL_TEMP = 0x00
MAX_TEMP = 90  # According to
MIN_TEMP = 35  # the official App.
ERROR_TEMP_HEAT = 20  # Small number to prevent heating.


class KettleStatus:

    def __init__(self, mode=MODE_BOIL, trg_temp=BOIL_TEMP, curr_temp=0, on=STATUS_OFF, boil_time=0):
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
        self.on = on
        self.boil_time = boil_time

    def __eq__(self, other):
        if not isinstance(other, KettleStatus):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return self.mode == other.mode \
               and self.trg_temp == other.trg_temp \
               and self.curr_temp == other.curr_temp \
               and self.on == other.on \
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
        status = data[8]  # On/Off
        boil_time = data[13] - BOIL_TIME_RELATIVE_DEFAULT
        return cls(mode, trg_temp, curr_temp, status, boil_time)

    def to_arr(self):
        data = [0x00] * 16
        data[0] = self.mode
        data[2] = self.trg_temp
        data[5] = self.curr_temp
        data[8] = self.on
        data[13] = BOIL_TIME_RELATIVE_DEFAULT + self.boil_time
        return data


class KettleStatistics:

    def __init__(self):
        self.watts = None
        self.on_times = None
        self.extra = [0x00, 0x9b, 0x8d, 0x02]

    def __add__(self, other):
        new = self.__class__()
        new.watts = self.newer(self.watts, other.watts)
        new.on_times = self.newer(self.on_times, other.on_times)
        new.extra = self.newer(self.extra, other.extra)
        return new

    def __eq__(self, other):
        if not isinstance(other, KettleStatistics):
            # don't attempt to compare against unrelated types
            return NotImplemented

        return self.watts == other.watts and self.on_times == other.on_times

    @staticmethod
    def newer(a, b):
        # Return always val from right param if it has value.
        if b is None:
            return a
        return b

    def from_usage_bytes(self, usage):
        self.watts = int.from_bytes(usage[6:10], 'little')  # watts * h
        self.extra = usage[1:5]  # TODO: Investigate these bytes.

    def from_times_bytes(self, times):
        self.on_times = int.from_bytes(times[3:7], 'little')

    def usage_to_arr(self):
        data = [0x00]
        data.extend(self.extra)
        data.append(0x00)
        data.append((self.watts, 8))
        return data

    def times_to_arr(self):
        data = [0x00] * 3
        data.append((self.on_times, 13))
        return data

    def get_work_time(self, power=2200):
        return self.watts / power  # Time in h.


class AbstractCommand:
    CODE = None

    @staticmethod
    def normalize(data, byte_order='little'):
        normalized = []
        for val in data:
            if type(val) is tuple:
                normalized.extend([x for x in val[0].to_bytes(val[1], byte_order)])
            else:
                normalized.append(val)

        return normalized

    @classmethod
    def wrap(cls, counter, cmd, data):
        result = [_DATA_BEGIN_BYTE, counter, cmd]
        result.extend(cls.normalize(data))
        result.append(_DATA_END_BYTE)
        return bytes(result)

    @staticmethod
    def unwrap(byte_arr):
        int_array = [x for x in byte_arr]
        start, i, cmd = int_array[:3]
        return i, cmd, int_array[3:-1]

    def wrapped(self, counter):
        return self.wrap(counter, self.CODE, self.to_arr())

    def to_arr(self):
        return []

    def parse_resp(self, resp):
        return True


class CmdFw(AbstractCommand):
    CODE = 0x01

    def parse_resp(self, resp):
        return resp


class CmdOn(AbstractCommand):
    CODE = 0x03

    def parse_resp(self, resp):
        return resp[0] == RESPONSE_SUCCESS


class CmdOff(AbstractCommand):
    CODE = 0x04

    def parse_resp(self, resp):
        return resp[0] == RESPONSE_SUCCESS


class CmdSetMode(AbstractCommand):
    CODE = 0x05

    def __init__(self, mode, temp, boil_time):
        self.status = KettleStatus(
            mode=mode,
            trg_temp=temp,
            boil_time=boil_time
        )

    def to_arr(self):
        return self.status.to_arr()

    def parse_resp(self, resp):
        return resp[0] == RESPONSE_SUCCESS


class CmdStatus(AbstractCommand):
    CODE = 0x06

    def parse_resp(self, resp):
        return KettleStatus.from_bytes(resp)


class CmdSetLights(AbstractCommand):
    CODE = 0x32

    def __init__(self, light_type):
        self.type = light_type
        # 0x00 - boil light, 0x01 backlight.
        # TODO: Rework.
        if light_type == 0x00:
            self.scale_light = [0x28, 0x46, 0x64]
        else:
            self.scale_light = [0x00, 0x32, 0x64]
        self.rgb1 = [0x00, 0x00, 0xff]
        self.rgb2 = [0xff, 0x00, 0x00]
        self.rgb_mid = [0x00, 0xff, 0x00]
        self.brightness = 0x5e

    def to_arr(self):
        data = [self.type]
        data.extend([self.scale_light[0], self.brightness])
        data.extend(self.rgb1)
        data.extend([self.scale_light[1], self.brightness])
        data.extend(self.rgb_mid)
        data.extend([self.scale_light[2], self.brightness])
        data.extend(self.rgb2)
        return data

    def parse_resp(self, resp):
        return resp[0] == RESPONSE_NEUTRAL


class CmdGetLights(AbstractCommand):
    CODE = 0x33

    def __init__(self, light_type):
        self.type = light_type

    def to_arr(self):
        return [self.type]


class CmdUseBacklight(AbstractCommand):
    CODE = 0x37

    def __init__(self, onoff):
        self.onoff = 0x01 if onoff else 0x00

    def to_arr(self):
        # TODO: Not clear.
        return [0xc8, 0xc8, self.onoff]

    def parse_resp(self, resp):
        return resp[0] == RESPONSE_NEUTRAL


class CmdStatsUsage(AbstractCommand):
    CODE = 0x47

    def to_arr(self):
        return [0x00]

    def parse_resp(self, resp):
        stats = KettleStatistics()
        stats.from_usage_bytes(resp)
        return stats


class CmdStatsTimes(AbstractCommand):
    CODE = 0x50

    def to_arr(self):
        return [0x00]

    def parse_resp(self, resp):
        stats = KettleStatistics()
        stats.from_times_bytes(resp)
        return stats


class CmdSync(AbstractCommand):
    CODE = 0x6e

    def __init__(self, timezone=4):
        # TODO: Get real timezone.
        import time
        from datetime import datetime, timedelta
        self.tmz = (timezone * 60 * 60, 2)
        self.now = (int(time.mktime(datetime.now().timetuple())), 4)
        self.tmz_sign = 0x00 if timezone >= 0 else 0x01  # TODO: Possibly 0x01 for negative timezone, need to discover.

    def to_arr(self):
        # TODO: Unclear 0x00.
        return [self.tmz, self.now, self.tmz_sign, 0x00]

    def parse_resp(self, resp):
        return resp[0] == RESPONSE_NEUTRAL


class CmdAuth(AbstractCommand):
    CODE = 0xff

    def __init__(self, key):
        self.key = key

    def to_arr(self):
        return self.key

    def parse_resp(self, resp):
        return resp[0] == RESPONSE_SUCCESS

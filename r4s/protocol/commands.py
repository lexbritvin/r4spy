from r4s.protocol.responses import SuccessResponse, ErrorResponse
from r4s.protocol.responses_kettle import KettleStatus

_DATA_BEGIN_BYTE = 0x55
_DATA_END_BYTE = 0xaa


class RedmondCommand:
    CODE = NotImplemented
    resp_cls = NotImplemented

    @classmethod
    def wrap(cls, counter, cmd, data):
        result = [_DATA_BEGIN_BYTE, counter, cmd]
        result.extend(data)
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
        return self.resp_cls.from_bytes()

    def parse_resp(self, resp):
        return self.resp_cls.from_bytes(resp)


class CmdFw(RedmondCommand):
    CODE = 1

    def parse_resp(self, resp):
        return resp


class Cmd3On(RedmondCommand):
    CODE = 3
    resp_cls = SuccessResponse


class Cmd4Off(RedmondCommand):
    CODE = 4
    resp_cls = SuccessResponse


class Cmd5SetMode(RedmondCommand):
    CODE = 5
    resp_cls = SuccessResponse

    def __init__(self, mode, temp, boil_time):
        self.status = KettleStatus(
            mode=mode,
            trg_temp=temp,
            boil_time=boil_time
        )

    def to_arr(self):
        return self.status.to_arr()


class Cmd6Status(RedmondCommand):
    CODE = 6

    def parse_resp(self, resp):
        return KettleStatus.from_bytes(resp)


class Cmd62SwitchSound(RedmondCommand):
    CODE = 60
    resp_cls = SuccessResponse

    def __init__(self, state):
        self.state = state

    def to_arr(self):
        return [int(self.state)]


class Cmd62SwitchLock(RedmondCommand):
    CODE = 62
    resp_cls = SuccessResponse

    def __init__(self, state):
        self.state = state

    def to_arr(self):
        return [int(self.state)]


class CmdSync(RedmondCommand):
    CODE = 110
    resp_cls = ErrorResponse

    def __init__(self, timezone=4):
        # TODO: Get real timezone.
        from datetime import datetime
        self.now = (int(datetime.now().timestamp()), 4)
        self.tmz = (timezone * 3600, 4)

    def to_arr(self):
        return [self.now, self.tmz]


class CmdAuth(RedmondCommand):
    CODE = 255
    resp_cls = SuccessResponse

    def __init__(self, key):
        self.key = key

    def to_arr(self):
        return self.key

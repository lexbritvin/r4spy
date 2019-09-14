RESPONSE_SUCCESS = 0x01
RESPONSE_FAIL = 0x00
RESPONSE_NEUTRAL = 0x00


class RedmondResponse:

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            # don't attempt to compare against unrelated types.
            return NotImplemented
        for attr, value in self.__dict__.items():
            if getattr(other, attr) != value:
                return False
        return True

    @classmethod
    def from_bytes(cls, data: list):
        raise NotImplemented

    def to_arr(self):
        raise NotImplemented


class SuccessResponse(RedmondResponse):

    def __init__(self, ok: bool):
        self.ok: bool = ok

    @classmethod
    def from_bytes(cls, data: list):
        return cls(bool(data[0]))

    def to_arr(self):
        return [0x01 if self.ok else 0x00]


class ErrorResponse(RedmondResponse):

    def __init__(self, err: int):
        self.err = err

    @classmethod
    def from_bytes(cls, data: list):
        return cls(data[0])

    def to_arr(self):
        return [self.err]


class VersionResponse(RedmondResponse):

    def __init__(self, version: list):
        self.version = version

    @classmethod
    def from_bytes(cls, data: list):
        return cls(data[0:2])

    def to_arr(self):
        return self.version

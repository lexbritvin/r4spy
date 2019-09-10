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
    def from_bytes(cls, data):
        return NotImplemented

    def to_arr(self):
        return NotImplemented


class SuccessResponse(RedmondResponse):

    def __init__(self, ok):
        self.ok = ok

    @classmethod
    def from_bytes(cls, data):
        return cls(bool(data[0]))

    def to_arr(self):
        return [0x01 if self.ok else 0x00]


class ErrorResponse(RedmondResponse):

    def __init__(self, err):
        self.err = err

    @classmethod
    def from_bytes(cls, data):
        return cls(bool(data[0]))

    def to_arr(self):
        return [0x01 if self.err else 0x00]


class VersionResponse(RedmondResponse):

    def __init__(self, version):
        self.version = version

    @classmethod
    def from_bytes(cls, data):
        return cls(data[0:2])

    def to_arr(self):
        return self.version

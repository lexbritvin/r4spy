RESPONSE_SUCCESS = 0x01
RESPONSE_FAIL = 0x00
RESPONSE_NEUTRAL = 0x00


class AbstractResponse:

    @classmethod
    def from_bytes(cls, data):
        return NotImplemented

    def to_arr(self):
        return NotImplemented




class SuccessResponse(AbstractResponse):

    def __init__(self, ok):
        self.ok = ok

    @classmethod
    def from_bytes(cls, data):
        return cls(bool(data[0]))

    def to_arr(self):
        return [0x01 if self.ok else 0x00]


class ErrorResponse(AbstractResponse):

    def __init__(self, err):
        self.err = err

    @classmethod
    def from_bytes(cls, data):
        return cls(bool(data[0]))

    def to_arr(self):
        return [0x01 if self.err else 0x00]

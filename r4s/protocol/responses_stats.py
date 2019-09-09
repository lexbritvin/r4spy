from r4s.protocol import int_to_arr, int_from_bytes
from r4s.protocol.responses import AbstractResponse


class TenInformationResponse(AbstractResponse):

    def __init__(self, ten_num, err, work_time, spent_power, relay_turn_on_amount):
        self.ten_num = ten_num
        self.err = err
        self.work_time = work_time
        self.spent_power = spent_power
        self.relay_turn_on_amount = relay_turn_on_amount

    @classmethod
    def from_bytes(cls, data):
        return cls(
            ten_num=data[0],
            err=data[1],
            work_time=int_from_bytes(data[2:6]),
            spent_power=int_from_bytes(data[6:10]),
            relay_turn_on_amount=int_from_bytes(data[10:14]),
        )

    def to_arr(self):
        data = [0] * 14
        data[0] = self.ten_num
        data[1] = self.err
        data[2:6] = int_to_arr(self.work_time, 4)
        data[6:10] = int_to_arr(self.spent_power, 4)
        data[10:14] = int_to_arr(self.relay_turn_on_amount, 4)
        return data


class TurningOnCountResponse(AbstractResponse):

    def __init__(self, err, turning_on_amount):
        self.err = err
        self.turning_on_amount = turning_on_amount

    @classmethod
    def from_bytes(cls, data):
        return cls(
            err=data[2],
            turning_on_amount=int_from_bytes(data[3:7]),
        )

    def to_arr(self):
        data = [0] * 16
        data[2] = self.err
        data[3:7] = int_to_arr(self.turning_on_amount, 4)
        return data

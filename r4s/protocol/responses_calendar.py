from r4s.protocol import int_from_bytes, int_to_arr
from r4s.protocol.responses import RedmondResponse


class EventInCalendarResponse(RedmondResponse):

    def __init__(self, timezone, uid, recurrence_type, repeat_rule, repeat_type, action_type, timestamp):
        self.timezone = timezone
        self.uid = uid
        self.recurrence_type = recurrence_type
        self.repeat_rule = repeat_rule
        self.repeat_type = repeat_type
        self.action_type = action_type
        self.timestamp = timestamp

    def is_enabled(self):
        return self.recurrence_type & 1 == 1

    @classmethod
    def from_bytes(cls, data):
        return cls(
            timezone=int_from_bytes(data[0:4]),
            uid=data[4],
            recurrence_type=data[5],
            repeat_rule=data[6],
            repeat_type=data[7],
            action_type=data[9],
            timestamp=int_from_bytes(data[10:15])
        )

    def to_arr(self):
        data = [0] * 16
        data[0:4] = int_to_arr(self.timezone, 4)
        data[4:7] = [self.uid, self.recurrence_type, self.repeat_rule, self.repeat_type]
        data[9] = self.action_type
        data[10:15] = int_to_arr(self.timestamp, 5)
        return data


class AddEventResponse(RedmondResponse):
    def __init__(self, uid, err):
        self.uid = uid
        self.err = err

    @classmethod
    def from_bytes(cls, data):
        return cls(
            uid=data[0],
            err=data[1],
        )

    def to_arr(self):
        return [self.uid, self.err]


class CalendarInfoResponse(RedmondResponse):
    def __init__(self, version, max_task_count, curr_task_count):
        self.version = version
        self.max_task_count = max_task_count
        self.curr_task_count = curr_task_count

    @classmethod
    def from_bytes(cls, data):
        return cls(
            version=data[0],
            max_task_count=data[1],
            curr_task_count=data[2],
        )

    def to_arr(self):
        return [self.version, self.max_task_count, self.curr_task_count]

from r4s.protocol.commands import AbstractCommand
from r4s.protocol.responses import ErrorResponse
from r4s.protocol.responses_calendar import EventInCalendarResponse, CalendarInfoResponse, AddEventResponse


class Cmd112(AbstractCommand):
    CODE = 112
    resp_cls = EventInCalendarResponse

    def __init__(self, uid):
        self.uid = uid

    def to_arr(self):
        return [self.uid]


class Cmd113(AbstractCommand):
    CODE = 113
    resp_cls = AddEventResponse

    def __init__(self, event: EventInCalendarResponse):
        self.event = event

    def to_arr(self):
        return self.event.to_arr()


class Cmd115(AbstractCommand):
    CODE = 115
    resp_cls = CalendarInfoResponse


class Cmd116DeleteEvent(AbstractCommand):
    CODE = 116
    resp_cls = ErrorResponse

    def __init__(self, uid):
        self.uid = uid

    def to_arr(self):
        return [self.uid]

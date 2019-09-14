from r4s.protocol.redmond.commands import RedmondCommand
from r4s.protocol.redmond.responses import ErrorResponse
from r4s.protocol.redmond.responses_calendar import EventInCalendarResponse, CalendarInfoResponse, AddEventResponse


class Cmd112(RedmondCommand):
    CODE = 112
    resp_cls = EventInCalendarResponse

    def __init__(self, uid):
        self.uid = uid

    def to_arr(self):
        return [self.uid]


class Cmd113(RedmondCommand):
    CODE = 113
    resp_cls = AddEventResponse

    def __init__(self, event: EventInCalendarResponse):
        self.event = event

    def to_arr(self):
        return self.event.to_arr()


class Cmd115(RedmondCommand):
    CODE = 115
    resp_cls = CalendarInfoResponse


class Cmd116DeleteEvent(RedmondCommand):
    CODE = 116
    resp_cls = ErrorResponse

    def __init__(self, uid):
        self.uid = uid

    def to_arr(self):
        return [self.uid]

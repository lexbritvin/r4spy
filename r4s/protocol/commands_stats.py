from r4s.protocol.commands import AbstractCommand
from r4s.protocol.responses_stats import TenInformationResponse, TurningOnCountResponse


class Cmd71StatsUsage(AbstractCommand):
    CODE = 71
    resp_cls = TenInformationResponse

    def to_arr(self):
        return [0x00]


class Cmd80StatsTimes(AbstractCommand):
    CODE = 80
    resp_cls = TurningOnCountResponse

    def to_arr(self):
        return [0x00]

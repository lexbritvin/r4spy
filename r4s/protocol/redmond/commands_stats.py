from r4s.protocol.redmond.commands import RedmondCommand
from r4s.protocol.redmond.responses_stats import TenInformationResponse, TurningOnCountResponse


class Cmd71StatsUsage(RedmondCommand):
    CODE = 71
    resp_cls = TenInformationResponse

    def to_arr(self):
        return [0x00]


class Cmd80StatsTimes(RedmondCommand):
    CODE = 80
    resp_cls = TurningOnCountResponse

    def to_arr(self):
        return [0x00]

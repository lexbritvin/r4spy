from bluepy.btle import Peripheral

from threading import Lock

from r4s.devices.base import RedmondDevice
from r4s.discovery import DeviceBTAttrs
from r4s.protocol.redmond.command.common import CmdFw, Cmd5SetProgram, Cmd3On, Cmd6Status, Cmd4Off, CmdSync
from r4s.protocol.redmond.command.kettle import FullKettle200Program
from r4s.protocol.redmond.command.lights import Cmd51GetLights
from r4s.protocol.redmond.command.statistics import Cmd71StatsUsage, Cmd80StatsTimes
from r4s.protocol.redmond.response.kettle import MODE_BOIL, BOIL_TEMP, BOIL_TIME_MAX, KettleResponse, Kettle200Response
from r4s.protocol.redmond.response.lights import LIGHT_TYPE_BOIL
from r4s.protocol.redmond.response.statistics import TenInformationResponse, TurningOnCountResponse


class RedmondKettle200(RedmondDevice):
    """"
    A class to read data from Mi Flora plant sensors.
    """

    status_resp_cls = Kettle200Response

    def __init__(self, key: bytearray, peripheral: Peripheral, conn_args: tuple, bt_attrs: DeviceBTAttrs):
        """
        Initialize a Mi Flora Poller for the given MAC address.
        """

        super().__init__(key, peripheral, conn_args, bt_attrs)
        self._fw_last_read = None
        self.lock = Lock()

        self.status = None
        self.stats_ten = None
        self.stats_times = None
        self._is_busy = False
        self._cmd_handlers.update({
            Cmd71StatsUsage.CODE: self.handler_cmd_71_stats,
            Cmd80StatsTimes.CODE: self.handler_cmd_80_stats,
            Cmd6Status.CODE: self.handler_cmd_6_status,
        })
        # TODO: Prepare config for lights/backlight. Use current or overwrite.

    def first_connect(self):
        # TODO: Rework is_busy to Lock.
        self._is_busy = True

        # Clear known.
        self._firmware_version = None
        self.status = None
        self.stats_ten = None

        cmds = [
            CmdFw(),
            Cmd71StatsUsage(),
            Cmd80StatsTimes(),
            Cmd51GetLights(LIGHT_TYPE_BOIL),
            CmdSync(),
            Cmd6Status(self.status_resp_cls)
        ]
        self.do_commands(cmds)
        # TODO: Save cache.

    def set_mode(self, on_off, mode=MODE_BOIL, temp=BOIL_TEMP):
        # TODO: Maybe we need to sync after every reconnection to prevent disconnect.
        if on_off:
            boil_time = self.status.boil_time if self.status else -BOIL_TIME_MAX
            program = FullKettle200Program(mode, temp, boil_time)
            cmds = [
                CmdSync(),
                Cmd5SetProgram(program),
                Cmd3On(),
                Cmd6Status(self.status_resp_cls),
            ]
        else:
            cmds = [
                CmdSync(),
                Cmd4Off(),
                Cmd6Status(self.status_resp_cls),
            ]

        self.do_commands(cmds)

    def update_status(self):
        self.do_commands([Cmd6Status(self.status_resp_cls)])
        # TODO: Save cache.

    def handler_cmd_71_stats(self, resp: TenInformationResponse):
        self.stats_ten = resp

    def handler_cmd_80_stats(self, resp: TurningOnCountResponse):
        self.stats_times = resp

    def handler_cmd_6_status(self, resp: KettleResponse):
        self.status = resp


kettles = {
    "RK-M170S": {
        "cls": NotImplemented,
    },
    "RK-M171S": {
        "cls": NotImplemented,
    },
    "RK-M173S": {
        "cls": NotImplemented,
    },
    "RK-G200S": {
        "cls": RedmondKettle200,
    },
    "RK-G200S-A": {
        "cls": NotImplemented,
    },
    "RK-G201S": {
        "cls": RedmondKettle200,
    },
    "RK-G202S": {
        "cls": RedmondKettle200,
    },
    "RK-G203S": {
        "cls": RedmondKettle200,
    },
    "RK-G210S": {
        "cls": RedmondKettle200,
    },
    "RK-G211S": {
        "cls": RedmondKettle200,
    },
    "RK-G240S": {
        "cls": RedmondKettle200,
    },
}

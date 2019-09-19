from bluepy.btle import Peripheral

from r4s.devices.base import RedmondDevice
from r4s.discovery import DeviceBTAttrs
from r4s.protocol.redmond.command.common import CmdFw, Cmd5SetProgram, Cmd3On, Cmd6Status, Cmd4Off, CmdSync
from r4s.protocol.redmond.command.kettle import FullKettle200Program
from r4s.protocol.redmond.command.statistics import Cmd71StatsUsage, Cmd80StatsTimes
from r4s.protocol.redmond.response.kettle import MODE_BOIL, BOIL_TEMP, BOIL_TIME_MAX, KettleResponse, Kettle200Response
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

        self.status = None
        self.stats_ten = None
        self.stats_times = None
        self._cmd_handlers.update({
            Cmd71StatsUsage.CODE: self.handler_cmd_71_stats,
            Cmd80StatsTimes.CODE: self.handler_cmd_80_stats,
            Cmd6Status.CODE: self.handler_cmd_6_status,
        })

    def first_connect(self):
        # Clear known.
        self._firmware_version = None
        self.status = None
        self.stats_ten = None

        self.fetch_firmware()
        self.send_sync()
        self.fetch_statistics()
        self.fetch_status()

    def set_mode(self, mode=MODE_BOIL, temp=BOIL_TEMP, boil_time=None):
        if boil_time is None:
            # Get status to get boil time.
            self.fetch_status()
            boil_time = self.status.boil_time if self.status else -BOIL_TIME_MAX
        # Set program.
        program = FullKettle200Program(mode, temp, boil_time)
        self.do_command(Cmd5SetProgram(program))
        self.fetch_status()

    def switch_on(self):
        self.do_command(Cmd3On())
        self.fetch_status()

    def switch_off(self):
        self.do_command(Cmd4Off())
        self.fetch_status()

    def fetch_status(self):
        self.do_commands([
            Cmd6Status(self.status_resp_cls),
        ])

    def send_sync(self):
        self.do_command(CmdSync())

    def fetch_firmware(self):
        self.do_command(CmdFw())

    def fetch_statistics(self):
        cmds = [
            Cmd71StatsUsage(),
            Cmd80StatsTimes(),
        ]
        self.do_commands(cmds)

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

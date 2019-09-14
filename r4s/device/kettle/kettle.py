from datetime import timedelta

from r4s.device.device import RedmondDevice

from threading import Lock

from r4s.protocol.redmond.command.common import CmdFw, Cmd5SetMode, Cmd3On, Cmd6Status, Cmd4Off, CmdSync
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

    def __init__(self, mac, backend, cache_timeout=600, retries=3, auth_timeout=5, adapter='hci0'):
        """
        Initialize a Mi Flora Poller for the given MAC address.
        """

        super().__init__(mac, backend, cache_timeout, retries, auth_timeout, adapter)
        self._cache = None
        self._cache_timeout = timedelta(seconds=cache_timeout)
        self._last_read = None
        self._fw_last_read = None
        self.ble_timeout = 10
        self.lock = Lock()

        self._available = False
        self.status = None
        self.stats_ten = None
        self.stats_times = None
        self._is_busy = False
        self._is_auth = False
        self._cmd_handlers.update({
            Cmd71StatsUsage.CODE: self.handler_cmd_71_stats,
            Cmd80StatsTimes.CODE: self.handler_cmd_80_stats,
            Cmd6Status.CODE: self.handler_cmd_6_status,
        })

        # TODO: Prepare config for lights/backlight. Use current or overwrite.

    def first_connect(self):
        # TODO: Rework is_busy to Lock.
        self._is_busy = True
        self._iter = 0
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
            cmds = [
                CmdSync(),
                Cmd5SetMode(mode, temp, boil_time),
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

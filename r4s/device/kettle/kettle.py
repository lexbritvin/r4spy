import time
from datetime import datetime, timedelta

from btlewrap.base import BluetoothBackendException

from r4s.device.device import RedmondDevice, _LOGGER

from threading import Lock

from r4s.protocol.commands import CmdFw, Cmd5SetMode, Cmd3On, Cmd6Status, Cmd4Off, CmdSync, CmdAuth
from r4s.protocol.commands_kettle import Cmd51GetLights
from r4s.protocol.commands_stats import Cmd71StatsUsage, Cmd80StatsTimes
from r4s.protocol.responses_kettle import MODE_BOIL, BOIL_TEMP, BOIL_TIME_MAX, LIGHT_TYPE_BOIL


class RedmondKettle(RedmondDevice):
    """"
    A class to read data from Mi Flora plant sensors.
    """

    def __init__(self, mac, backend, cache_timeout=600, retries=3, adapter='hci0'):
        """
        Initialize a Mi Flora Poller for the given MAC address.
        """

        super().__init__(mac, backend, cache_timeout, retries, adapter)
        self._cache = None
        self._cache_timeout = timedelta(seconds=cache_timeout)
        self._last_read = None
        self._fw_last_read = None
        self.retries = retries
        self.ble_timeout = 10
        self.lock = Lock()
        self._firmware_version = None
        # TODO: Make it random on first run.
        self._key = [0xbb, 0xbb, 0xbb, 0xbb, 0xbb, 0xbb, 0xbb, 0xbb]
        self._available = False
        self.status = None
        self.statistics = None
        self._is_busy = False
        self._is_auth = False
        self._time_upd = '00:00'  # Save timestamp

        # TODO: Prepare config for lights/backlight. Use current or overwrite.

    def _try_auth(self, conn):
        i = 0
        cmd_auth = CmdAuth(self._key)
        self._is_auth = False
        while i < self.retries:
            try:
                self._send_subscribe(conn)
                self._do_commands(conn, [cmd_auth])
                if self._is_auth:
                    return
            except BluetoothBackendException:
                # Try again.
                _LOGGER.debug('Auth failed. Attempt no: %s. Trying again.', i + 1)
            time.sleep(5)
            i += 1

    def first_connect(self):
        # TODO: Rework is_busy to Lock.
        self._is_busy = True
        self._iter = 0
        # Clear known.
        self._firmware_version = None
        self.status = None
        self.statistics = None

        with self._bt_interface.connect(self._mac) as conn:
            self._try_auth(conn)
            if not self._is_auth:
                # TODO: Handle next time request.
                self._last_read = datetime.now() - self._cache_timeout + timedelta(seconds=300)
                return

            self._available = True
            # If a sensor doesn't work, wait 5 minutes before retrying
            try:
                cmds = [
                    CmdFw(),
                    Cmd71StatsUsage(),
                    Cmd80StatsTimes(),
                    Cmd51GetLights(LIGHT_TYPE_BOIL),
                    CmdSync(),
                    Cmd6Status()
                ]
                self.do_commands(cmds)
                self._time_upd = time.strftime("%H:%M")

            except BluetoothBackendException as e:
                # TODO: Handle next time request.
                _LOGGER.exception('message')
                self._last_read = datetime.now() - self._cache_timeout + timedelta(seconds=300)
                return False

    def set_mode(self, on_off, mode=MODE_BOIL, temp=BOIL_TEMP):
        # TODO: Maybe we need to sync after every reconnection to prevent disconnect.
        if on_off:
            boil_time = self.status.boil_time if self.status else -BOIL_TIME_MAX
            cmds = [
                CmdSync(),
                Cmd5SetMode(mode, temp, boil_time),
                Cmd3On(),
                Cmd6Status(),
            ]
        else:
            cmds = [
                CmdSync(),
                Cmd4Off(),
                Cmd6Status(),
            ]

        self.run_commands(cmds)

    def update_status(self):
        cmds = [Cmd6Status()]
        with self._bt_interface.connect(self._mac) as conn:
            self._try_auth(conn)
            if not self._is_auth:
                # TODO: Handle next time request.
                self._last_read = datetime.now() - self._cache_timeout + timedelta(seconds=300)
                return

            try:
                self.do_commands(cmds)

            except BluetoothBackendException as e:
                # TODO: Handle next time request.
                _LOGGER.exception('message')
                self._last_read = datetime.now() - self._cache_timeout + timedelta(seconds=300)
                return False

    def run_commands(self, cmds):
        i = 0
        cmd_auth = CmdAuth(self._key)
        self._is_auth = False
        while i < self.retries:
            if i > 0:
                # Sleep before reconnect.
                time.sleep(5)
            with self._bt_interface.connect(self._mac) as conn:
                try:
                    self._send_subscribe()
                    self.do_commands([cmd_auth])
                except BluetoothBackendException:
                    # Try again.
                    _LOGGER.debug('Auth failed. Attempt no: %s. Trying again.', i + 1)

                i += 1
                if not self._is_auth:
                    continue

                try:
                    self.do_commands(cmds)
                    break
                except BluetoothBackendException as e:
                    # TODO: Handle next time request.
                    _LOGGER.exception('message')
                    self._last_read = datetime.now() - self._cache_timeout + timedelta(seconds=300)
                    return False
                break  # Success

    def _process_resp(self, cmd, resp):
        parsed = cmd.parse_resp(resp)
        if CmdAuth.CODE == cmd.CODE:
            self._is_auth = parsed
        elif CmdFw.CODE == cmd.CODE:
            self._firmware_version = parsed
        elif Cmd71StatsUsage.CODE == cmd.CODE:
            self.statistics = parsed
        elif Cmd6Status.CODE == cmd.CODE:
            self.status = parsed

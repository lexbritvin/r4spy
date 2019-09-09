import time
from datetime import datetime, timedelta

from btlewrap.base import BluetoothInterface, BluetoothBackendException

from r4s.protocol.commands import *

import logging
from threading import Lock

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel('DEBUG')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
_LOGGER.addHandler(ch)

_HANDLE_R_CMD = 0x000b
_HANDLE_W_SUBSCRIBE = 0x000c
_HANDLE_W_CMD = 0x000e

_DATA_SUBSCRIBE = [0x01, 0x00]


class RedmondKettle(object):
    """"
    A class to read data from Mi Flora plant sensors.
    """

    def __init__(self, mac, backend, cache_timeout=600, retries=3, adapter='hci0'):
        """
        Initialize a Mi Flora Poller for the given MAC address.
        """

        self._mac = mac
        self._bt_interface = BluetoothInterface(backend, adapter)
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
        self._iter = 0  # int counter
        self._curr_cmd = None
        self._data = None
        # TODO: Prepare config for lights/backlight. Use current or overwrite.

    def _send_subscribe(self, conn):
        # for the newer models a magic number must be written before we can read the current data
        data = bytes(_DATA_SUBSCRIBE)
        conn.write_handle(_HANDLE_W_SUBSCRIBE, data)  # pylint: disable=no-member
        return True

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
                    CmdStatsUsage(),
                    CmdStatsTimes(),
                    CmdUseBacklight(True),
                    CmdGetLights(LIGHT_TYPE_BOIL),
                    CmdSetLights(LIGHT_TYPE_BOIL),
                    CmdSync(),
                    CmdStatus()
                ]
                self._do_commands(conn, cmds)
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
                # CmdSync(),
                CmdSetMode(mode, temp, boil_time),
                CmdOn(),
                CmdStatus(),
            ]
        else:
            cmds = [
                # CmdSync(),
                CmdOff(),
                CmdStatus(),
            ]

        self.run_commands(cmds)

    def update_status(self):
        cmds = [CmdStatus()]
        with self._bt_interface.connect(self._mac) as conn:
            self._try_auth(conn)
            if not self._is_auth:
                # TODO: Handle next time request.
                self._last_read = datetime.now() - self._cache_timeout + timedelta(seconds=300)
                return

            try:
                self._do_commands(conn, cmds)

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
                    self._send_subscribe(conn)
                    self._do_commands(conn, [cmd_auth])
                except BluetoothBackendException:
                    # Try again.
                    _LOGGER.debug('Auth failed. Attempt no: %s. Trying again.', i + 1)

                i += 1
                if not self._is_auth:
                    continue

                try:
                    self._do_commands(conn, cmds)
                    break
                except BluetoothBackendException as e:
                    # TODO: Handle next time request.
                    _LOGGER.exception('message')
                    self._last_read = datetime.now() - self._cache_timeout + timedelta(seconds=300)
                    return False
                break  # Success

    def _do_commands(self, conn, cmds):
        # TODO: Maybe send subscribe every time.
        for cmd in cmds:
            self._send_subscribe(conn)
            resp = self._send_cmd(conn, cmd)
            self._process_resp(cmd, resp)

    def _send_cmd(self, conn, cmd: AbstractCommand):
        # Save cmd to compare on notification handle.
        self._curr_cmd = cmd

        # Write and wait for response in self.handleNotification.
        conn._DATA_MODE_LISTEN = cmd.wrapped(self._iter)
        success = conn.wait_for_notification(_HANDLE_W_CMD, self, 3)
        if not success or self._data is None:
            return None

        # Update counter on success.
        self._inc_counter()

        return self._data

    def _process_resp(self, cmd, resp):
        parsed = cmd.parse_resp(resp)
        if CmdAuth.CODE == cmd.CODE:
            self._is_auth = parsed
        elif CmdFw.CODE == cmd.CODE:
            self._firmware_version = parsed
        elif cmd.CODE in [CmdStatsUsage.CODE, CmdStatsTimes.CODE]:
            self.statistics = self.statistics + parsed if self.statistics is not None else parsed
        elif cmd.CODE == CmdStatus.CODE:
            self.status = parsed

    def handleNotification(self, handle, raw_data):  # pylint: disable=unused-argument,invalid-name
        """ gets called by the bluepy backend when using wait_for_notification
        """
        self._data = None
        if raw_data is None:
            return
        _LOGGER.debug('Received result for cmd "%s" on handle %s: %s', type(self._curr_cmd).__name__,
                      handle, self._format_bytes(raw_data))
        i, cmd, data = AbstractCommand.unwrap(raw_data)
        if i != self._iter or self._curr_cmd.CODE != cmd:
            # It is not the response for the request.
            # TODO: Throw error or something.
            return
        # Save data to process in parent callback.
        self._data = data

    ### additional methods
    def _inc_counter(self):
        self._iter += 1
        if self._iter > 255:
            self._iter = 0

    @staticmethod
    def _format_bytes(raw_data):
        """Prettyprint a byte array."""
        if raw_data is None:
            return 'None'
        return ' '.join([format(c, "02x") for c in raw_data]).upper()

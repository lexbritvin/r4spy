from textwrap import wrap

_HANDLE_R_CMD = 0x000b

_HANDLE_W_SUBSCRIBE = 0x000c
_HANDLE_W_CMD = 0x000e

_DATA_BEGIN_BYTE = 0x55
_DATA_END_BYTE = 0xaa

_DATA_CONNECT = [0x01, 0x00]

_DATA_CMD_AUTH = 0xff
_DATA_CMD_SYNC = 0x6e

_DATA_CMD_SET_LIGHTS = 0x32
_DATA_CMD_GET_LIGHTS = 0x33
_DATA_CMD_USE_BACKLIGHT = 0x37

_DATA_CMD_STATS_USAGE = 0x47
_DATA_CMD_STATS_TIMES = 0x50

_DATA_CMD_FW = 0x01
_DATA_CMD_ON = 0x03
_DATA_CMD_OFF = 0x04
_DATA_CMD_SET_MODE = 0x05
_DATA_CMD_STATUS = 0x06

_DATA_CMD_52 = 0x52  # TODO: Investigate. Body 00. Empty resp.
_DATA_CMD_35 = 0x35  # TODO: Investigate. Body c8. Empty resp.

_DATA_MODE_BOIL = 0x00
_DATA_MODE_HEAT = 0x01
_DATA_MODE_LIGHT = 0x03

import time

from btlewrap.base import BluetoothInterface, BluetoothBackendException
from datetime import datetime, timedelta

from r4s.helper import wrap_send, to_bytes, unwrap_recv, prepare_mode, parse_status

_HANDLE_READ_VERSION_BATTERY = 0x0004

import logging
from threading import Lock

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel('DEBUG')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
_LOGGER.addHandler(ch)


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
        self.battery = None
        # TODO: Make it random on first run.
        self._key = [0xbb, 0xbb, 0xbb, 0xbb, 0xbb, 0xbb, 0xbb, 0xbb]
        self._available = False
        self.status = {}
        self._is_busy = False
        self._is_auth = False
        self._time_upd = '00:00'  # Save timestamp
        self._iter = 0  # int counter
        self._curr_cmd = None
        self._data = None
        # TODO: Prepare config for lights/backlight. Use current or overwrite.

    @staticmethod
    def _format_bytes(raw_data):
        """Prettyprint a byte array."""
        if raw_data is None:
            return 'None'
        return ' '.join([format(c, "02x") for c in raw_data]).upper()

    def first_connect(self):
        self._is_busy = True
        self._iter = 0
        i = 0

        with self._bt_interface.connect(self._mac) as conn:
            while i < self.retries:
                answer = False
                try:
                    self.send_subscribe(conn)
                    if self.send_auth(conn):
                        answer = True
                        break
                except BluetoothBackendException:
                    # Try again.
                    _LOGGER.debug('Auth failed. Attempt no: %s. Trying again.', i + 1)
                time.sleep(1)
                i += 1
            if not answer:
                # TODO: Handle next time request.
                self._last_read = datetime.now() - self._cache_timeout + timedelta(seconds=300)
                return
            self._is_auth = True
            self._available = True
            # If a sensor doesn't work, wait 5 minutes before retrying
            try:
                self.send_get_fw(conn)
                self.send_get_stats(conn)
                self.send_use_backlight(conn)
                self.send_get_lights(conn)
                self.send_set_lights(conn)
                ## TODO: Maybe sync shouldn't be sent often.
                self.send_sync(conn)
                self.send_status(conn)
                self._time_upd = time.strftime("%H:%M")

            except BluetoothBackendException as e:
                # TODO: Handle next time request.
                _LOGGER.exception('message')
                self._last_read = datetime.now() - self._cache_timeout + timedelta(seconds=300)
                return False

    def send_subscribe(self, conn):
        # for the newer models a magic number must be written before we can read the current data
        data = to_bytes(_DATA_CONNECT)
        conn.write_handle(_HANDLE_W_SUBSCRIBE, data)  # pylint: disable=no-member
        return True

    def handleNotification(self, handle, raw_data):  # pylint: disable=unused-argument,invalid-name
        """ gets called by the bluepy backend when using wait_for_notification
        """
        self._data = None
        if raw_data is None:
            return
        _LOGGER.debug('Received result for cmd "%s" on handle %s: %s', self._curr_cmd,
                      handle, self._format_bytes(raw_data))
        i, cmd, data = unwrap_recv(raw_data)
        if i != self._iter or self._curr_cmd != cmd:
            # It is not the response for the request.
            return
        # Save data to process in parent callback.
        self._data = data

    def send_auth(self, conn):
        resp = self.send_cmd(conn, _DATA_CMD_AUTH, self._key)
        if resp is None:
            return False
        status = resp[0]

        return status == 0x01

    def send_get_fw(self, conn):
        resp = self.send_cmd(conn, _DATA_CMD_FW, [])
        if resp is None:
            return False
        # TODO: save fw.
        return resp

    def send_get_stats(self, conn):
        usage = self.send_cmd(conn, _DATA_CMD_STATS_USAGE, [0x00])
        times = self.send_cmd(conn, _DATA_CMD_STATS_TIMES, [0x00])
        if usage is None or times is None:
            return False
        # TODO: Save usage and times.
        watts = int.from_bytes(usage[6:10], 'little')  # watts / h
        work_time = watts / 2200  # Time in h
        on_times = int.from_bytes(times[3:5], 'little')
        return True

    def send_use_backlight(self, conn, onoff=0x01):
        # TODO: Not clear.
        data = [0xc8, 0xc8, onoff]
        resp = self.send_cmd(conn, _DATA_CMD_USE_BACKLIGHT, data)
        if resp is None:
            return False

        return True

    def send_set_lights(self, conn, boil_light=0x00):  # 00 - boil light    01 - backlight
        if boil_light == 0x00:
            scale_light = [0x28, 0x46, 0x64]
        else:
            scale_light = [0x00, 0x32, 0x64]
        rgb1 = [0x00, 0x00, 0xff]
        rgb2 = [0xff, 0x00, 0x00]
        rgb_mid = [0x00, 0xff, 0x00]
        brightness = 0x5e

        # Prepare light data.
        data = [boil_light]  # Boil light. 0x01 backlight.
        data.extend([scale_light[0], brightness])
        data.extend(rgb1)
        data.extend([scale_light[1], brightness])
        data.extend(rgb_mid)
        data.extend([scale_light[2], brightness])
        data.extend(rgb2)
        resp = self.send_cmd(conn, _DATA_CMD_SET_LIGHTS, data)

        if resp is None:
            return False
        return True

    def send_get_lights(self, conn, boil_light=0x00):
        resp = self.send_cmd(conn, _DATA_CMD_GET_LIGHTS, [boil_light])
        if resp is None:
            return False
        # TODO: Save lights
        return True

    def send_sync(self, conn, timezone=4):
        tmz = (timezone * 60 * 60, 2)
        now = (int(time.mktime(datetime.now().timetuple())), 4)
        tmz_sign = 0x00 if timezone >= 0 else 0x01  # TODO: Possibly 0x01 for negative timezone, need to discover.

        # TODO: Unclear.
        data = [tmz, now, tmz_sign, 0x00]
        resp = self.send_cmd(conn, _DATA_CMD_SYNC, data)
        if resp is None:
            return False

        return True

    def send_status(self, conn):
        resp = self.send_cmd(conn, _DATA_CMD_STATUS, [])
        if resp is None:
            return False
        self.status = parse_status(resp)
        return True

    def send_on(self, conn):
        resp = self.send_cmd(conn, _DATA_CMD_ON, [])
        if resp is None:
            return False
        return True

    def send_off(self, conn):
        resp = self.send_cmd(conn, _DATA_CMD_OFF, [])
        if resp is None:
            return False
        return True

    def send_mode(self, conn, mode, temp):
        # Mode: 00 - boil 01 - heat to temp 03 - backlight (boil by default)
        data = prepare_mode({
            'mode': mode,
            'tgtemp': temp,
        })
        resp = self.send_cmd(conn, _DATA_CMD_SET_MODE, data)

        if resp is None:
            return False
        return True

    def send_cmd(self, conn, cmd, data):
        # Save cmd to compare on notification handle.
        self._curr_cmd = cmd

        # Prepare data to send.
        req_data = [self._curr_cmd]
        req_data.extend(data)
        req_data = wrap_send(self._iter, req_data)

        # Write and wait for response in self.handleNotification.
        conn._DATA_MODE_LISTEN = req_data
        success = conn.wait_for_notification(_HANDLE_W_CMD, self, 3)
        if not success or self._data is None:
            return None

        # Update counter on success.
        self.inc_counter()

        return self._data

    ### additional methods
    def inc_counter(self):
        self._iter += 1
        if self._iter >= 255:
            self._iter = 0

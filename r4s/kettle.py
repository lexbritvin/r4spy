from textwrap import wrap

_HANDLE_R_CMD = 0x000b

_HANDLE_W_SUBSCRIBE = 0x000c
_HANDLE_W_CMD = 0x000e

_DATA_CONNECT = [0x01, 0x00]
_DATA_CMD_AUTH = 0xff
_DATA_CMD_STATUS = 0x06
_DATA_CMD_USE_BACKLIGHT = 0x37
_DATA_CMD_SYNC = 0x6e
_DATA_CMD_LIGHTS = 0x32
_DATA_BEGIN_BYTE = 0x55
_DATA_END_BYTE = 0xaa
_DATA_CMD_ON = 0x03
_DATA_CMD_OFF = 0x04
_DATA_CMD_SET_MODE = 0x05
_DATA_MODE_BOIL = 0x00
_DATA_MODE_HEAT = 0x01
_DATA_MODE_LIGHT = 0x03

import time

from btlewrap.base import BluetoothInterface, BluetoothBackendException
from datetime import datetime, timedelta

from r4s.helper import wrap_send, to_bytes, unwrap_recv

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
        self._icon = 'mdi:kettle'
        self._available = False
        self._is_on = False
        self._heatorboil = ''  # may be  '' or 'b' - boil or 'h' - heat to temp
        self._temp = 0

        self._is_busy = False
        self._is_auth = False
        self._status = ''  # may be '' or '00' - OFF or '02' - ON
        self._mode = ''  # may be  '' or '00' - boil or '01' - heat to temp or '03' - backlight
        self._time_upd = '00:00'
        self._iter = 0  # int counter

    def firmware_version(self):
        """Return the firmware version."""
        if (self._firmware_version is None) or \
                (datetime.now() - timedelta(hours=24) > self._fw_last_read):
            self._fw_last_read = datetime.now()
            with self._bt_interface.connect(self._mac) as connection:
                res = connection.read_handle(_HANDLE_READ_VERSION_BATTERY)  # pylint: disable=no-member
                _LOGGER.debug('Received result for handle %s: %s',
                              _HANDLE_READ_VERSION_BATTERY, self._format_bytes(res))
            if res is None:
                self.battery = 0
                self._firmware_version = None
            else:
                self.battery = res[0]
                self._firmware_version = "".join(map(chr, res[2:]))
        return self._firmware_version

    @staticmethod
    def _format_bytes(raw_data):
        """Prettyprint a byte array."""
        if raw_data is None:
            return 'None'
        return ' '.join([format(c, "02x") for c in raw_data]).upper()

    def firstConnect(self):
        self._is_busy = True
        i = 0
        with self._bt_interface.connect(self._mac) as connection:
            while i < self.retries:
                answer = False
                try:
                    if self.sendSubscribe(connection) \
                            and self.sendAuth(connection):
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
                # self.sendSubscribe(connection)
                self.sendUseBackLight(connection)
                self.sendSetLights(connection)
                self.sendSync(connection)
                self.sendStatus(connection)
                self._time_upd = time.strftime("%H:%M")

            except BluetoothBackendException as e:
                # TODO: Handle next time request.
                _LOGGER.exception('message')
                self._last_read = datetime.now() - self._cache_timeout + timedelta(seconds=300)
                return False

    def test_sync(self):
        with self._bt_interface.connect(self._mac) as connection:
            try:
                ## TODO: Check if we can use saved counter and prevent error.
                self.sendSubscribe(connection)
                self.sendAuth(connection)
                self.sendUseBackLight(connection)
                self.sendSetLights(connection)
                self.sendSync(connection)
                self.sendStatus(connection)
                self._time_upd = time.strftime("%H:%M")
            except BluetoothBackendException as e:
                # TODO: Handle next time request.
                _LOGGER.exception('message')
                self._last_read = datetime.now() - self._cache_timeout + timedelta(seconds=300)
                return False

    def sendSubscribe(self, connection):
        # for the newer models a magic number must be written before we can read the current data
        data = to_bytes(_DATA_CONNECT)
        connection.write_handle(_HANDLE_W_SUBSCRIBE, data)  # pylint: disable=no-member
        return True

    def sendAuth(self, connection):
        data = [_DATA_CMD_AUTH]
        data.extend(self._key)
        data = wrap_send(self._iter, data)
        res = connection.write_handle(_HANDLE_W_CMD, data)  # pylint: disable=no-member
        self.inc_counter()
        resp = connection.read_handle(_HANDLE_R_CMD)  # pylint: disable=no-member
        _LOGGER.debug('Received result in %s for handle %s: %s', 'sendAuth',
                      _HANDLE_R_CMD, self._format_bytes(resp))
        iter, cmd, resp = unwrap_recv(resp)
        status = resp[0]

        if status == 0x01:
            answer = True
        else:
            answer = False
        return answer

    def sendUseBackLight(self, connection, onoff=0x01):
        # TODO: Not clear.
        data = [_DATA_CMD_USE_BACKLIGHT, 0xc8, 0xc8, onoff]
        data = wrap_send(self._iter, data)
        connection.write_handle(_HANDLE_W_CMD, data)  # pylint: disable=no-member
        self.inc_counter()
        resp = connection.read_handle(_HANDLE_R_CMD)  # pylint: disable=no-member
        _LOGGER.debug('Received result in %s for handle %s: %s', 'sendUseBackLight',
                      _HANDLE_R_CMD, self._format_bytes(resp))
        # TODO: handle Counter != sent counter
        return True

    def sendSetLights(self, connection, boil_light=0x00):  # 00 - boil light    01 - backlight
        if boil_light == 0x00:
            scale_light = [0x28, 0x46, 0x64]
        else:
            scale_light = [0x00, 0x32, 0x64]
        rgb1 = [0x00, 0x00, 0xff]
        rgb2 = [0xff, 0x00, 0x00]
        rgb_mid = [0x00, 0xff, 0x00]
        brightness = 0x5e
        data = [_DATA_CMD_LIGHTS]
        # Boil light. 0x01 backlight.
        data.append(boil_light)
        data.append(scale_light[0])
        data.append(brightness)
        data.extend(rgb1)
        data.append(scale_light[1])
        data.append(brightness)
        data.extend(rgb_mid)
        data.append(scale_light[2])
        data.append(brightness)
        data.extend(rgb2)
        data = wrap_send(self._iter, data)
        res = connection.write_handle(_HANDLE_W_CMD, data)  # pylint: disable=no-member
        self.inc_counter()
        resp = connection.read_handle(_HANDLE_R_CMD)  # pylint: disable=no-member
        _LOGGER.debug('Received result in %s for handle %s: %s', 'sendSetLights',
                      _HANDLE_R_CMD, self._format_bytes(resp))
        return True

    def sendSync(self, connection, timezone=4):
        ## TODO: Maybe sync shouldn't be sent often.
        tmz = (timezone * 60 * 60, 2)
        now = (int(time.mktime(datetime.now().timetuple())), 4)
        tmz_sign = 0x00 if timezone >= 0 else 0x01  # TODO: Possibly 0x01 for negative timezone, need to discover.

        data = [_DATA_CMD_SYNC, tmz, now]
        # TODO: Unclear.
        data.extend([tmz_sign, 0x00])
        data = wrap_send(self._iter, data)
        res = connection.write_handle(_HANDLE_W_CMD, data)  # pylint: disable=no-member
        # If a sensor doesn't work, wait 5 minutes before retrying
        self.inc_counter()
        resp = connection.read_handle(_HANDLE_R_CMD)  # pylint: disable=no-member
        _LOGGER.debug('Received result in %s for handle %s: %s', 'sendSync',
                      _HANDLE_R_CMD, self._format_bytes(resp))
        return True

    def sendStatus(self, connection):
        data = [_DATA_CMD_STATUS]
        data = wrap_send(self._iter, data)
        res = connection.write_handle(_HANDLE_W_CMD, data)  # pylint: disable=no-member
        self.inc_counter()
        resp = connection.read_handle(_HANDLE_R_CMD)  # pylint: disable=no-member
        _LOGGER.debug('Received result in %s for handle %s: %s', 'sendStatus',
                      _HANDLE_R_CMD, self._format_bytes(resp))
        counter, cmd, data = unwrap_recv(resp)
        status = self.parseStatus(data)
        return True

    def sendOn(self, connection):
        data = [_DATA_CMD_ON]
        data = wrap_send(self._iter, data)
        res = connection.write_handle(_HANDLE_W_CMD, data)  # pylint: disable=no-member
        self.inc_counter()
        resp = connection.read_handle(_HANDLE_R_CMD)  # pylint: disable=no-member
        _LOGGER.debug('Received result in %s for handle %s: %s', 'sendOn',
                      _HANDLE_R_CMD, self._format_bytes(resp))
        return True

    def sendOff(self, connection):
        data = [_DATA_CMD_OFF]
        data = wrap_send(self._iter, data)
        res = connection.write_handle(_HANDLE_W_CMD, data)  # pylint: disable=no-member
        self.inc_counter()
        resp = connection.read_handle(_HANDLE_R_CMD)  # pylint: disable=no-member
        _LOGGER.debug('Received result in %s for handle %s: %s', 'sendOff',
                      _HANDLE_R_CMD, self._format_bytes(resp))
        return True

    def sendMode(self, connection, mode, temp):   # 00 - boil 01 - heat to temp 03 - backlight (boil by default)    temp - in HEX
        data = [_DATA_CMD_SET_MODE]
        data.extend([mode, 0x00, temp])
        data.append((0, 10))
        data.append(0x80) # TODO: Set how much boil
        data.append((0, 2))
        data = wrap_send(self._iter, data)
        res = connection.write_handle(_HANDLE_W_CMD, data)  # pylint: disable=no-member
        self.inc_counter()
        resp = connection.read_handle(_HANDLE_R_CMD)  # pylint: disable=no-member
        _LOGGER.debug('Received result in %s for handle %s: %s', 'sendMode',
                      _HANDLE_R_CMD, self._format_bytes(resp))
        return True

    ### additional methods
    def inc_counter(self):  # counter
        self._iter += 1
        if self._iter >= 100:
            self._iter = 0

    def decToHex(self, num):
        char = str(hex(int(num))[2:])
        if len(char) < 2:
            char = '0' + char
        return char

    def parseStatus(self, data):
        status = {}
        tgtemp = data[2]
        onoff = data[8]
        temp = data[5]
        mode = data[0]
        boil_time_relative = data[13]


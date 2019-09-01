_HANDLE_R_CMD = 0x000b

_HANDLE_W_SUBSCRIBE = 0x000c
_HANDLE_W_CMD = 0x000e

_DATA_CONNECT = [0x01, 0x00]
_DATA_CMD_AUTH = 0xff
_DATA_CMD_STATUS = 0x06
_DATA_CMD_SYNC = 0x6e
_DATA_CMD_LIGHTS = 0x32
_DATA_BEGIN_BYTE = 0x55
_DATA_END_BYTE = 0xaa

import time

from btlewrap.base import BluetoothInterface, BluetoothBackendException
from datetime import datetime, timedelta

from r4s.helper import wrap_send, to_bytes, unwrap_recv

_HANDLE_READ_VERSION_BATTERY = 0x0004


import logging
from threading import Lock
_LOGGER = logging.getLogger(__name__)



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
        self._avialible = False
        self._is_on = False
        self._heatorboil = '' #may be  '' or 'b' - boil or 'h' - heat to temp
        self._temp = 0

        self._is_busy = False
        self._is_auth = False
        self._status = '' #may be '' or '00' - OFF or '02' - ON
        self._mode = '' #may be  '' or '00' - boil or '01' - heat to temp or '03' - backlight
        self._time_upd = '00:00'
        self._iter = 0 # int counter

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
        iter = 0
        while iter < 5:  # 5 attempts to auth
            answer = False
            if self.sendSubscribe():
                if self.sendAuth():
                    answer = True
                    break
            time.sleep(1)
            iter += 1
        if answer:
            self._is_auth = True
            self._available = True
            # if self.sendUseBackLight():
            #     if self.sendSetLights():
            #         if self.sendSync():
            #             if self.sendStatus():
            #                 self._time_upd = time.strftime("%H:%M")

    def sendSubscribe(self):
        # TODO: Check firmware version.
        with self._bt_interface.connect(self._mac) as connection:
            # for the newer models a magic number must be written before we can read the current data
            try:
                data = to_bytes(_DATA_CONNECT)
                connection.write_handle(_HANDLE_W_SUBSCRIBE, data)  # pylint: disable=no-member
                # If a sensor doesn't work, wait 5 minutes before retrying
            except BluetoothBackendException:
                self._last_read = datetime.now() - self._cache_timeout + \
                                  timedelta(seconds=300)
                return False

            return True

    def sendAuth(self):
        with self._bt_interface.connect(self._mac) as connection:
            # for the newer models a magic number must be written before we can read the current data
            try:
                data = [_DATA_CMD_AUTH]
                data.extend(self._key)
                data = wrap_send(self._iter, data)
                res = connection.write_handle(_HANDLE_W_CMD, data)  # pylint: disable=no-member
                self.iterase()
                # If a sensor doesn't work, wait 5 minutes before retrying
            except BluetoothBackendException:
                self._last_read = datetime.now() - self._cache_timeout + \
                                  timedelta(seconds=300)
                return
            resp = connection.read_handle(_HANDLE_R_CMD)  # pylint: disable=no-member
            iter, cmd, resp = unwrap_recv(resp)
            status = resp[0]

            if status == 0x01:
                answer = True
            else:
                answer = False
            return answer



    def sendUseBackLight(self, onoff=0x01):
        with self._bt_interface.connect(self._mac) as connection:
            # for the newer models a magic number must be written before we can read the current data
            try:
                # TODO: Not clear.
                data = [0x37, 0xc8, 0xc8]
                data.append(onoff)
                data = wrap_send(self._iter, data)
                res = connection.write_handle(_HANDLE_W_CMD, data)  # pylint: disable=no-member
                self.iterase()
                # If a sensor doesn't work, wait 5 minutes before retrying
            except BluetoothBackendException:
                self._last_read = datetime.now() - self._cache_timeout + \
                                  timedelta(seconds=300)
                return False
            status = connection.read_handle(_HANDLE_R_CMD)  # pylint: disable=no-member
            return True

    def sendSetLights(self, boilOrLight = 0x00): # 00 - boil light    01 - backlight
        if boilOrLight == 0x00:
            scale_light = [0x28, 0x46, 0x64]
        else:
            scale_light = [0x00, 0x32, 0x64]
        rgb1 = [0x00, 0x00, 0xff]
        rgb2 = [0xff, 0x00, 0x00]
        rgb_mid = [0x00, 0xff, 0x00]
        brightness = 0x5e
        with self._bt_interface.connect(self._mac) as connection:
            # for the newer models a magic number must be written before we can read the current data
            try:
                data = [_DATA_CMD_LIGHTS]
                # Boil light. 0x01 backlight.
                data.append(boilOrLight)
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
                self.iterase()
                # If a sensor doesn't work, wait 5 minutes before retrying
            except BluetoothBackendException:
                self._last_read = datetime.now() - self._cache_timeout + \
                                  timedelta(seconds=300)
                return False
            status = connection.read_handle(_HANDLE_R_CMD)  # pylint: disable=no-member
            return True

    def sendSync(self, timezone = 4):
        tmz_hex = reversed(hex(int(timezone * 60 * 60)))
        timeNow_hex = reversed(hex(int(time.mktime(datetime.now().timetuple()))))

        with self._bt_interface.connect(self._mac) as connection:
            # for the newer models a magic number must be written before we can read the current data
            try:
                data = [_DATA_CMD_SYNC]
                data.extend(tmz_hex)
                data.extend(timeNow_hex)
                # TODO: Unclear.
                data.extend([0x00, 0x00])
                data = wrap_send(self._iter, data)
                res = connection.write_handle(_HANDLE_W_CMD, data)  # pylint: disable=no-member
                # If a sensor doesn't work, wait 5 minutes before retrying
                self.iterase()
            except BluetoothBackendException:
                self._last_read = datetime.now() - self._cache_timeout + \
                                  timedelta(seconds=300)
                return False
            status = connection.read_handle(_HANDLE_R_CMD)  # pylint: disable=no-member
            return True

    def sendStatus(self):
        with self._bt_interface.connect(self._mac) as connection:
            # for the newer models a magic number must be written before we can read the current data
            try:
                data = [_DATA_CMD_STATUS]
                data = wrap_send(self._iter, data)
                res = connection.write_handle(_HANDLE_W_CMD, data)  # pylint: disable=no-member
                # If a sensor doesn't work, wait 5 minutes before retrying
                self.iterase()
            except BluetoothBackendException:
                self._last_read = datetime.now() - self._cache_timeout + \
                                  timedelta(seconds=300)
                return False
            status = connection.read_handle(_HANDLE_R_CMD)  # pylint: disable=no-member
            return True

        answ = False
        try:
            self.child.sendline("char-write-req 0x000e 55" + self.decToHex(self._iter) + "06aa") # status of device
            self.child.expect("value: ")
            self.child.expect("\r\n")
            statusStr = self.child.before[0:].decode("utf-8") # answer from device example 55 xx 06 00 00 00 00 01 2a 1e 00 00 00 00 00 00 80 00 00 aa
            answer = statusStr.split()
            self._status = str(answer[11])
            self._temp = self.hexToDec(str(answer[8]))
            self._mode = str(answer[3])
            tgtemp = str(answer[5])
            if tgtemp != '00':
                self._tgtemp = self.hexToDec(tgtemp)
            else:
                self._tgtemp = 100
            if self._mode == '00':
                self._heatorboil = 'b'
            elif self._mode == '01':
                self._heatorboil = 'h'
            else:
                self._heatorboil = ''
            if self._status == '02' and self._heatorboil != '':
                self._is_on = True
            else:
                self._is_on = False
            self.child.expect(r'\[LE\]>')
            self.iterase()
            answ = True
        except:
            answ = False
            _LOGGER.error('error sendStatus')
        return answ

    ### additional methods
    def iterase(self):  # counter
        self._iter += 1
        if self._iter >= 100:
            self._iter = 0

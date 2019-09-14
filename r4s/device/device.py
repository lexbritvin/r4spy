import time

from r4s.protocol.redmond.command.common import RedmondCommand, CmdAuth, CmdFw
from btlewrap.base import BluetoothInterface, BluetoothBackendException
import logging

from r4s.protocol.redmond.response.common import SuccessResponse, VersionResponse

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel('DEBUG')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
_LOGGER.addHandler(ch)

## TODO: Use UUID.
_UUID_SRV_R4S = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"
_UUID_SRV_GENERIC = 0x1800
_UUID_CHAR_GENERIC = 0x2a00
_UUID_CHAR_CONN = 0x2a04
_UUID_CCCD = "00002902-0000-1000-8000-00805f9b34fb"
_UUID_CHAR_CMD = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"
_UUID_CHAR_RSP = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"

_HANDLE_R_CMD = 0x000b
_HANDLE_W_SUBSCRIBE = 0x000c  # TODO: Name it CCCD.
_HANDLE_W_CMD = 0x000e

_GATT_ENABLE_NOTIFICATION = [0x01, 0x00]


class RedmondDevice:
    status_resp_cls = NotImplemented

    def __init__(self, mac, backend, cache_timeout=600, retries=3, auth_timeout=5, adapter='hci0'):
        # Bluetooth config.
        self._mac = mac
        self._bt_interface = BluetoothInterface(backend, adapter, address_type='random')

        # TODO: Replace hardcoded values.
        self.cmd_handle = _HANDLE_W_CMD
        self.ccc_handle = _HANDLE_W_SUBSCRIBE
        self.device_name = "RK-G200S"

        self._conn = None
        self._backend = None

        # TODO: Make it random on first run.
        self._is_auth = False
        self._firmware_version = None
        self._key = [0xbb, 0xbb, 0xbb, 0xbb, 0xbb, 0xbb, 0xbb, 0xbb]
        self.retries = retries
        self.auth_timeout = auth_timeout
        self._iter = 0  # int counter
        self._curr_cmd = None
        self._data = None
        self._cmd_handlers = {
            CmdAuth.CODE: self.handler_cmd_auth,
            CmdFw.CODE: self.handler_cmd_fw,
        }

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def __del__(self):
        self.disconnect()

    def connect(self):
        self._conn = self._bt_interface.connect(self._mac)
        self._backend = self._conn.__enter__()
        # TODO: Finish
        # self.discover_device()

        #  Connection interval min 18, max 38, timeout 50. x1.25ms
        if not self._try_auth():
            self.disconnect()
            raise BluetoothBackendException('could not authenticate')
        # TODO: Do internal staff like characteristics read and auth.
        # TODO: Check connection is not reset.
        return self._backend

    def discover_device(self):
        # TODO: Provide patch to btlewrap.
        services = self._backend.services()
        r4s_service = self.get_prop_by_uuid(services, _UUID_SRV_R4S)
        if r4s_service is None:
            raise BluetoothBackendException('unsupported device')
        generic_srv = self.get_prop_by_uuid(services, _UUID_SRV_GENERIC)
        generic_chars = generic_srv.getCharacteristics()

        chars = r4s_service.getCharacteristics()
        desc = r4s_service.getDescriptors()
        device_name_char = self.get_prop_by_uuid(generic_chars, _UUID_CHAR_GENERIC)
        conn_params_char = self.get_prop_by_uuid(generic_chars, _UUID_CHAR_CONN)
        cmd_char = self.get_prop_by_uuid(chars, _UUID_CHAR_CMD)
        cccd = self.get_prop_by_uuid(desc, _UUID_CCCD)

        self.device_name = self._backend.read_handle(device_name_char.valHandle)
        conn_params = self._backend.read_handle(conn_params_char.valHandle)
        min_conn, max_conn, lat, timeout = conn_params[0:2], conn_params[2:4], conn_params[4:6], conn_params[6:8]

        # TODO: Init it better.
        self.device_name_handle = device_name_char.valHandle
        self.conn_param_handle = conn_params_char.valHandle
        self.cmd_handle = cmd_char.valHandle
        self.ccc_handle = cccd.valHandle

    def get_prop_by_uuid(self, objs, uuid):
        for el in objs:
            if el.uuid == uuid:
                return el
        return None

    def disconnect(self):
        try:
            if self._conn is not None:
                self._conn.__del__()
            self._conn = None
            self._backend = None
            self._is_auth = False
        except AttributeError:
            pass

    def _try_auth(self):
        i = 0
        cmd_auth = CmdAuth(self._key)
        self._is_auth = False
        while i < self.retries:
            try:
                self._send_subscribe()
                self.do_command(cmd_auth)
                if self._is_auth:
                    return True
            except BluetoothBackendException:
                # Try again.
                _LOGGER.debug('Auth failed. Attempt no: %s. Trying again.', i + 1)
            time.sleep(self.auth_timeout)
            i += 1

        return False

    def _send_subscribe(self):
        # for the newer models a magic number must be written before we can read the current data
        data = bytes(_GATT_ENABLE_NOTIFICATION)
        self._backend.write_handle(self.ccc_handle, data)  # pylint: disable=no-member
        return True

    def do_command(self, cmd):
        resp = self._send_cmd(cmd)
        parsed = cmd.parse_resp(resp)
        if cmd.CODE in self._cmd_handlers:
            self._cmd_handlers[cmd.CODE](parsed)
        return parsed

    def do_commands(self, cmds):
        for cmd in cmds:
            self.do_command(cmd)

    def _send_cmd(self, cmd: RedmondCommand):
        if self._backend is None:
            raise BluetoothBackendException('not connected to backend')
        # Save cmd to compare on notification handle.
        self._curr_cmd = cmd

        # Write and wait for response in self.handleNotification.
        ## TODO: Define connection interval.
        self._backend._DATA_MODE_LISTEN = cmd.wrapped(self._iter)
        success = self._backend.wait_for_notification(self.cmd_handle, self, 3)
        if not success or self._data is None:
            return None

        # Update counter on success.
        self._inc_counter()

        return self._data

    def handleNotification(self, handle, raw_data):  # pylint: disable=unused-argument,invalid-name
        """ gets called by the bluepy backend when using wait_for_notification
        """
        self._data = None
        if raw_data is None:
            return
        _LOGGER.debug('Received result for cmd "%s" on handle %s: %s', type(self._curr_cmd).__name__,
                      handle, self._format_bytes(raw_data))
        i, cmd, data = RedmondCommand.unwrap(raw_data)
        if i != self._iter or self._curr_cmd.CODE != cmd:
            # It is not the response for the request.
            # TODO: Throw error or something.
            return
        # Save data to process in parent callback.
        self._data = data

    def handler_cmd_auth(self, resp: SuccessResponse):
        self._is_auth = resp.ok

    def handler_cmd_fw(self, resp: VersionResponse):
        self._firmware_version = resp.version

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

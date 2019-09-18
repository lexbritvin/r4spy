from bluepy.btle import Peripheral, BTLEException
from r4s.discovery import DeviceBTAttrs
from r4s import R4sUnexpectedResponse
from r4s.protocol.redmond.command.common import CmdAuth, CmdFw, RedmondCommand
from r4s.protocol.redmond.response.common import SuccessResponse, VersionResponse

_HANDLE_R_CMD = 0x000b
_HANDLE_W_SUBSCRIBE = 0x000c
_HANDLE_W_CMD = 0x000e

_GATT_ENABLE_NOTIFICATION = [0x01, 0x00]


class RedmondDevice:
    status_resp_cls = NotImplemented
    set_program_cls = NotImplemented

    def __init__(self, key: bytearray, peripheral: Peripheral, conn_args: tuple, bt_attrs: DeviceBTAttrs):
        # Bluetooth config.
        self._peripheral = peripheral
        self._bt_attrs = bt_attrs
        self._conn_args = conn_args

        self._is_auth = False
        self._firmware_version = None
        self._key = key
        self._counter = 0
        self._curr_cmd = None
        self._data = None
        self._cmd_handlers = {
            CmdAuth.CODE: self.handler_cmd_auth,
            CmdFw.CODE: self.handler_cmd_fw,
        }

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def __del__(self):
        self.disconnect()

    def connect(self):
        if self._peripheral._helper is None:
            self._peripheral.connect(*self._conn_args)
        if not self._is_auth:
            self.try_auth()

    def disconnect(self):
        try:
            self._peripheral.disconnect()
        except AttributeError:
            # Sometimes called from __del__.
            pass

    def enable_notifications(self):
        # for the newer models a magic number must be written before we can read the current data
        data = bytes(_GATT_ENABLE_NOTIFICATION)
        self._write_handle(self._bt_attrs.ccc, data)

    def try_auth(self):
        if self._is_auth:
            # Already authenticated.
            return True
        self._is_auth = False
        self._counter = 0
        self.enable_notifications()
        self.do_command(CmdAuth(self._key))
        if self._is_auth:
            return True

        return False

    def do_command(self, cmd):
        # TODO: Catch disconnect and try to reconnect.
        resp = self._send_cmd(cmd)
        parsed = cmd.parse_resp(resp)
        if cmd.CODE in self._cmd_handlers:
            self._cmd_handlers[cmd.CODE](parsed)
        return parsed

    def do_commands(self, cmds: list):
        for cmd in cmds:
            self.do_command(cmd)

    def _write_handle(self, handle, data):
        self._peripheral.writeCharacteristic(handle, data, True)

    def _send_cmd(self, cmd: RedmondCommand):
        if self._peripheral is None:
            raise BTLEException('not connected to backend')
        # Save cmd to compare on notification handle.
        self._curr_cmd = cmd

        # Write and wait for response in self.handleNotification.
        self._write_handle(self._bt_attrs.cmd, cmd.wrapped(self._counter))
        self._peripheral.withDelegate(self)
        notification_timeout = 3
        success = self._peripheral.waitForNotifications(notification_timeout)

        if not success or self._data is None:
            return None

        # Update counter on success.
        self._inc_counter()

        return self._data

    def handleNotification(self, handle, raw_data):
        """ gets called by the bluepy backend when using wait_for_notification
        """
        self._data = None
        if raw_data is None:
            return
        # _LOGGER.debug('Received result for cmd "%s" on handle %s: %s', type(self._curr_cmd).__name__,
        #               handle, self._format_bytes(raw_data))

        i, cmd, data = RedmondCommand.unwrap(raw_data)
        if i != self._counter or self._curr_cmd.CODE != cmd:
            # It is not the response for the request.
            raise R4sUnexpectedResponse()

        # Save data to process in parent callback.
        self._data = data

    def handler_cmd_auth(self, resp: SuccessResponse):
        self._is_auth = resp.ok

    def handler_cmd_fw(self, resp: VersionResponse):
        self._firmware_version = resp.version

    def _inc_counter(self):
        self._counter += 1
        if self._counter > 255:
            self._counter = 0

    @staticmethod
    def _format_bytes(raw_data):
        """Pretty print a byte array."""
        if raw_data is None:
            return 'None'
        return ' '.join([format(c, "02x") for c in raw_data]).upper()

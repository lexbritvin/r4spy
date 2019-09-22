import logging

from r4s.manager import Peripheral
from r4s.discovery import DeviceBTAttrs
from r4s import R4sUnexpectedResponse
from r4s.protocol.redmond.command.common import CmdAuth, CmdFw, RedmondCommand
from r4s.protocol.redmond.response.common import SuccessResponse, VersionResponse

_LOGGER = logging.getLogger(__name__)

_GATT_ENABLE_NOTIFICATION = [0x01, 0x00]


class RedmondDevice:
    """
    Base class for r4s device connection.

    The class handles basic commands and provides layer to communicate with a peripheral.
    """
    status_resp_cls = NotImplemented
    set_program_cls = NotImplemented

    def __init__(self, key: bytearray, peripheral: Peripheral, conn_args: tuple, bt_attrs: DeviceBTAttrs):
        # Bluetooth config.
        self._conn_args = conn_args
        self._peripheral = peripheral
        self._peripheral.withDelegate(self)
        self.bt_attrs = bt_attrs

        self._is_auth = False  # Is authenticated to make requests.
        self._firmware_version = None  # Device firmware.
        self._key = key  # Key to auth.
        self._counter = 0  # Command counter. Used on every request.
        self._curr_cmd = None  # Last command requested.
        self._data = None  # Command response notification data.

        # Command handlers to update instance data.
        self._cmd_handlers = {
            CmdAuth.CODE: self.handler_cmd_auth,
            CmdFw.CODE: self.handler_cmd_fw,
        }

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def __del__(self):
        self.disconnect()

    def connect(self):
        """Connects to a peripheral."""
        self._peripheral.connect(*self._conn_args)

    def disconnect(self):
        """Disconnects from a peripheral and sets related vars."""
        try:
            self._is_auth = False
            self._peripheral.disconnect()
        except AttributeError:
            # Sometimes called from __del__.
            pass

    def enable_notifications(self):
        """Sets client characteristics to receive notifications."""
        data = bytes(_GATT_ENABLE_NOTIFICATION)
        self._write_handle(self.bt_attrs.ccc, data)

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
        """Send request and handle response."""
        # TODO: Catch disconnect and try to reconnect.
        resp = self._send_cmd(cmd)
        if resp is None:
            raise R4sUnexpectedResponse()
        parsed = cmd.parse_resp(resp)
        if cmd.CODE in self._cmd_handlers:
            self._cmd_handlers[cmd.CODE](parsed)
        return parsed

    def do_commands(self, cmds: list):
        """Handle multiple commands."""
        for cmd in cmds:
            self.do_command(cmd)

    def _write_handle(self, handle, data):
        """Helper function send data to a peripheral."""
        self._peripheral.writeCharacteristic(handle, data)

    def _send_cmd(self, cmd: RedmondCommand):
        """Send command and handle notification."""
        # Save cmd to compare on notification handle.
        self._curr_cmd = cmd

        # Write and wait for response in self.handleNotification.
        self._write_handle(self.bt_attrs.cmd, cmd.wrapped(self._counter))
        success = self._peripheral.waitForNotifications(1)

        if not success or self._data is None:
            return None

        # Update counter on success.
        self._inc_counter()

        return self._data

    def handleNotification(self, handle, raw_data):
        """Gets called by the bluepy backend when using waitForNotifications."""
        self._data = None
        if raw_data is None:
            return
        _LOGGER.debug('Received result for cmd "%s" on handle %s: %s', type(self._curr_cmd).__name__,
                      handle, self._format_bytes(raw_data))

        i, cmd, data = RedmondCommand.unwrap(raw_data)
        if i != self._counter or self._curr_cmd.CODE != cmd:
            # It is not the response for the request.
            raise R4sUnexpectedResponse()

        # Save data to process in parent callback.
        self._data = data

    def handler_cmd_auth(self, resp: SuccessResponse):
        """Response handler for auth command."""
        self._is_auth = resp.ok

    def handler_cmd_fw(self, resp: VersionResponse):
        """Response handler for firmware command."""
        self._firmware_version = resp.version

    def _inc_counter(self):
        """Helper method for command counter."""
        self._counter += 1
        if self._counter > 255:
            self._counter = 0

    @staticmethod
    def _format_bytes(raw_data):
        """Pretty print a byte array."""
        if raw_data is None:
            return 'None'
        return ' '.join([format(c, "02x") for c in raw_data]).upper()

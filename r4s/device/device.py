from r4s.protocol.commands import RedmondCommand
from btlewrap.base import BluetoothInterface, BluetoothBackendException
import logging

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel('DEBUG')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
_LOGGER.addHandler(ch)

_HANDLE_R_CMD = 0x000b
_HANDLE_W_SUBSCRIBE = 0x000c
_HANDLE_W_CMD = 0x000e

_GATT_ENABLE_NOTIFICATION = [0x01, 0x00]


class RedmondDevice:

    def __init__(self, mac, backend, cache_timeout=600, retries=3, adapter='hci0'):
        # Bluetooth config.
        self._mac = mac
        self._bt_interface = BluetoothInterface(backend, adapter, address_type='random')
        self._conn = None
        self._backend = None

        self._iter = 0  # int counter
        self._curr_cmd = None
        self._data = None

    def __enter__(self):
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def connect(self):
        self._conn = self._bt_interface.connect(self._mac)
        self._backend = self._conn.__enter__()
        # TODO: Do internal staff like characteristics read and auth.
        return self._backend

    def disconnect(self):
        self._conn.__exit__()
        self._backend = None

    def _send_subscribe(self):
        # for the newer models a magic number must be written before we can read the current data
        data = bytes(_GATT_ENABLE_NOTIFICATION)
        self._backend.write_handle(_HANDLE_W_SUBSCRIBE, data)  # pylint: disable=no-member
        return True

    def do_command(self, cmd):
        resp = self._send_cmd(cmd)
        self._process_resp(cmd, resp)

    def do_commands(self, cmds):
        # TODO: Maybe send subscribe every time.
        # TODO: Check connection is not reset.
        for cmd in cmds:
            self.do_command(cmd)

    def _send_cmd(self, cmd: RedmondCommand):
        if self._backend is None:
            raise BluetoothBackendException('not connected to backend')
        # Save cmd to compare on notification handle.
        self._curr_cmd = cmd

        # Write and wait for response in self.handleNotification.
        self._backend._DATA_MODE_LISTEN = cmd.wrapped(self._iter)
        success = self._backend.wait_for_notification(_HANDLE_W_CMD, self, 3)
        if not success or self._data is None:
            return None

        # Update counter on success.
        self._inc_counter()

        return self._data

    def _process_resp(self, cmd, resp):
        return NotImplemented

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

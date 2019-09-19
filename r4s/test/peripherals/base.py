"""Helpers for test cases."""

from r4s.discovery import UUID_CHAR_GENERIC, UUID_CHAR_CMD, UUID_CHAR_RSP, UUID_CCCD, UUID_SRV_GENERIC, UUID_SRV_R4S
from r4s.protocol.redmond.command.common import CmdAuth, CmdFw, CmdSync, Cmd6Status, Cmd5SetProgram, Cmd3On, Cmd4Off, \
    RedmondCommand
from r4s.protocol.redmond.response.common import SuccessResponse, ErrorResponse
from r4s.protocol.redmond.response.kettle import STATE_ON, STATE_OFF
from r4s.test.bluepy_helper import *

_HANDLE_R_GENERIC = 0x0003
_HANDLE_R_CMD = 0x000b
_HANDLE_W_SUBSCRIBE = 0x000c
_HANDLE_W_CMD = 0x000e


class MockPeripheral:
    """Bluepy mock peripheral.

    Base class for all mock peripherals.
    The behaviour of all implementations is based on the knowledge of the peripheral.
    The behaviour can be wrong.
    """

    def __init__(self, deviceAddr=None, addrType=ADDR_TYPE_PUBLIC, iface=None):
        self.delegate = None
        self._serviceMap = None  # Indexed by UUID
        (self.deviceAddr, self.addrType, self.iface) = (None, None, None)

        # Read handlers.
        self.cmd_responses = []
        self.override_read_handles = {
            _HANDLE_R_GENERIC: self.get_device_name,
            _HANDLE_R_CMD: self.cmd_handle_read,
        }

        # Write handlers.
        self.written_handles = []
        self.override_write_handles = {
            _HANDLE_W_SUBSCRIBE: self.cccd_handle_write,
            _HANDLE_W_CMD: self.cmd_handle_write,
        }

        # Write cmd handlers.
        self.cmd_handlers = {
            CmdAuth.CODE: self.cmd_auth,
            CmdFw.CODE: self.cmd_fw,
            CmdSync.CODE: self.cmd_sync,
            Cmd6Status.CODE: self.cmd_status,
            Cmd5SetProgram.CODE: self.cmd_set_mode,
            Cmd3On.CODE: self.cmd_on,
            Cmd4Off.CODE: self.cmd_off,
        }

        # Current state.
        self.is_available = True
        self.is_connected = False
        self.ready_to_pair = False
        self.is_subscribed = False
        self.is_authed = False
        self.auth_keys = set()
        self.auth_keys.add(bytes([0xbb] * 8))
        self.counter = 0

        # Internal status. Firmware version.
        self.device_cls = NotImplemented
        self.fw_version = NotImplemented
        self.status = NotImplemented

        if deviceAddr is not None:
            self.connect(deviceAddr, addrType, iface)

    def __del__(self):
        self.disconnect()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.disconnect()

    def get_device_name(self):
        """Returns device name for generic service."""
        raise NotImplemented

    def connect(self, addr, addrType=ADDR_TYPE_PUBLIC, iface=None):
        """Imitate connect."""
        if self.is_connected:
            ValueError('cannot have more than 1 connection')
        self.is_connected = True

    def disconnect(self):
        """Imitate disconnect."""
        if not self.is_connected:
            ValueError('cannot disconnect when not connected')
        self.is_connected = False
        self.is_subscribed = False
        self.is_authed = None

    def check_connected(self):
        """helper function to check if the request can be processed."""
        if not self.is_connected:
            raise ValueError('Not connected')
        return True

    def discoverServices(self):
        """Mock bluetooth services."""
        return {
            UUID(UUID_SRV_GENERIC): Service(
                self, UUID_SRV_GENERIC, 1, 7
            ),
            UUID(UUID_SRV_R4S): Service(
                self, UUID_SRV_R4S, 9, 14,
            ),
        }

    def getServiceByUUID(self, uuidVal):
        """Returns service by uuid."""
        uuid = UUID(uuidVal)
        services = self.discoverServices()
        if uuid in services:
            return services[uuid]
        raise BTLEGattError("Service %s not found" % uuid)

    def getCharacteristics(self, startHnd=1, endHnd=0xFFFF, uuid=None):
        """Mock bluetooth characteristics."""
        return [
            Characteristic(self, UUID_CHAR_GENERIC, _HANDLE_R_GENERIC - 1, 2, _HANDLE_R_GENERIC),
            Characteristic(self, UUID_CHAR_CMD, _HANDLE_W_CMD - 1, 12, _HANDLE_W_CMD),
            Characteristic(self, UUID_CHAR_RSP, _HANDLE_R_CMD - 1, 16, _HANDLE_R_CMD),
        ]

    def getDescriptors(self, startHnd=1, endHnd=0xFFFF):
        """Mock bluetooth descriptors."""
        return [
            Descriptor(self, UUID_CCCD, 12),
        ]

    def withDelegate(self, delegate_):
        """Sets delegate for peripheral."""
        self.delegate = delegate_
        return self

    def readCharacteristic(self, handle):
        """Read one of the handles that are implemented."""
        self.check_connected()
        if handle in self.override_read_handles:
            return self.override_read_handles[handle]()
        raise ValueError('handle not implemented in mockup')

    def waitForNotifications(self, timeout):
        """Wait for notification callback."""
        if not self.is_subscribed:
            return False
        resp = self.readCharacteristic(_HANDLE_R_CMD)
        self.delegate.handleNotification(_HANDLE_R_CMD, resp)
        return True

    def writeCharacteristic(self, handle, val, withResponse=False):
        """Writing handles just stores the results in a list."""
        self.check_connected()
        self.written_handles.append((handle, val))

        if handle in self.override_write_handles:
            return self.override_write_handles[handle](val)
        raise ValueError('handle not implemented in mockup')

    """Command handlers."""

    def cmd_handle_read(self):
        """R4S command response characteristic handler."""
        if not self.cmd_responses:
            raise ValueError('no writes were registered')

        # Pop the latest response.
        counter, cmd, data = self.cmd_responses[-1]
        return RedmondCommand.wrap(counter, cmd, data)

    def cccd_handle_write(self, value):
        """CCCD write handler."""
        self.is_subscribed = True
        return ['wr']

    def cmd_handle_write(self, value):
        """R4S command request characteristic handler."""
        self.counter, cmd, data = RedmondCommand.unwrap(value)
        if not self.is_authed and cmd != CmdAuth.CODE:
            raise ValueError('you are not authorised to send commands')

        if cmd in self.cmd_handlers:
            resp = self.cmd_handlers[cmd](data)
            self.cmd_responses.append((self.counter, cmd, resp))
            return ['wr']

        raise ValueError('cmd not implemented in mockup')

    def check_key(self, key):
        """Checks whether key is valid and registered."""
        if len(key) != 8:
            raise ValueError('Auth key is not 8 bytes long.')
        return bytes(key) in self.auth_keys

    def cmd_auth(self, data):
        """Auth command handler."""
        if self.check_key(data):
            self.is_authed = True
            return SuccessResponse(True).to_arr()

        if not self.ready_to_pair:
            return SuccessResponse(False).to_arr()

        self.is_authed = True
        self.auth_keys.add(bytes(data))
        return SuccessResponse(True).to_arr()

    def cmd_fw(self, data):
        """Firmware command handler."""
        return self.fw_version.to_arr()

    def cmd_sync(self, data):
        """Sync device time handler."""
        # TODO: Save time.
        return ErrorResponse(0).to_arr()

    def cmd_status(self, data):
        """Status command handler."""
        return self.status.to_arr()

    def cmd_set_mode(self, data):
        """Program set command handler."""
        try:
            new_status = self.device_cls.status_resp_cls.from_bytes(data)
        except ValueError:
            return SuccessResponse(False).to_arr()

        # Save mode.
        self.status.program = new_status.program
        self.status.trg_temp = new_status.trg_temp
        self.status.boil_time = new_status.boil_time

        return SuccessResponse(True).to_arr()

    def cmd_on(self, data):
        """Command On handler."""
        # TODO: Return 0x00 on some internal error.
        self.status.state = STATE_ON
        return SuccessResponse(True).to_arr()

    def cmd_off(self, data):
        """Command Off handler."""
        # TODO: Return 0x00 on some internal error.
        self.status.state = STATE_OFF
        return SuccessResponse(True).to_arr()

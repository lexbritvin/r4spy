"""Helpers for test cases."""
import binascii

from r4s.discovery import UUID_CHAR_GENERIC, UUID_CHAR_CMD, UUID_CHAR_RSP, UUID_CCCD, UUID_SRV_GENERIC, UUID_SRV_R4S
from r4s.protocol.redmond.command.common import CmdAuth, CmdFw, CmdSync, Cmd6Status, Cmd5SetProgram, Cmd3On, Cmd4Off, \
    RedmondCommand
from r4s.protocol.redmond.response.common import SuccessResponse, ErrorResponse
from r4s.protocol.redmond.response.kettle import STATE_ON, STATE_OFF

ADDR_TYPE_PUBLIC = "public"
ADDR_TYPE_RANDOM = "random"

_HANDLE_R_GENERIC = 0x0003
_HANDLE_R_CMD = 0x000b
_HANDLE_W_SUBSCRIBE = 0x000c
_HANDLE_W_CMD = 0x000e


class MockPeripheral:

    def __init__(self, deviceAddr=None, addrType=ADDR_TYPE_PUBLIC, iface=None):
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
            _HANDLE_W_SUBSCRIBE: self.subscribe_handle_write,
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
        raise NotImplemented

    def connect(self, addr, addrType=ADDR_TYPE_PUBLIC, iface=None):
        if self.is_connected:
            ValueError('cannot have more than 1 connection')
        self.is_connected = True

    def disconnect(self):
        if not self.is_connected:
            ValueError('cannot disconnect when not connected')
        self.is_connected = False
        self.is_subscribed = False
        self.is_authed = None

    def check_connected(self):
        if not self.is_connected:
            raise ValueError('Not connected')
        return True

    def discoverServices(self):
        return {
            UUID(UUID_SRV_GENERIC): Service(
                self, UUID_SRV_GENERIC, 1, 7
            ),
            UUID(UUID_SRV_R4S): Service(
                self, UUID_SRV_R4S, 9, 14,
            ),
        }

    def getServiceByUUID(self, uuidVal):
        pass

    def getCharacteristics(self, startHnd=1, endHnd=0xFFFF, uuid=None):
        return [
            Characteristic(self, UUID_CHAR_GENERIC, _HANDLE_R_GENERIC -1, 2, _HANDLE_R_GENERIC),
            Characteristic(self, UUID_CHAR_CMD, _HANDLE_W_CMD - 1, 12, _HANDLE_W_CMD),
            Characteristic(self, UUID_CHAR_RSP, _HANDLE_R_CMD - 1, 16, _HANDLE_R_CMD),
        ]

    def getDescriptors(self, startHnd=1, endHnd=0xFFFF):
        return [
            Descriptor(self, UUID_CCCD, 12),
        ]

    def withDelegate(self, delegate_):
        self.delegate = delegate_
        return self

    def readCharacteristic(self, handle):
        self.check_connected()
        """Read one of the handles that are implemented."""
        if handle in self.override_read_handles:
            return self.override_read_handles[handle]()
        raise ValueError('handle not implemented in mockup')

    def waitForNotifications(self, timeout):
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

    # Command handlers.

    def cmd_handle_read(self):
        if not self.cmd_responses:
            raise ValueError('no writes were registered')

        # Pop the latest response.
        counter, cmd, data = self.cmd_responses[-1]
        return RedmondCommand.wrap(counter, cmd, data)

    def subscribe_handle_write(self, value):
        self.is_subscribed = True
        return ['wr']

    def cmd_handle_write(self, value):
        self.counter, cmd, data = RedmondCommand.unwrap(value)
        if not self.is_authed and cmd != CmdAuth.CODE:
            raise ValueError('you are not authorised to send commands')

        if cmd in self.cmd_handlers:
            resp = self.cmd_handlers[cmd](data)
            self.cmd_responses.append((self.counter, cmd, resp))
            return ['wr']

        raise ValueError('cmd not implemented in mockup')

    def check_key(self, key):
        if len(key) != 8:
            raise ValueError('Auth key is not 8 bytes long.')
        return bytes(key) in self.auth_keys

    def cmd_auth(self, data):
        if self.check_key(data):
            self.is_authed = True
            return SuccessResponse(True).to_arr()

        if not self.ready_to_pair:
            return SuccessResponse(False).to_arr()

        self.is_authed = True
        self.auth_keys.add(bytes(data))
        return SuccessResponse(True).to_arr()

    def cmd_fw(self, data):
        return self.fw_version.to_arr()

    def cmd_sync(self, data):
        # TODO: Save time.
        return ErrorResponse(0).to_arr()

    def cmd_status(self, data):
        return self.status.to_arr()

    def cmd_set_mode(self, data):
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
        # TODO: Return 0x00 on some internal error.
        self.status.state = STATE_ON
        return SuccessResponse(True).to_arr()

    def cmd_off(self, data):
        # TODO: Return 0x00 on some internal error.
        self.status.state = STATE_OFF
        return SuccessResponse(True).to_arr()


class BTLEException(Exception):
    """Base class for all Bluepy exceptions"""
    def __init__(self, message, resp_dict=None):
        self.message = message

        # optional messages from bluepy-helper
        self.estat = None
        self.emsg = None
        if resp_dict:
            self.estat = resp_dict.get('estat',None)
            if isinstance(self.estat,list):
                self.estat = self.estat[0]
            self.emsg = resp_dict.get('emsg',None)
            if isinstance(self.emsg,list):
                self.emsg = self.emsg[0]


    def __str__(self):
        msg = self.message
        if self.estat or self.emsg:
            msg = msg + " ("
            if self.estat:
                msg = msg + "code: %s" % self.estat
            if self.estat and self.emsg:
                msg = msg + ", "
            if self.emsg:
                msg = msg + "error: %s" % self.emsg
            msg = msg + ")"

        return msg


class UUID:
    def __init__(self, val, commonName=None):
        """We accept: 32-digit hex strings, with and without '-' characters,
           4 to 8 digit hex strings, and integers"""
        if isinstance(val, int):
            if (val < 0) or (val > 0xFFFFFFFF):
                raise ValueError(
                    "Short form UUIDs must be in range 0..0xFFFFFFFF")
            val = "%04X" % val
        elif isinstance(val, self.__class__):
            val = str(val)
        else:
            val = str(val)  # Do our best

        val = val.replace("-", "")
        if len(val) <= 8:  # Short form
            val = ("0" * (8 - len(val))) + val + "00001000800000805F9B34FB"

        self.binVal = binascii.a2b_hex(val.encode('utf-8'))
        if len(self.binVal) != 16:
            raise ValueError(
                "UUID must be 16 bytes, got '%s' (len=%d)" % (val,
                                                              len(self.binVal)))
        self.commonName = commonName

    def __str__(self):
        s = binascii.b2a_hex(self.binVal).decode('utf-8')
        return "-".join([s[0:8], s[8:12], s[12:16], s[16:20], s[20:32]])

    def __eq__(self, other):
        return self.binVal == UUID(other).binVal

    def __hash__(self):
        return hash(self.binVal)


class Service:
    def __init__(self, *args):
        (self.peripheral, uuidVal, self.hndStart, self.hndEnd) = args
        self.uuid = UUID(uuidVal)
        self.chars = None
        self.descs = None

    def getCharacteristics(self, forUUID=None):
        if not self.chars:
            self.chars = [] if self.hndEnd <= self.hndStart else self.peripheral.getCharacteristics(self.hndStart,
                                                                                                    self.hndEnd)
        if forUUID is not None:
            u = UUID(forUUID)
            return [ch for ch in self.chars if ch.uuid == u]
        return self.chars

    def getDescriptors(self, forUUID=None):
        if not self.descs:
            # Grab all descriptors in our range, except for the service
            # declaration descriptor
            all_descs = self.peripheral.getDescriptors(self.hndStart + 1, self.hndEnd)
            # Filter out the descriptors for the characteristic properties
            # Note that this does not filter out characteristic value descriptors
            self.descs = [desc for desc in all_descs if desc.uuid != 0x2803]
        if forUUID is not None:
            u = UUID(forUUID)
            return [desc for desc in self.descs if desc.uuid == u]
        return self.descs


class Characteristic:

    def __init__(self, *args):
        (self.peripheral, uuidVal, self.handle, self.properties, self.valHandle) = args
        self.uuid = UUID(uuidVal)
        self.descs = None

    def read(self):
        return self.peripheral.readCharacteristic(self.valHandle)

    def write(self, val, withResponse=False):
        return self.peripheral.writeCharacteristic(self.valHandle, val, withResponse)

    def getDescriptors(self, forUUID=None, hndEnd=0xFFFF):
        if not self.descs:
            # Descriptors (not counting the value descriptor) begin after
            # the handle for the value descriptor and stop when we reach
            # the handle for the next characteristic or service
            self.descs = []
            for desc in self.peripheral.getDescriptors(self.valHandle + 1, hndEnd):
                if desc.uuid in (0x2800, 0x2801, 0x2803):
                    # Stop if we reach another characteristic or service
                    break
                self.descs.append(desc)
        if forUUID is not None:
            u = UUID(forUUID)
            return [desc for desc in self.descs if desc.uuid == u]
        return self.descs

    def getHandle(self):
        return self.valHandle


class Descriptor:
    def __init__(self, *args):
        (self.peripheral, uuidVal, self.handle) = args
        self.uuid = UUID(uuidVal)

    def read(self):
        return self.peripheral.readCharacteristic(self.handle)

    def write(self, val, withResponse=False):
        self.peripheral.writeCharacteristic(self.handle, val, withResponse)

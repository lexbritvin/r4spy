"""Bluepy copy of internal classes to exclude dependency on the module."""
import binascii

ADDR_TYPE_PUBLIC = "public"
ADDR_TYPE_RANDOM = "random"


class BTLEException(Exception):
    """Base class for all Bluepy exceptions"""

    def __init__(self, message, resp_dict=None):
        self.message = message

        # optional messages from bluepy-helper
        self.estat = None
        self.emsg = None
        if resp_dict:
            self.estat = resp_dict.get('estat', None)
            if isinstance(self.estat, list):
                self.estat = self.estat[0]
            self.emsg = resp_dict.get('emsg', None)
            if isinstance(self.emsg, list):
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


class BTLEInternalError(BTLEException):
    def __init__(self, message, rsp=None):
        BTLEException.__init__(self, message, rsp)


class BTLEDisconnectError(BTLEException):
    def __init__(self, message, rsp=None):
        BTLEException.__init__(self, message, rsp)


class BTLEManagementError(BTLEException):
    def __init__(self, message, rsp=None):
        BTLEException.__init__(self, message, rsp)


class BTLEGattError(BTLEException):
    def __init__(self, message, rsp=None):
        BTLEException.__init__(self, message, rsp)


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

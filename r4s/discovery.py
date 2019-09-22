import yaml

from bluepy.btle import Peripheral, UUID

from r4s import UnsupportedDeviceException

UUID_SRV_R4S = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"  # GATT Service Custom: R4S custom service.
UUID_SRV_GENERIC = 0x1800  # GATT Service: Generic Access.

UUID_CCCD = "00002902-0000-1000-8000-00805f9b34fb"  # GATT Descriptors: Client Characteristic Configuration Descriptor.
UUID_CHAR_GENERIC = 0x2a00  # GATT Characteristics - Device Name.
UUID_CHAR_CONN = 0x2a04  # GATT Characteristics - Peripheral Preferred Connection Parameters.
UUID_CHAR_CMD = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # GATT Characteristics Custom: Write commands.
UUID_CHAR_RSP = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # GATT Characteristics Custom: Read commands responses.


class DeviceBTAttrs:
    """Device bluetooth attributes container."""

    def __init__(self, name=None, cmd=None, ccc=None, unsupported=False):
        self.name = name
        self.ccc = ccc
        self.cmd = cmd
        self.unsupported = unsupported

    def is_complete(self):
        """Whether the instance has all required fields."""
        return self.name is not None and self.ccc is not None and self.cmd is not None \
               or self.unsupported

    def as_dict(self):
        """Casts the instance to a dict."""
        return {
            'name': self.name,
            'ccc': self.ccc,
            'cmd': self.cmd,
            'unsupported': self.unsupported,
        }

    def get_class(self):
        if self.unsupported:
            raise UnsupportedDeviceException('The device is not supported.')
        """Checks known devices and returns a device class."""
        from r4s.devices import known_devices
        cls = known_devices[self.name]['cls'] if self.name in known_devices else None
        if cls is None:
            raise UnsupportedDeviceException('The device {} is not supported.', self.name)
        if cls is NotImplemented:
            raise NotImplemented('The device {} is known but not yet implemented.', self.name)
        return cls


class DeviceDiscovery:
    """Discovers bluetooth device and checks all required services.

    The implementation stores all discoveries in memory and will be flushed on next run.
    Bluetooth SIG encourage to cache discovered services, characteristics and descriptors.
    Inherit the class to introduce caching.
    """

    def __init__(self):
        self._discovered = {}

    def discover_device(self, peripheral: Peripheral, mac: str):
        """Discover peripheral services."""
        if mac in self._discovered and self._discovered[mac].is_complete():
            return self._discovered[mac]

        if mac not in self._discovered:
            self._discovered[mac] = DeviceBTAttrs()

        self._discover_device(self._discovered[mac], peripheral)
        # This section is reached only if previous didn't raise any errors.
        self._on_success(mac, self._discovered[mac])

        return self._discovered[mac]

    def _on_success(self, mac, new_attr):
        """Callback function when the peripheral was successfully discovered."""
        pass

    def as_dict(self):
        """Casts the instance to a dict."""
        result = {}
        for key, value in self._discovered.items():
            result[key] = value.as_dict()
        return result

    @staticmethod
    def _discover_device(attrs, peripheral):
        """Requests services to discover characteristics and descriptors."""
        # Services.
        services = peripheral.discoverServices()
        r4s_custom_uuid = UUID(UUID_SRV_R4S)
        if r4s_custom_uuid not in services:
            attrs.unsupported = True
            return

        r4s_service = services[UUID(UUID_SRV_R4S)]
        generic_srv = services[UUID(UUID_SRV_GENERIC)]
        # Main characteristics.
        if attrs.name is None:
            device_name_char = generic_srv.getCharacteristics(UUID_CHAR_GENERIC)[0]
            # Generic params.
            attrs.name = peripheral.readCharacteristic(device_name_char.valHandle).decode("utf-8")

        # R4S characteristics.
        if attrs.cmd is None:
            cmd_char = r4s_service.getCharacteristics(UUID_CHAR_CMD)[0]
            attrs.cmd = cmd_char.valHandle
        if attrs.ccc is None:
            cccd = r4s_service.getDescriptors(UUID_CCCD)[0]
            attrs.ccc = cccd.handle


class DeviceDiscoveryYml(DeviceDiscovery):
    """Discovery service with yml caching."""

    def __init__(self, filename):
        super().__init__()
        self.filename = filename
        try:
            with open(self.filename, 'r') as stream:
                config = yaml.safe_load(stream)
                for mac, attrs in config.items():
                    self._discovered[mac] = DeviceBTAttrs(**attrs)
        except FileNotFoundError:
            pass

    def _on_success(self, mac, new_attr):
        """Rewrite the whole file on success discovery."""
        with open(self.filename, 'w+') as stream:
            yaml.safe_dump(self.as_dict(), stream)

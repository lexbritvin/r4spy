import asyncio

try:
    from bluepy.btle import Peripheral, ADDR_TYPE_RANDOM, BTLEException, BTLEDisconnectError
except ImportError:
    from r4s.test.bluepy_helper import ADDR_TYPE_RANDOM, BTLEException, BTLEDisconnectError
    from r4s.test.peripherals.base import MockPeripheral as Peripheral

from r4s.discovery import DeviceDiscovery
from r4s import UnsupportedDeviceException, R4sAuthFailed
import logging

_LOGGER = logging.getLogger(__name__)


# TODO: Make it Singleton.
class DeviceManager:
    """Discovers a device and provides a connection if it's known."""
    _retry_i = 0

    def __init__(self, key, discovery: DeviceDiscovery, iface=0, ble_timeout=3, retries=10):
        if len(key) != 8:
            raise ValueError('Invalid key')
        self._discovery = discovery
        self._devices = {}
        self._ble_timeout = ble_timeout
        self._retries = retries
        self._addr_type = ADDR_TYPE_RANDOM
        self._iface = iface
        # TODO: Make it random on first run.
        self._key = key
        # TODO: Add lock on Mac.

    def connect(self, mac):
        """Provides connection to a device."""
        coro = asyncio.coroutine(self.async_connect)
        future = coro(mac)
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(future)

    async def async_connect(self, mac):
        """Provides connection to a device in async way."""
        peripheral = Peripheral()
        i = 0
        device = None
        err = None
        while i < self._retries:
            # Retry.
            if i != 0:
                _LOGGER.debug('Auth failed. Attempt no: %s. Trying again.', i + 1)
                await asyncio.sleep(self._ble_timeout)

            # Try connect.
            device, err = self._do_connect(peripheral, mac)
            if device is not None:
                break  # Success.

            i += 1

        if device is None:
            raise err

        self._devices[mac] = device
        return device

    def _do_connect(self, peripheral, mac):
        """Does actual connection and tries to auth the client."""
        conn_args = (mac, self._addr_type, self._iface)
        try:
            if mac not in self._devices:
                peripheral.connect(*conn_args)
                # Get device class and all used characteristics.
                bt_attrs = self._discovery.discover_device(peripheral, mac)
                cls = bt_attrs.get_class()
                device = cls(self._key, peripheral, conn_args, bt_attrs)
            else:
                device = self._devices[mac]
                device.connect()

            # Try auth before any actions.
            is_auth = device.try_auth()
            if not is_auth:
                raise R4sAuthFailed()

            # Success.
            _LOGGER.debug('Device %s (%s) connected successfully.', mac, device.bt_attrs.name)
            return device, None

        except (BTLEException, R4sAuthFailed) as err:
            _LOGGER.exception('connection failed')
            peripheral.disconnect()
            return None, err

        except UnsupportedDeviceException as e:
            _LOGGER.exception('unsupported device')
            peripheral.disconnect()
            raise

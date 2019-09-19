import time

try:
    from bluepy.btle import Peripheral, ADDR_TYPE_RANDOM, BTLEException
except ImportError:
    from r4s.test.helper import MockPeripheral as Peripheral, ADDR_TYPE_RANDOM, BTLEException

from r4s.discovery import DeviceDiscovery
from r4s import UnsupportedDeviceException, R4sAuthFailed
import logging

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel('DEBUG')
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
_LOGGER.addHandler(ch)


# TODO: Make it Singleton.
class DeviceManager:
    _retry_i = 0

    def __init__(self, key, discovery: DeviceDiscovery, iface=0, ble_timeout=3, retries=10):
        if len(key) != 8:
            raise ValueError('Invalid key')
        self._discovery = discovery
        self._ble_timeout = ble_timeout
        self._retries = retries
        self._addr_type = ADDR_TYPE_RANDOM
        self._iface = iface
        # TODO: Make it random on first run.
        self._key = key
        # TODO: Add lock on Mac.

    def connect(self, mac):
        last_error = None
        peripheral = Peripheral()
        conn_args = (mac, self._addr_type, self._iface)
        try:
            peripheral.connect(*conn_args)
            # Get device class and all used handles.
            config = self._discovery.discover_device(peripheral, mac)
            cls = config.get_class()
            device = cls(self._key, peripheral, conn_args, config)
            # Try auth before any actions.
            is_auth = device.try_auth()
            if not is_auth:
                raise R4sAuthFailed()

        except (BTLEException, R4sAuthFailed) as e:
            _LOGGER.debug(e)
            # Disconnect and try again.
            peripheral.disconnect()

            last_error = e
            if self._retry_i < self._retries:
                _LOGGER.debug('Auth failed. Attempt no: %s. Trying again.', self._retry_i + 1)
                self._retry_i += 1
                time.sleep(self._ble_timeout)
                return self.connect(mac)
            else:
                raise

        except UnsupportedDeviceException as e:
            _LOGGER.debug('unsupported device')
            peripheral.disconnect()
            raise

        finally:
            self._retry_i = 0

        # Free to send any commands.
        return device

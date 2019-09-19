"""Tests for the BluetoothInterface class."""
import unittest

from r4s import R4sAuthFailed
from r4s.discovery import DeviceDiscovery
from r4s.manager import DeviceManager

from r4s.protocol.redmond.response.kettle import MODE_BOIL, BOIL_TEMP, STATE_ON, STATE_OFF, MODE_HEAT, MAX_TEMP
from r4s.test.helper import BTLEException, ADDR_TYPE_RANDOM
from r4s.test.peripherals.kettle import MockKettle200Peripheral as Peripheral

import r4s.manager
r4s.manager.Peripheral = Peripheral
r4s.manager.ADDR_TYPE_RANDOM = ADDR_TYPE_RANDOM
r4s.manager.BTLEException = BTLEException


class TestKettle200(unittest.TestCase):
    """Tests for the BluetoothInterface class."""
    model = 'RK-G200S'

    def test_first_connect(self):
        """Test the usage of the with statement."""
        manager = self.get_manager()

        # When key is authed.
        with manager.connect(self.model) as kettle:
            kettle.first_connect()
            self.assertTrue(kettle._is_auth)
            self.assertTrue(kettle._peripheral.check_key(kettle._key))
            # Check data.
            self.assertListEqual(kettle._firmware_version, kettle._peripheral.fw_version.version)
            self.assertIsNotNone(kettle.status)
            self.assertIsNotNone(kettle.stats_ten)
            self.assertEqual(kettle.stats_ten, kettle._peripheral.statistics)
            self.assertEqual(kettle.status, kettle._peripheral.status)

        # When key is not authed
        manager._key = [0xaa] * 8
        try:
            with manager.connect(self.model) as kettle:
                kettle.first_connect()
                self.assertFalse(kettle._is_auth)
        except R4sAuthFailed:
            self.assertTrue(True)

        # TODO: Test sync.
        # TODO: Implement/test cache.
        # TODO: Imitate and test be busy.
        # TODO: Test all data structures creates correct bytes (size, possible content).

    def test_set_mode(self):
        # Register kettle.
        manager = self.get_manager()
        kettle = manager.connect(self.model)
        backend = kettle._peripheral

        kettle.first_connect()
        kettle.set_mode(MODE_BOIL)
        self.assertEqual(kettle.status, backend.status)
        self.assertEqual(backend.status.trg_temp, BOIL_TEMP)
        # Check that the kettle was not enabled to run set mode.
        self.assertEqual(kettle.status.state, STATE_OFF)
        kettle.switch_on()
        self.assertEqual(kettle.status.state, STATE_ON)

        kettle.switch_off()
        self.assertEqual(kettle.status, backend.status)
        self.assertEqual(kettle.status.state, STATE_OFF)

        # Test incorrect temp.
        old_temp = backend.status.trg_temp
        try:
            kettle.set_mode(MODE_HEAT, MAX_TEMP + 1)
            self.assertTrue(False)
        except ValueError:
            pass
        self.assertEqual(kettle.status, backend.status)
        self.assertEqual(backend.status.trg_temp, old_temp)

        # Test correct temp.
        kettle.set_mode(MODE_HEAT, MAX_TEMP)
        self.assertEqual(kettle.status, backend.status)
        self.assertEqual(backend.status.trg_temp, MAX_TEMP)
        # TODO: Test status change when on.
        # TODO: Test status == off when boiled. on when heat.
        # TODO: Test all responses.

    @staticmethod
    def get_manager():
        manager = DeviceManager(
            key=[0xbb] * 8,
            discovery=DeviceDiscovery(),
            ble_timeout=0,
            retries=1
        )
        return manager

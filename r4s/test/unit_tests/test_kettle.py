"""Tests for the BluetoothInterface class."""
import unittest

from btlewrap import BluetoothBackendException

from r4s.device.kettle.kettle import RedmondKettle
from r4s.protocol import MODE_BOIL, BOIL_TEMP, STATE_ON, STATE_OFF, MODE_HEAT, MAX_TEMP
from r4s.test.helper import MockKettleBackend


class TestBluetoothInterface(unittest.TestCase):
    """Tests for the BluetoothInterface class."""

    def test_first_connect(self):
        """Test the usage of the with statement."""

        kettle, backend = self.get_kettle()

        try:
            # Try get info without connection.
            kettle.first_connect()
        except BluetoothBackendException:
            pass
        self.assertIsNone(kettle._firmware_version)
        self.assertIsNone(kettle.status)
        self.assertIsNone(kettle.stats_ten)

        # When key is not authed and not ready to pair.
        backend.ready_to_pair = False
        try:
            with kettle:
                kettle.first_connect()
                self.assertFalse(kettle._is_auth)
                # Check that connection is done properly.
                self.assertIsNotNone(kettle._backend)
        except BluetoothBackendException:
            pass
        self.assertIsNone(kettle._backend)
        self.assertFalse(backend.check_key(kettle._key))

        # When ready to pair and key is not authed.
        backend.ready_to_pair = True
        with kettle:
            kettle.first_connect()
            self.assertTrue(kettle._is_auth)
        self.assertTrue(backend.check_key(kettle._key))
        # Check data.
        self.assertListEqual(kettle._firmware_version, backend.fw_version.version)
        self.assertIsNotNone(kettle.status)
        self.assertIsNotNone(kettle.stats_ten)
        self.assertEqual(kettle.stats_ten, backend.statistics)
        self.assertEqual(kettle.status, backend.status)

        # When not ready to pair and key changed and unauthed.
        backend.ready_to_pair = False
        old_key = kettle._key
        kettle._key = [0xaa] * 8
        try:
            with kettle:
                kettle.first_connect()
                self.assertFalse(kettle._is_auth)
        except BluetoothBackendException:
            pass
        self.assertFalse(backend.check_key(kettle._key))

        # When not ready to pair and key is authed.
        kettle._key = old_key
        with kettle:
            kettle.first_connect()
            self.assertTrue(kettle._is_auth)
        self.assertTrue(backend.check_key(kettle._key))

        # When key is not valid.
        kettle._key = [0xaa] * 2
        try:
            with kettle:
                kettle.first_connect()
        except ValueError:
            self.assertFalse(kettle._is_auth)

        # TODO: Test sync.
        # TODO: Implement/test cache.
        # TODO: Imitate and test be busy.
        # TODO: Test all data structures creates correct bytes (size, possible content).

    def test_set_mode(self):
        # Register kettle.
        kettle, backend = self.get_kettle()
        backend.ready_to_pair = True
        with kettle:
            kettle.first_connect()

        # Set kettle to boil.
        with kettle:
            kettle.set_mode(True, MODE_BOIL)
        self.assertEqual(kettle.status, backend.status)
        self.assertEqual(backend.status.trg_temp, BOIL_TEMP)
        self.assertEqual(kettle.status.state, STATE_ON)

        # Test disable.
        with kettle:
            kettle.set_mode(False)
        self.assertEqual(kettle.status, backend.status)
        self.assertEqual(kettle.status.state, STATE_OFF)

        # Test incorrect temp.
        old_temp = backend.status.trg_temp
        try:
            with kettle:
                kettle.set_mode(True, MODE_HEAT, MAX_TEMP + 1)
        except ValueError:
            pass
        self.assertEqual(kettle.status, backend.status)
        self.assertEqual(backend.status.trg_temp, old_temp)

        # Test correct temp.
        with kettle:
            kettle.set_mode(True, MODE_HEAT, MAX_TEMP)
        self.assertEqual(kettle.status, backend.status)
        self.assertEqual(backend.status.trg_temp, MAX_TEMP)
        # TODO: Test status change when on.
        # TODO: Test status == off when boiled. on when heat.
        # TODO: Test all responses.

    @staticmethod
    def get_kettle():
        kettle = RedmondKettle(
            'test_mac',
            cache_timeout=600,
            adapter='hci0',
            backend=MockKettleBackend,
            retries=1,
            auth_timeout=1,
        )
        return kettle, kettle._bt_interface._backend

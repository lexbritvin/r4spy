"""Tests for the BluetoothInterface class."""
import unittest

from r4s.kettle.kettle import RedmondKettle
from r4s.test.helper import MockKettleBackend


class TestBluetoothInterface(unittest.TestCase):
    """Tests for the BluetoothInterface class."""

    def test_first_connect(self):
        """Test the usage of the with statement."""

        kettle, backend = self.get_kettle()
        # Check we know nothing about backend.
        self.assertIsNone(kettle._firmware_version)
        self.assertIsNone(kettle.status)
        self.assertIsNone(kettle.statistics)

        # When key is not authed and not ready to pair.
        backend.ready_to_pair = False
        kettle.first_connect()
        self.assertFalse(kettle._is_auth)
        self.assertFalse(backend.check_key(kettle._key))

        # When ready to pair and key is not authed.
        backend.ready_to_pair = True
        kettle.first_connect()
        self.assertTrue(kettle._is_auth)
        self.assertTrue(backend.check_key(kettle._key))
        # Check data.
        self.assertListEqual(kettle._firmware_version, backend.fw_version)
        self.assertIsNotNone(kettle.status)
        self.assertIsNotNone(kettle.statistics)
        self.assertTrue(kettle.statistics == backend.statistics)
        self.assertTrue(kettle.status == backend.status)

        # When not ready to pair and key changed and unauthed.
        backend.ready_to_pair = False
        old_key = kettle._key
        kettle._key = [0xaa] * 8
        kettle.first_connect()
        self.assertFalse(kettle._is_auth)
        self.assertFalse(backend.check_key(kettle._key))
        # Check cache cleared.
        self.assertIsNone(kettle._firmware_version)
        self.assertIsNone(kettle.status)
        self.assertIsNone(kettle.statistics)

        # When not ready to pair and key is authed.
        kettle._key = old_key
        kettle.first_connect()
        self.assertTrue(kettle._is_auth)
        self.assertTrue(backend.check_key(kettle._key))

        # When key is not valid.
        kettle._key = [0xaa] * 2
        try:
            kettle.first_connect()
        except ValueError:
            self.assertFalse(kettle._is_auth)

        # TODO: Test sync.
        # TODO: Test boil/heat.
        # TODO: Test on/off.
        # TODO: Test status change when on.
        # TODO: Implement/test cache.
        # TODO: Imitate and test be busy.
        # TODO: Test all data structures creates correct bytes (size, possible content).


    @staticmethod
    def get_kettle():
        backend = MockKettleBackend
        kettle = RedmondKettle(
            'test_mac',
            cache_timeout=600,
            adapter='hci0',
            backend=backend,
            retries=1
        )
        return kettle, kettle._bt_interface._backend

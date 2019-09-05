"""Tests for the BluetoothInterface class."""
import unittest

from r4s.kettle import RedmondKettle
from r4s.test.helper import MockKettleBackend


class TestBluetoothInterface(unittest.TestCase):
    """Tests for the BluetoothInterface class."""

    def test_first_connect(self):
        """Test the usage of the with statement."""
        kettle = self.get_kettle()
        kettle._bt_interface._backend.ready_to_pair = False
        kettle.first_connect()
        self.assertFalse(kettle._is_auth)
        kettle._bt_interface._backend.ready_to_pair = True
        kettle.first_connect()
        self.assertTrue(kettle._is_auth)

        # TODO: Test status parse.
        # TODO: Test sync.
        # TODO: Test boil/heat.
        # TODO: Test on/off.
        # TODO: Test status change when on.
        # TODO: Implement/test cache.
        # TODO: Check stats parse.

    def get_kettle(self):
        backend = MockKettleBackend
        kettle = RedmondKettle(
            'test_mac',
            cache_timeout=600,
            adapter='hci0',
            backend=backend,
            retries=1
        )
        return kettle

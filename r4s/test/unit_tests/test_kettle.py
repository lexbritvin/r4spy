"""Tests for the BluetoothInterface class."""
import unittest

from r4s.kettle import RedmondKettle
from r4s.test.helper import MockKettleBackend


class TestBluetoothInterface(unittest.TestCase):
    """Tests for the BluetoothInterface class."""

    def test_first_connect(self):
        """Test the usage of the with statement."""
        backend = MockKettleBackend
        kettle = RedmondKettle(
            'tesc_mac',
            cache_timeout=600,
            adapter='hci0',
            backend=backend,
        )
        kettle.firstConnect()

"""Helpers for test cases."""
from btlewrap.base import AbstractBackend


class MockKettleBackend(AbstractBackend):
    """Mockup of a Backend and Sensor.

    The behaviour of this Sensors is based on the knowledge there
    is so far on the behaviour of the sensor. So if our knowledge
    is wrong, so is the behaviour of this sensor! Thus is always
    makes sensor to also test against a real sensor.
    """

    def __init__(self, adapter='hci0'):
        super(MockKettleBackend, self).__init__(adapter)
        self.written_handles = []
        self.override_read_handles = {
            0x000b: self.cmd_handle_read,
        }
        self.override_write_handles = {
            0x000c: self.subscribe_handle_write,
            0x000e: self.cmd_handle_write,
        }
        self.is_available = True
        self.iter = 0

    def check_backend(self):
        """This backend is available when the field is set accordingly."""
        return self.is_available

    def read_handle(self, handle):
        """Read one of the handles that are implemented."""
        if handle in self.override_read_handles:
            return self.override_read_handles[handle]()
        raise ValueError('handle not implemented in mockup')

    def write_handle(self, handle, value):
        """Writing handles just stores the results in a list."""
        self.written_handles.append((handle, value))
        if handle in self.override_write_handles:
            return self.override_write_handles[handle](value)
        raise ValueError('handle not implemented in mockup')

    def wait_for_notification(self, handle, delegate, notification_timeout):
        """same as write_handle. Delegate is not used, yet."""
        delegate.handleNotification(bytes([int(x, 16) for x in "54 3d 32 37 2e 33 20 48 3d 32 37 2e 30 00".split()]))
        return self.write_handle(handle, self._DATA_MODE_LISTEN)

    def cmd_handle_read(self):
        # TODO: Get read based on iter.
        return

    def subscribe_handle_write(self, value):
        # TODO: Save device is subsribed.
        return self.get_default_write_resp()

    def cmd_handle_write(self, value):
        ## TODO: Save current iter.
        return self.get_default_write_resp()

    def get_default_write_resp(self):
        # It always returns that.
        return ['wr']

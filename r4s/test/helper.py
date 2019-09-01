"""Helpers for test cases."""
from btlewrap.base import AbstractBackend

from r4s.helper import unwrap_recv, to_bytes, wrap_send
from r4s import kettle

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
            kettle._HANDLE_R_CMD: self.cmd_handle_read,
        }
        self.override_write_handles = {
            kettle._HANDLE_W_SUBSCRIBE: self.subscribe_handle_write,
            kettle._HANDLE_W_CMD: self.cmd_handle_write,
        }
        self.cmd_handlers = {
            kettle._DATA_CMD_AUTH: self.cmd_auth
        }
        self.cmd_responses = []
        self.is_available = True
        self.iter = 0
        self.is_subscribed = False
        self.auth_key = None
        ## TODO: Implement ready to pair.
        self.ready_to_pair = False

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
        if handle != kettle._HANDLE_W_SUBSCRIBE and not self.is_subscribed:
            raise ValueError('you are not subscribed to make writes')
        if handle in self.override_write_handles:
            return self.override_write_handles[handle](value)
        raise ValueError('handle not implemented in mockup')

    def wait_for_notification(self, handle, delegate, notification_timeout):
        """same as write_handle. Delegate is not used, yet."""
        delegate.handleNotification(bytes([int(x, 16) for x in "54 3d 32 37 2e 33 20 48 3d 32 37 2e 30 00".split()]))
        return self.write_handle(handle, self._DATA_MODE_LISTEN)

    def cmd_handle_read(self):
        if not self.cmd_responses:
            raise ValueError('no writes were registered')
        iter, cmd, data = self.cmd_responses[-1]
        resp = [cmd]
        resp.extend(data)
        return wrap_send(iter, resp)

    def subscribe_handle_write(self, value):
        # TODO: Save device is subsribed.
        self.is_subscribed = True
        return self.get_default_write_resp()

    def cmd_handle_write(self, value):
        ## TODO: Save current iter.
        self.iter, cmd, data = unwrap_recv(value)
        if not self.auth_key and cmd != kettle._DATA_CMD_AUTH:
            raise ValueError('you are not authorised to send commands')
        if cmd in self.cmd_handlers:
            resp = self.cmd_handlers[cmd](data)
            self.cmd_responses.append((self.iter, cmd, resp))
            return self.get_default_write_resp()
        raise ValueError('cmd not implemented in mockup')

    def get_default_write_resp(self):
        # It always returns that.
        return ['wr']

    def cmd_auth(self, data):
        if not self.ready_to_pair:
            return [0x00]
        self.auth_key = to_bytes(data)
        return [0x01]

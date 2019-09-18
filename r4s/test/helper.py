"""Helpers for test cases."""
from typing import List, Tuple

from r4s.manager import _HANDLE_R_CMD, _HANDLE_W_SUBSCRIBE, _HANDLE_W_CMD
from r4s.manager.kettle.kettle import RedmondKettle200
from r4s.protocol.redmond.command.common import *
from r4s.protocol.redmond.command.statistics import *
from r4s.protocol.redmond.command.lights import *
from r4s.protocol.redmond.response.common import *
from r4s.protocol.redmond.response.kettle import MODE_BOIL, STATE_OFF, STATE_ON


class MockKettleBackend(AbstractBackend):
    """Mockup of a Backend and Sensor.

    The behaviour of this Sensors is based on the knowledge there
    is so far on the behaviour of the sensor. So if our knowledge
    is wrong, so is the behaviour of this sensor! Thus is always
    makes sensor to also test against a real sensor.
    """

    def services(self):
        return {

        }.values()

    def __init__(self, adapter: str = 'hci0', address_type: str = 'public'):
        super(MockKettleBackend, self).__init__(adapter)
        # Read handlers.
        self.cmd_responses = []
        self.override_read_handles = {
            _HANDLE_R_CMD: self.cmd_handle_read,
        }
        # Write handlers.
        self.written_handles = []
        self.override_write_handles = {
            _HANDLE_W_SUBSCRIBE: self.subscribe_handle_write,
            _HANDLE_W_CMD: self.cmd_handle_write,
        }
        # Write cmd handlers.
        self.cmd_handlers = {
            CmdAuth.CODE: self.cmd_auth,
            CmdFw.CODE: self.cmd_fw,
            Cmd55UseBacklight.CODE: self.cmd_backlight,
            Cmd50SetLights.CODE: self.cmd_set_lights,
            Cmd51GetLights.CODE: self.cmd_get_lights,
            CmdSync.CODE: self.cmd_sync,
            Cmd6Status.CODE: self.cmd_status,
            Cmd5SetMode.CODE: self.cmd_set_mode,
            Cmd3On.CODE: self.cmd_on,
            Cmd4Off.CODE: self.cmd_off,
            Cmd71StatsUsage.CODE: self.cmd_stats_usage,
            Cmd80StatsTimes.CODE: self.cmd_stats_times,
        }

        # Current state.
        self.is_available = True
        self.is_connected = False
        self.ready_to_pair = False
        self.is_subscribed = False
        self.is_authed = False
        self.auth_keys = set()
        self.counter = 0
        # Internal status.
        # Firmware version.
        self.fw_version = VersionResponse([3, 10])
        # Statistics data.
        self.statistics = TenInformationResponse(
            ten_num=0,
            err=0,
            work_time=1223,
            spent_power=102252,
            relay_turn_on_amount=0,
        )

        # TODO: Change to test other.
        self.device_cls = RedmondKettle200
        # Current status.
        self.status = self.device_cls.status_resp_cls(
            program=MODE_BOIL,
            curr_temp=40,
            trg_temp=0,
            state=STATE_OFF,
            boil_time=0
        )

    def connect(self, mac):
        if self.is_connected:
            ValueError('cannot have more than 1 connection')
        self.is_connected = True

    def disconnect(self):
        if not self.is_connected:
            ValueError('cannot disconnect when not connected')
        self.is_connected = False
        self.is_subscribed = False
        self.is_authed = None

    @staticmethod
    def scan_for_devices(timeout) -> List[Tuple[str, str]]:
        return [
            ('r4s', 'RK-G200S'),
            *[('mac_' + str(x), 'title_' + str(x)) for x in range(3)]
        ]

    def check_backend(self):
        """This backend is available when the field is set accordingly."""
        return self.is_available

    def check_connected(self):
        if not self.is_connected:
            raise ValueError('Not connected')
        return True

    def read_handle(self, handle):
        self.check_connected()
        """Read one of the handles that are implemented."""
        if handle in self.override_read_handles:
            return self.override_read_handles[handle]()
        raise ValueError('handle not implemented in mockup')

    def write_handle(self, handle, value):
        """Writing handles just stores the results in a list."""
        self.check_connected()
        self.written_handles.append((handle, value))

        if handle != _HANDLE_W_SUBSCRIBE and not self.is_subscribed:
            raise ValueError('you are not subscribed to make writes')

        if handle in self.override_write_handles:
            return self.override_write_handles[handle](value)
        raise ValueError('handle not implemented in mockup')

    def wait_for_notification(self, handle, delegate, notification_timeout):
        """same as write_handle. Delegate is not used, yet."""
        self.write_handle(handle, self._DATA_MODE_LISTEN)
        if handle == _HANDLE_W_CMD:
            resp = self.read_handle(_HANDLE_R_CMD)
            delegate.handleNotification(_HANDLE_R_CMD, resp)
            return True

        return False

    def cmd_handle_read(self):
        if not self.cmd_responses:
            raise ValueError('no writes were registered')

        # Pop the latest response.
        counter, cmd, data = self.cmd_responses[-1]
        return RedmondCommand.wrap(counter, cmd, data)

    def subscribe_handle_write(self, value):
        self.is_subscribed = True
        return ['wr']

    def cmd_handle_write(self, value):
        self.counter, cmd, data = RedmondCommand.unwrap(value)
        if not self.is_authed and cmd != CmdAuth.CODE:
            raise ValueError('you are not authorised to send commands')

        if cmd in self.cmd_handlers:
            resp = self.cmd_handlers[cmd](data)
            self.cmd_responses.append((self.counter, cmd, resp))
            return ['wr']

        raise ValueError('cmd not implemented in mockup')

    def check_key(self, key):
        if len(key) != 8:
            raise ValueError('Auth key is not 8 bytes long.')
        return bytes(key) in self.auth_keys

    def cmd_auth(self, data):
        if self.check_key(data):
            self.is_authed = True
            return SuccessResponse(True).to_arr()

        if not self.ready_to_pair:
            return SuccessResponse(False).to_arr()

        self.is_authed = True
        self.auth_keys.add(bytes(data))
        return SuccessResponse(True).to_arr()

    def cmd_fw(self, data):
        return self.fw_version.to_arr()

    def cmd_backlight(self, data):
        # TODO: Handle somehow.
        return ErrorResponse(0).to_arr()

    def cmd_set_lights(self, data):
        # TODO: Handle somehow.
        return ErrorResponse(0).to_arr()

    def cmd_get_lights(self, data):
        # TODO: Return current set values.
        return [0x00, 0x28, 0x5e, 0x00, 0x00, 0xff, 0x46, 0x5e, 0x00, 0xff, 0x00, 0x64, 0x5e, 0xff, 0x00, 0x00]

    def cmd_sync(self, data):
        # TODO: Save time.
        return ErrorResponse(0).to_arr()

    def cmd_status(self, data):
        return self.status.to_arr()

    def cmd_set_mode(self, data):
        try:
            new_status = self.device_cls.status_resp_cls.from_bytes(data)
        except ValueError:
            return SuccessResponse(False).to_arr()

        # Save mode.
        self.status.mode = new_status.mode
        self.status.trg_temp = new_status.trg_temp
        self.status.boil_time = new_status.boil_time

        return SuccessResponse(True).to_arr()

    def cmd_on(self, data):
        # TODO: Return 0x00 on some internal error.
        self.status.state = STATE_ON
        return SuccessResponse(True).to_arr()

    def cmd_off(self, data):
        # TODO: Return 0x00 on some internal error.
        self.status.state = STATE_OFF
        return SuccessResponse(True).to_arr()

    def cmd_stats_usage(self, data):
        return self.statistics.to_arr()

    def cmd_stats_times(self, data):
        return self.statistics.to_arr()

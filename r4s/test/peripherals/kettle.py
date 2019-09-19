from r4s.devices.kettles import RedmondKettle200
from r4s.protocol.redmond.command.lights import Cmd55UseBacklight, Cmd50SetLights, Cmd51GetLights
from r4s.protocol.redmond.command.statistics import Cmd71StatsUsage, Cmd80StatsTimes
from r4s.protocol.redmond.response.common import SuccessResponse, ErrorResponse, VersionResponse
from r4s.protocol.redmond.response.kettle import MODE_BOIL, STATE_OFF
from r4s.protocol.redmond.response.statistics import TenInformationResponse
from .base import MockPeripheral


class MockKettle200Peripheral(MockPeripheral):
    """Kettle 200 mock peripheral."""

    def __init__(self, *args):
        super().__init__(*args)
        # Write cmd handlers.
        self.cmd_handlers.update({
            Cmd55UseBacklight.CODE: self.cmd_set_backlight,
            Cmd50SetLights.CODE: self.cmd_set_lights,
            Cmd51GetLights.CODE: self.cmd_get_lights,
            Cmd71StatsUsage.CODE: self.cmd_stats_usage,
            Cmd80StatsTimes.CODE: self.cmd_stats_times,
        })

        # Internal status. Firmware version.
        self.fw_version = VersionResponse([3, 10])
        # Statistics data.
        self.statistics = TenInformationResponse(
            ten_num=0,
            err=0,
            work_time=1223,
            spent_power=102252,
            relay_turn_on_amount=0,
        )

        self.device_cls = RedmondKettle200
        # Current status.
        self.status = self.device_cls.status_resp_cls(
            program=MODE_BOIL,
            curr_temp=40,
            trg_temp=0,
            state=STATE_OFF,
            boil_time=0
        )

    def get_device_name(self):
        """Returns device name for generic service."""
        return b'RK-G200S'

    def cmd_set_backlight(self, data):
        """Sets backlight."""
        # TODO: Handle somehow.
        return ErrorResponse(0).to_arr()

    def cmd_set_lights(self, data):
        """Sets the light."""
        # TODO: Handle somehow.
        return ErrorResponse(0).to_arr()

    def cmd_get_lights(self, data):
        """Gets current light settings."""
        # TODO: Return current set values.
        return [0x00, 0x28, 0x5e, 0x00, 0x00, 0xff, 0x46, 0x5e, 0x00, 0xff, 0x00, 0x64, 0x5e, 0xff, 0x00, 0x00]

    def cmd_stats_usage(self, data):
        """Returns device statistics of usage."""
        return self.statistics.to_arr()

    def cmd_stats_times(self, data):
        """Returns device statistics with number of uses."""
        return self.statistics.to_arr()

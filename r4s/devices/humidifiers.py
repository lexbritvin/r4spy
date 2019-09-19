from r4s.devices.base import RedmondDevice


class Humidifier3310(RedmondDevice):
    pass


humidifiers = {
    "RHF-3310S": {
        "cls": Humidifier3310,
    },
    "RHF-3317S": {
        "cls": Humidifier3310,
    },
    "RHF-3318S": {
        "cls": Humidifier3310,
    },
}

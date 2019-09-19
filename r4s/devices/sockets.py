from r4s.devices.base import RedmondDevice


class Socket100(RedmondDevice):
    pass


class Bulb202(RedmondDevice):
    pass


class CordBA300S(RedmondDevice):
    pass


sockets = {
    "RSP-S202S": {
        "cls": Bulb202,
    },
    "RSP-100S": {
        "cls": Socket100,
    },
    "RSP-121S": {
        "cls": Socket100,
    },
    "RSP-103S": {
        "cls": Socket100,
    },
    "RSP-300S": {
        "cls": CordBA300S,
    },
    "RSP-BA300S": {
        "cls": CordBA300S,
    },
    "RSP-BA300S/1/1": {
        "cls": CordBA300S,
    },
    "RSP-301S": {
        "cls": CordBA300S,
    },
    "RSP-303S": {
        "cls": CordBA300S,
    },
}

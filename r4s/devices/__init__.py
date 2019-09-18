from .air_cleaners import air_cleaners
from .coffee_machines import coffee_machines
from .cookers import cookers
from .fans import fans
from .floor import floor
from .heaters import heaters
from .humidifiers import humidifiers
from .irons import irons
from .kettles import kettles
from .ovens import ovens
from .sensors import sensors
from .sockets import sockets
from .thermopots import thermopots
from .water_heaters import water_heaters

known_devices = {
    **air_cleaners,
    **coffee_machines,
    **cookers,
    **fans,
    **floor,
    **heaters,
    **humidifiers,
    **irons,
    **kettles,
    **ovens,
    **sockets,
    **sensors,
    **thermopots,
    **water_heaters,
}

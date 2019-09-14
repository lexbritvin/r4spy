from r4s.protocol.redmond.response.common import RedmondResponse

LIGHT_TYPE_BOIL = 0x00
LIGHT_TYPE_BACKLIGHT = 0x01


class ColorSchemeResponse(RedmondResponse):

    def __init__(self, scheme_id, color1, color2, color3):
        if len(color1) != 5 or len(color2) != 5 or len(color3) != 5:
            ValueError('Incorrect color config')
        self.id = scheme_id
        self.colors = []
        for color in [color1, color2, color3]:
            self.colors.append({
                'percent': color[0],
                'brightness': color[1],
                'red': color[2],
                'green': color[3],
                'blue': color[4],
            })

    @classmethod
    def from_bytes(cls, data: list):
        return cls(
            scheme_id=data[0],
            color1=data[1:6],
            color2=data[6:11],
            color3=data[11:16],
        )

    def to_arr(self):
        data = [self.id]
        for color in self.colors:
            data.append(color['percent'])
            data.append(color['brightness'])
            data.append(color['red'])
            data.append(color['green'])
            data.append(color['blue'])
        return data


class NightLightWorkTimeResponse(RedmondResponse):

    def __init__(self, time):
        self.time = time

    @classmethod
    def from_bytes(cls, data: list):
        return cls(
            time=data[0],
        )

    def to_arr(self):
        return [self.time, 0]


class PaletteConfigResponse(RedmondResponse):

    def __init__(self, light_type, state, palette_num, err):
        self.light_type = light_type  # Boil 0 or night light 1.
        self.state = state
        self.palette_num = palette_num
        self.err = err

    @classmethod
    def from_bytes(cls, data: list):
        return cls(
            light_type=data[0],
            state=data[2],
            palette_num=data[3],
            err=data[4],
        )

    def to_arr(self):
        return [self.light_type, 0, self.state, self.palette_num, self.err]

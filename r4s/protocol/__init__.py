BYTE_ORDER = 'little'


def int_to_arr(val, byte_num, signed=False):
    """Converts int to byte array."""
    return [x for x in val.to_bytes(byte_num, byteorder=BYTE_ORDER, signed=signed)]


def int_from_bytes(byte_arr):
    """Create int from byte array."""
    return int.from_bytes(byte_arr, BYTE_ORDER)


def fahrenheit_to_celsius(c: int):
    """Converts fahrenheit to celsius."""
    return (c - 32) * 5 / 9


def celsius_to_fahrenheit(f: int):
    """Converts celsius to fahrenheit."""
    return round(f * 1.8 + 32)


def float_to_arr(f: float):
    """R4S function to convert float to byte array.

    The function has strange output for negative numbers
    and numbers more than a byte 255. It is not clear if such numbers
    ever appear in the app.
    """
    f2 = 1.0 if f > 0.0 else -1.0
    f_abs = float(abs(f))
    i = 0
    while f_abs > 2045.0:
        f_abs /= 10.0
        i += 1
        if i > 7:
            return int_to_arr(2046 if f2 > 0.0 else 2050, 2)

    # Round small values to 1 or return 0.
    while f_abs < 1.0:
        f_abs *= 10.0
        i -= 1
        if i < -8:
            return int_to_arr(0, 2)
    f_abs2 = abs(float(round(f_abs * 10000.0)) - float(round(f_abs) * 10000))
    while f_abs2 > 0.5 and i > -8:
        d = f_abs * 10.0
        if d > 2045.0:
            break
        i -= 1
        f_abs2 = abs(round(d * 10000.0) - round(d) * 10000)
        f_abs = d

    return int_to_arr((round(f2 * f_abs) & 4095) | ((i & 15) << 12), 4)

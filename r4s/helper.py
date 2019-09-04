from r4s.kettle import _DATA_BEGIN_BYTE
from r4s.kettle import _DATA_END_BYTE


def to_bytes(data):
    return bytes(data)


def wrap_send(counter, data, byte_order='little'):
    result = [_DATA_BEGIN_BYTE]
    result.append(counter)
    normalized = []
    for val in data:
        if type(val) is tuple:
            normalized.extend([x for x in val[0].to_bytes(val[1], byte_order)])
        else:
            normalized.append(val)
    result.extend(normalized)
    result.append(_DATA_END_BYTE)
    return to_bytes(result)


def unwrap_recv(byte_arr):
    int_array = [x for x in byte_arr]
    start, i, cmd = int_array[:3]
    # TODO: Check iter == iter_init, cmd == cmd_init
    return i, cmd, int_array[3:-1]


def parse_status(data):
    mode = data[0]  # Boil/Heat/Light.
    tgtemp = data[2]  # Target temp.
    temp = data[5]  # Current temp.
    status = data[8]  # On/Off
    boil_time_relative = data[13] - 0x80  # Relative boil time in range [-5:5]
    return {
        'temp': temp,
        'tg_temp': tgtemp,
        'status': status,
        'mode': mode,
        'boil_time': boil_time_relative,
    }


def prepare_mode(status):
    data = [status['mode'], 0x00, status['tgtemp']]  # Set mode and target temp.
    data.append((0, 10))  # 10 empty bytes.
    data.append(0x80 + (status['boil_time'] or 0))  # Set boil time.
    data.append((0, 2))  # 2 empty bytes.
    return data

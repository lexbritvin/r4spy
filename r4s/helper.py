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

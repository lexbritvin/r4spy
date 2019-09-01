from r4s.kettle import _DATA_BEGIN_BYTE
from r4s.kettle import _DATA_END_BYTE


def to_bytes(data):
    return bytes(data)


def wrap_send(iter, data):
    result = [_DATA_BEGIN_BYTE]
    result.append(iter)
    result.extend(data)
    result.append(_DATA_END_BYTE)
    return to_bytes(result)


def unwrap_recv(byte_arr):
    int_array = [x for x in byte_arr]
    start, iter, cmd = int_array[:3]
    # TODO: Check iter == iter_init, cmd == cmd_init
    return iter, cmd, int_array[3:-1]

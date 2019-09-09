BYTE_ORDER = 'little'


def int_to_arr(val, byte_num):
    return [x for x in val.to_bytes(byte_num, BYTE_ORDER)]


def int_from_bytes(byte_arr):
    return int.from_bytes(byte_arr, BYTE_ORDER)

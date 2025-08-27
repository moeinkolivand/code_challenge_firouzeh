import string

BASE62_ALPHABET = string.digits + string.ascii_uppercase + string.ascii_lowercase
BASE = len(BASE62_ALPHABET)

def encode_base62(num: int) -> str:
    if num == 0:
        return BASE62_ALPHABET[0]
    s = []
    while num > 0:
        num, rem = divmod(num, BASE)
        s.append(BASE62_ALPHABET[rem])
    return ''.join(reversed(s))

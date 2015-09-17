#!/usr/bin/env python


def sk_id_encode(number):
    return base36encode(int(str(number)[2:-2]))


def sk_id_decode(string):
    return int('73' + str(base36decode(string)) + '00')


def base36encode(number, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
    """Converts an integer to a base36 string."""
    if not isinstance(number, (int, long)):
        raise TypeError('number must be an integer')

    base36 = ''
    sign = ''

    if number < 0:
        sign = '-'
        number = -number

    if 0 <= number < len(alphabet):
        return sign + alphabet[number]

    while number != 0:
        number, i = divmod(number, len(alphabet))
        base36 = alphabet[i] + base36

    return sign + base36


def base36decode(number):
    return int(number, 36)


print sk_id_encode(7339865163392400)
print sk_id_decode('534YW1DW')

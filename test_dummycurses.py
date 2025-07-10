"""Test dummycurses against the real curses"""

import itertools

import _curses
import dummycurses

_curses.setupterm(dummycurses._TERM, 2)

for name in dummycurses._TERMINFO:
    want = _curses.tigetstr(name)
    got = dummycurses.tigetstr(name)
    hdr = f'{name}: {want} == {got}'
    if want != got:
        print(hdr)
    assert want == got

    s = got

    params = [
        (0, -1111, -256, -255, -50, -1, 1, 10, 50, 255, 256, 500, 1000, 1111)
        for i in range(10)
        if f'%p{i}'.encode('ascii') in want
        or (b'%i' in want) and i < 2
    ]
    for params in itertools.product(*params):
        want = _curses.tparm(s, *params)
        got = dummycurses.tparm(s, *params)
        if want != got:
            print(hdr)
            print(f'   {params}:\t{want} == {got}')
        assert want == got

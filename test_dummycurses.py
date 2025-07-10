"""Test dummycurses against the real curses"""

import itertools

import _curses
import dummycurses

_curses.setupterm(dummycurses._TERM, 2)

for name in dummycurses._TERMINFO:
    want = _curses.tigetstr(name)
    got = dummycurses.tigetstr(name)
    hdr = f'{name}: {want} == {got}'
    try:
        assert want == got

        s = got

        params = [
            (0, 1, 10, -1, -50, 255, 256, -256, -255, 50, 500, 1000, 1111, -1111)
            for i in range(5)
            if f'%p{i}'.encode('ascii') in want
            or (b'%i' in want) and i < 2
        ]
        for params in itertools.product(*params):
            want = _curses.tparm(s, *params)
            try:
                got = dummycurses.tparm(s, *params)
            except Exception as e:
                e.add_note(f'   {params}:\t{want} == ?')
                raise
            try:
                assert want == got
            except Exception as e:
                e.add_note(f'   {params}:\t{want} == {got}')
                raise
    except Exception as e:
        e.add_note(hdr)
        raise

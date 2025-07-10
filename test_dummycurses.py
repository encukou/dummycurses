"""Test dummycurses against the real curses"""

from pathlib import Path
import itertools
import subprocess

import _curses
import dummycurses
from _pyrepl import _minimal_curses

_curses.setupterm(dummycurses._TERM, 2)


def test_tigetstr_and_tparm(term_name, terminfo, cache=set()):

    # Use setupterm via ctypes: Python's wrapper disallows
    # repeated initialization
    _minimal_curses.setupterm(term_name.encode(), 2)

    for name in terminfo:
        got = dummycurses.tigetstr(name, terminfo)
        if term_name == dummycurses._TERM or 1:
            want = _curses.tigetstr(name)
        else:
            want = got
        hdr = f'{term_name} {name}: {want} == {got}'
        print(hdr)
        try:
            assert want == got

            s = got
            if s in cache:
                continue
            cache.add(s)

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

test_tigetstr_and_tparm(dummycurses._TERM, dummycurses._TERMINFO)

for path in Path('/usr/share/terminfo/').glob('*/*'):
    print(path)
    term_name = path.name
    if term_name in {'rxvt-unicode', 'rxvt-unicode-256color'}:
        # TODO: acsc seems corrupted for these?
        continue
    proc = subprocess.run(['infocmp', term_name], stdout=subprocess.PIPE)
    source = proc.stdout.decode()
    print(source)
    terminfo = dummycurses._get_terminfo(source)
    print(terminfo)
    test_tigetstr_and_tparm(term_name, terminfo)

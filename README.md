# dummycurses

A super-minimal 'curses' stub

Provides the functions _pyrepl needs, hardcoding values to `xterm-256color`
(which "new" terminal emulators are likely to support).
If your $TERM is different, try substituting your own `infocmp` output.

Use this instead of _pyrepl._minimal_curses.

See `man terminfo` for docs on the format.

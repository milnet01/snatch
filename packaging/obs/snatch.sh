#!/bin/sh
# /usr/bin/snatch: the launcher the OBS package installs (SNAT-0028).
# The app is Snatch's own source under /usr/share/snatch, run by the system's
# Python; "$@" passes arguments through, so `snatch --selftest` works.
exec /usr/bin/python3 /usr/share/snatch/snatch.py "$@"

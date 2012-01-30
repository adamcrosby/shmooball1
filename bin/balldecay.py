#!/usr/bin/python

from __future__ import division
from redis import Redis

## Constants
TRACKS=(1,2,3)

r = Redis("localhost")

for track in TRACKS:
    try:
        decay_percent = float(r.get('%s:decay_percent' % track))
    except TypeError, ValueError:
        decay_percent = .9

    try:
        ballcount = int(r.get('%d:ballcount' % track))
    except TypeError, ValueError:
        ballcount = 0

    try:
        new_ballcount = int(ballcount * decay_percent)
    except ZeroDivisionError:
        print "skipping"
        continue

    print "track: %d  decay: %s old ballcount: %d  new ballcount: %d" % (track, decay_percent, ballcount, new_ballcount)

    r.set('%d:ballcount' % track, new_ballcount)

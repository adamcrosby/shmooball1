#!/usr/bin/python

from __future__ import division
from redis import Redis
import sys
import time

## Constants
MIN_TIMEDELTA = 3600 ## fire horn no more than once every N seconds

r = Redis("localhost")

def log(msg):
    logfile = open('/tmp/log.10241', 'a')
    logfile.write(msg)
    logfile.write("\n")
    logfile.close()

log("started moose script")

try:
    moosemode = int(r.get('2:honk_action'))
except:
    moosemode = None

#print 0

if moosemode > 0:
    r.delete('2:honk_action')
    print 3
    sys.exit(254)

try:
    count = int(r.get('2:ballcount'))
except:
    count = 0

time_delta = 0

log("count is currently %s" % count)

if count > 8:
    try:
        last_honk = int(r.get('2:last_honk'))
        time_delta = int(time.time() - last_honk)
    except Exception, e:
        log("exception in time check - %s" % e)
        last_honk = int(time.time())
        r.set('2:last_honk', int(time.time()))

    log("time delta is %s" % time_delta)

    if time_delta > MIN_TIMEDELTA:
        log("timedelta is gt %s, firing horn" % MIN_TIMEDELTA)
        r.set('2:last_honk', int(time.time()))
        print 3
        sys.exit()
    else:
        log("timedelta is lt %s, skipping horn" % MIN_TIMEDELTA)
        print 2
        sys.exit()
elif count > 2:
    log("count is gt 2, setting angry blinky eyes")
    print 2
    sys.exit()
elif count > 1:
    log("count is gt 1, setting angry eyes")
    print 1
    sys.exit()
else:
    log("count is eq 0, setting normal eyes")
    print 0

import datetime
import pytz
import calendar
import pygtfs
import numpy as np
import gevent

from . import settings

sched = pygtfs.Schedule(':memory:')
pygtfs.append_feed(sched, settings.GTFS_FILE)

def _utcnow():
    return pytz.UTC.localize(datetime.datetime.now())

pacific = pytz.timezone('US/Pacific')

def _now():
    return _utcnow().astimezone(pacific)

def _today():
    return pacific.localize(datetime.datetime.combine(_now().date(), datetime.time()))


def _unix_ts(dt):
    return calendar.timegm(dt.utctimetuple())


def lookup_train_service(timestamp):
    dow = timestamp.weekday()
    for s in sched.services:
        svc_days = [s.sunday, s.monday, s.tuesday, s.wednesday, s.thursday, s.friday, s.saturday]
        if svc_days[dow]:
            return s

    raise RuntimeError('Failed to lookup train service for {}'.format(timestamp))


def lookup_stop_schedule(svc_id, dir_id):
    trips = frozenset(t.trip_id for t in sched.trips if t.service_id == svc_id and t.direction_id == dir_id)
    return [s for s in sched.stop_times if s.trip_id in trips]


def match_to_stop(stop_sched, loc):
    def point(stop_time):
        s = sched.stops_by_id(stop_time.stop_id)[0]
        departs = _today() + stop_time.departure_time
        return s.stop_lat, s.stop_lon, _unix_ts(departs)

    stops = np.array([point(s) for s in stop_sched])
    user = np.array([loc[0], loc[1], _unix_ts(loc[2])])

    sqdiff = (stops - user)**2
    i = sqdiff.sum(axis=1).argmin()

    return stop_sched[i]


def lookup_stop_time(station, train_no):
    trip = sched.trips_by_id(train_no)[0]
    for st in sched.stop_times:
        if st.trip_id == trip.trip_id and st.stop_id == station.stop_id:
            return st

    raise RuntimeError('Failed to find {} station for train {}'.format(station.stop_id, trip.trip_id))


def lookup_station(station_id):
    return sched.stops_by_id(station_id)[0]


def monitor_arrival(stop_time, interval, callback):
    while True:
        arrival = _today() + stop_time.arrival_time
        arrives_in = arrival - _now()
        if arrives_in.total_seconds() < 0:
            # already arrived
            arrives_in = datetime.timedelta()

        if not callback(arrives_in):
            return

        gevent.sleep(interval)

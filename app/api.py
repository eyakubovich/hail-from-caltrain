from __future__ import absolute_import
import warnings
warnings.simplefilter("ignore")

import sys
import dateutil.parser

from flask import request, Flask, jsonify
from flask import make_response, render_template, redirect
import gevent
from webargs import fields
from webargs.flaskparser import use_args

from . import settings
from .lyft_client import LyftClient
from .caltrain import *


app = Flask(__name__)
app.config.from_object(settings)

@app.route('/healthcheck')
def healthcheck():
    # The healthcheck returns status code 200
    return 'OK'


query_train_args = {
    'location': fields.Str(required=True),
    'timestamp': fields.Str(required=True),
    'direction': fields.Int(required=True)
}


@app.route('/trains/query')
@use_args(query_train_args)
def query_train(args):
    location = args['location']
    timestamp = args['timestamp']
    direction = int(args['direction'])

    train = process_query_train(location, timestamp, direction)
    return jsonify({
        'train': train
    })


def process_query_train(location, timestamp, direction):
    lat, lng = location.split(',')
    lat, lng = float(lat), float(lng)
    ts = dateutil.parser.parse(timestamp)

    svc = lookup_train_service(ts)
    stop_sched = lookup_stop_schedule(svc.service_id, direction)

    stop_time = match_to_stop(stop_sched, (lat, lng, ts))
    return stop_time.trip_id


@app.route('/rides/requests', methods=['POST'])
def post_ride_request():
    station_code = request.form['station']
    train_no = request.form['train_no']
    access_token = request.cookies['lyft_token']

    process_ride_request(station_code, None, train_no, access_token)
    return make_response()


def process_ride_request(station_code, dest, train_no, access_token):
    station = lookup_station(station_code)
    stop_time = lookup_stop_time(station, train_no)

    lat = station.stop_lat
    lng = station.stop_lon

    lyft = LyftClient(access_token)

    def on_arrival_update(arrives_in):
        try:
            print 'Train arrives in: ', arrives_in
            eta = lyft.eta(lat, lng)
            print 'Current ETA is {} seconds'.format(eta)
            if eta >= arrives_in.total_seconds():
                print 'Requesting Lyft to {}, {}'.format(lat, lng)
                lyft.request_ride(lat, lng)
                print 'Ride {} requested!'.format(resp['ride_id'])
                return False
            return True
        finally:
            print

    gevent.spawn(monitor_arrival, stop_time, 10, on_arrival_update)


@app.route('/')
def home():
    access_token = request.cookies.get('lyft_token')
    if not access_token:
        return redirect(LyftClient.authorize_url())
    else:
        return render_template('home.html')


authorized_args = {
    'code': fields.Str(required=True)
}


@app.route('/authorized')
@use_args(authorized_args)
def authorized(args):
    access_token = LyftClient.retrieve_oauth_token(args['code'])

    resp = redirect('/')
    resp.set_cookie('lyft_token', access_token)
    return resp

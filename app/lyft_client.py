import requests

from . import settings

class LyftClient(object):
    def __init__(self, token):
        self.token = token

    def _request(self, url, method='GET', **kwargs):
        headers = {
            'Authorization': 'Bearer ' + self.token
        }
        resp = requests.request(method, url, headers=headers, **kwargs)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def authorize_url():
        return settings.LYFT_OAUTH_AUTHORIZE_URL + '?client_id={}&response_type=code&scope=public%20rides.request&state=foo'.format(settings.LYFT_CLIENT_ID)

    @staticmethod
    def retrieve_oauth_token(code):
        url = settings.LYFT_OAUTH_TOKEN_URL
        body = {
            'grant_type': 'authorization_code',
            'code': code
        }

        creds = (settings.LYFT_CLIENT_ID, settings.LYFT_CLIENT_SECRET)
        resp = requests.post(url, json=body, auth=creds)
        resp.raise_for_status()

        resp_body = resp.json()
        return resp_body['access_token']

    def eta(self, lat, lng, ride_type='lyft'):
        args = dict(lat=lat, lng=lng, ride_type=ride_type)
        resp = self._request('https://api.lyft.com/v1/eta', params=args)

        for eta in resp['eta_estimates']:
            if eta['ride_type'] == 'lyft' and eta['is_valid_estimate']:
                return eta['eta_seconds']

        raise RuntimeError('Unable to get eta')

    def request_ride(self, lat, lng, ride_type='lyft'):
        args = {
            'ride_type': ride_type,
            'origin': {
                'lat': lat,
                'lng': lng
            }
        }
        resp = self._request('https://api.lyft.com/v1/rides', method='POST', json=args)

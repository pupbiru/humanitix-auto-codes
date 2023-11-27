#!/usr/bin/env python3

import datetime
import itertools
import json
import re
import requests
import sys

from copy import deepcopy
from pprint import pprint

def get_usersettings():
    with open('usersettings.json', 'r') as f:
        return json.load(f)

def get_settings():
    with open('settings.json', 'r') as f:
        return json.load(f)

def get_token(firebase_api_key, refresh_token):
    res = requests.post(
        'https://securetoken.googleapis.com/v1/token',
        params={'key': firebase_api_key},
        data={
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
        },
    )
    assert res.status_code >= 200 and res.status_code < 300, res.text
    return res.json()

def dt_suffix(d):
    return {1:'st',2:'nd',3:'rd'}.get(d%20, 'th')
def custom_strftime(format, t):
    return t.strftime(format).replace('{S}', str(t.day) + dt_suffix(t.day))

def auto_discount(name_suffix, *ids):
    return {
        'code': f'[AUTO] {name_suffix}',
        'quantity': 1000,
        'trigger': {
            'type': 'purchase',
            'purchased': [
                {
                    'ticketId': i,
                    'quantity': 1,
                }
                for i in ids
            ],
        },
        'discount': 100,
        'discountType': 'percent',
        'appliesTo': list(ids),
        'maximumUsePerOrder': len(ids),
        'enabled': True,
    }
def generate_auto_discounts(**tickets):
    for i in range(len(tickets)):
        for keys in itertools.combinations(tickets.keys(), i+1):
            yield auto_discount(' & '.join(keys), *[tickets[k] for k in keys])

class HumanitixClient:
    default_headers = {
        'x-user-level-location': 'AU',
        'x-override-location': 'AU',
    }
    def __init__(self, token):
        self.token = token

    def get_date(self):
        return custom_strftime('%a {S} %b %Y, %I:%M %p AEDT', datetime.datetime.now())

    def get_events(self):
        res = requests.get(
            'https://console.humanitix.com/api/events/search',
            params={
                'page': 1,
                'sortOrder': 'newest',
                'filter': 'all',
                'loc': 'AU',
                'date': self.get_date(),
            },
            headers={
                'x-token': self.token,
                **self.default_headers,
            }
        )
        assert res.status_code >= 200 and res.status_code < 300, res.text
        return res.json()

    def get_event(self, event_id):
        res = requests.get(
            f'https://console.humanitix.com/api/events/{event_id}',
            headers={
                'x-token': self.token,
                **self.default_headers,
            },
        )
        assert res.status_code >= 200 and res.status_code < 300, res.text
        return res.json()

    def get_event_discount_codes(self, event_id):
        res = requests.get(
            f'https://console.humanitix.com/api/events/discount-codes/{event_id}',
            params={
                'page': 1,
            },
            headers={
                'x-token': self.token,
                **self.default_headers,
            },
        )
        assert res.status_code >= 200 and res.status_code < 300, res.text
        return res.json()
    
    def get_event_access_codes(self, event_id):
        res = requests.get(
            f'https://console.humanitix.com/api/events/access-codes/{event_id}',
            params={
                'page': 1,
            },
            headers={
                'x-token': self.token,
                **self.default_headers,
            },
        )
        assert res.status_code >= 200 and res.status_code < 300, res.text
        return res.json()

    def send_event_discounts_csv(self, event_id, applies_to, codes):
        res = requests.put(
            f'https://console.humanitix.com/api/events/discount-codes/upload/{event_id}',
            headers={
                'x-token': self.token,
                **self.default_headers,
            },
            files={
                'file': ('buff-events-vips.csv', '\n'.join(codes), 'text/csv'),
                'appliesTo': (None, applies_to),
                'enabled': (None, 'true'),
                'quantity': (None, '1'),
                'maximumUsePerOrder': (None, '1'),
                'discount': (None, '100'),
                'discountType': (None, 'percent'),
                'startDate': (None, 'undefined'),
                'endDate': (None, 'undefined'),
                'location': (None, 'AU'),
            },
        )
        assert res.status_code >= 200 and res.status_code < 300, res.text
        return res.json()

    def send_event_access_codes_csv(self, event_id, applies_to, codes):
        res = requests.put(
            f'https://console.humanitix.com/api/events/access-codes/upload/{event_id}',
            headers={
                'x-token': self.token,
                **self.default_headers,
            },
            files={
                'file': ('vips.csv', '\n'.join(codes), 'text/csv'),
                'appliesTo': (None, applies_to),
                'enabled': (None, 'true'),
            },
        )
        assert res.status_code >= 200 and res.status_code < 300, res.text
        return res.json()

    def send_auto_discounts(self, event_id, auto_discounts):
        res = requests.post(
            f'https://console.humanitix.com/api/events/{event_id}',
            headers={
                'x-token': self.token,
                **self.default_headers,
            },
            json={
                'autoDiscounts': auto_discounts,
            },
        )
        assert res.status_code >= 200 and res.status_code < 300, res.text
        return res.json()

def main():
    try:
        usersettings = get_usersettings()
    except FileNotFoundError:
        print('No usersettings.json found', file=sys.stderr)
        print('  The file must be in the format {"refresh_token": <STRING>, "codes": [...<STRING>], "prefixes": [...<STRING>]}', file=sys.stderr)
        print('  The refresh token may be obtained by pasting the following into the Humanitix producer console:', file=sys.stderr)
        print("  (() => { dbReq = indexedDB.open('firebaseLocalStorageDb'); dbReq.onsuccess = () => { dataReq = dbReq.result.transaction('firebaseLocalStorage').objectStore('firebaseLocalStorage').getAll(); dataReq.onsuccess = () => { console.log(dataReq.result[0].value.stsTokenManager.refreshToken) }; dataReq.onerror = console.error }; dbReq.onerror = console.error })()", file=sys.stderr)
        return

    try:
        settings = get_settings()
    except FileNotFoundError:
        print('No settings.json found', file=sys.stderr)
        print('  Run get-settings.py to generate it', file=sys.stderr)
        return

    token = get_token(settings['FIREBASE_API_KEY'], usersettings['refresh_token'])
    client = HumanitixClient(token['id_token'])

    try:
        with open('state.json', 'r') as f:
            state = json.load(f)
    except FileNotFoundError:
        state = {}

    for event in client.get_events()['events']:
        for prefix in usersettings['prefixes']:
            if event['name'].lower().startswith(prefix.lower()):
                print(f'Processing {event["name"]}...')

                vip_tickets = [t for t in event['ticketTypes'] if 'vip' in t['name'].lower()]
                vip_ticket_ids = ','.join([t['_id'] for t in vip_tickets])

                other_discounts = [i for i in event['autoDiscounts'] if not i['code'].startswith('[AUTO]')]
                our_discounts = [i for i in generate_auto_discounts(**{t['name']: t['_id'] for t in vip_tickets})]

                wanted_discounts =  other_discounts + our_discounts
                current_discounts_cmp = deepcopy(event['autoDiscounts'])
                for i in current_discounts_cmp:
                    del i['_id']
                    del i['trigger']['_id']
                    for j in i['trigger']['purchased']:
                        del j['_id']

                if wanted_discounts != current_discounts_cmp:
                    print('  Updating auto discounts...')
                    client.send_auto_discounts(event['eventId'], other_discounts + our_discounts)

                if state.setdefault('events', {}).setdefault(event['eventId'], False):
                    print(f'  Already processed access codes')
                    continue
                else:
                    print('  Sending access codes...')
                    # client.send_event_discounts_csv(event['eventId'], vip_ticket_ids, usersettings['codes'])
                    client.send_event_access_codes_csv(event['eventId'], vip_ticket_ids, usersettings['codes'])

                state['events'][event['eventId']] = True
                with open('state.json', 'w') as f:
                    json.dump(state, f, indent=4)

    # pprint(client.get_events()['events'][0])

if __name__ == '__main__':
    main()
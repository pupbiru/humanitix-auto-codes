#!/usr/bin/env python3

import json
import re
import requests

from bs4 import BeautifulSoup

def get_settings():
    res = requests.get('https://console.humanitix.com/scripts/browserConfig.js')
    settings_json = re.search(r'window\.config\s*=\s*(\{.*\})', res.text).group(1)
    return json.loads(settings_json)

def main():
    with open('settings.json', 'w') as f:
        json.dump(get_settings(), f, indent=4)

if __name__ == '__main__':
    main()
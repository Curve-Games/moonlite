import concurrent.futures
import threading
import time
from typing import Any, Dict, List
import browser_cookie3
import json
from bs4 import BeautifulSoup
import requests
from urllib.parse import unquote, urlparse
from pathlib import PurePosixPath

from moonlite.utils.text import ask_browser
from moonlite.utils.browsers import BrowserTypes

COOKIES_REQUIRED_PREFIXES = {"sessionid", "steamLoginSecure", "steamMachineAuth"}
STEAM_DASHBOARDS = {
    ''
}

class CookiesNotFound(Exception):
    pass

def get_cookies(browser_type: BrowserTypes) -> dict:
    tries = 3
    while tries:
        cj = getattr(browser_cookie3, browser_type.name.lower())()
        cookies = {}
        for cookie in cj:
            if cookie.domain == 'partner.steamgames.com' and (cookie.name.startswith('steam') or cookie.name == 'sessionid') and cookie not in cookies:
                cookies[cookie.name] = cookie.value

        if all(any(cookie.startswith(check) for cookie in cookies) for check in COOKIES_REQUIRED_PREFIXES):
            break
        else:
            print('ERROR: Could not find all cookies required. Try refreshing partner.steamgames.com. Trying again...')
            tries -= 1

    if not tries:
        raise CookiesNotFound('ERROR: Could not find all cookies required. Try refreshing partner.steamgames.com.')
    print('Found the following cookies from partner.steamgames.com:')
    print(json.dumps(cookies, sort_keys=True, indent=4))
    return cookies

def get_apps(cookies: dict, store_pages_only: bool = True) -> List[Dict[str, Any]]:
    """Gets all apps from the partner.steamgames.com dashboard.

    Args:
        cookies: a dictionary of cookies so that partner.steamgames.com can be accessed. See get_cookies.
        store_pages_only: whether or not to get apps with store pages available or to get all apps (default: True).

    Returns:
        A list of dictionaries which includes the appid, name and type of each app scraped.
    """
    # Fetch the apps page
    soup = BeautifulSoup(requests.get('https://partner.steamgames.com/apps/', cookies=cookies).content, 'html.parser')
    header2 = soup.find('h2', text='View and search all apps:')
    app_rows = header2.find_next_siblings('div', {'class': 'recent_app_row'})
    apps = []
    for app_row in app_rows:
        # If the store_pages_only flag is set we find the app links divider and check whether there are 2 or more links available.
        # These essentially filters out any "test" or unpublished apps which will not have much data anyway.
        if store_pages_only:
            links = app_row.find_next('div', {'class': 'recent_app_links'}).find_all('a')
            if len(links) < 2:
                continue

        # Find the name <a> tag
        name_a = app_row.find_next('div', {'class': 'recent_app_name'}).find('a')
        # Find the type divider
        type_div = app_row.find_next('div', {'class': 'recent_app_type'})
        # Construct the dictionary for the app
        app = {
            # Appid is the last element in the <a> tag's href so we parse the href and search for the last numeric string
            'appid': [int(part) for part in PurePosixPath(unquote(urlparse(name_a['href']).path)).parts if part.isnumeric()][-1],
            # Name is extracted from the <a> tag
            'name': name_a.get_text().strip(),
            # Type is extracted from the type divider
            'type': type_div.get_text().strip()
        }
        apps.append(app)
    return apps

def get_packages(cookies: dict, store_pages_only: bool = True, get_app_results: List[Dict[str, Any]] = None) -> Dict[int, int]:
    """Will first retrieve all the apps from the partner.steamgames.com dashboard (using get_apps), and will then use
    the Steam store API to retrieve all the packages that ARE BEING SOLD for that app.

    Args:
        cookies: a dictionary of cookies so that partner.steamgames.com can be accessed. See get_cookies.
        store_pages_only: whether or not to get apps with store pages available or to get all apps (default: True).
        get_app_results: pass in results from previous get_app call to remove the need for calling it again.

    Returns:
        A dictionary containing a mapping of packageids to appids.
    """
    apps = get_app_results
    if apps is None:
        apps = get_apps(cookies, store_pages_only)
    app_ids = [app['appid'] for app in apps]

    packages = dict()
    package_lock = threading.Lock()

    def app_thread(appid: int):
        soup = BeautifulSoup(requests.get(f'https://partner.steamgames.com/apps/associated/{appid}', cookies=cookies).content, 'html.parser')
        packageids = [
            [int(part) for part in PurePosixPath(
                unquote(urlparse(row.find('a', attrs={'href': True})['href']).path)
            ).parts if part.isnumeric()][-1] for row in soup.find(
                'div',
                text='Store packages'
            ).parent.find_all(
                'div',
                attrs={'class': 'tr released'}
            )
        ]

        with package_lock:
            for packageid in packageids:
                packages[packageid] = appid

    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        pool.map(app_thread, app_ids)
    return packages

if __name__ == '__main__':
    start = time.time()
    cookies = get_cookies(ask_browser())
    apps = get_apps(cookies)
    print('apps:')
    print(json.dumps(apps, sort_keys=True, indent=4))

    packages = get_packages(cookies, get_app_results=apps)
    print('packages:')
    print(json.dumps(packages, sort_keys=True, indent=4))
    print('Fetching took:', time.time() - start)

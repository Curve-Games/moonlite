import threading
import re
from typing import Dict, Type
import requests
from datetime import date, timedelta, datetime
from bs4 import BeautifulSoup
from pathlib import Path
import concurrent.futures
import traceback
from tqdm import tqdm

from moonlite.scrape.progress import Progress, StopException, get_exec_results
from moonlite.utils.time import DATE_FORMAT, DATE_FORMAT_FILE
from moonlite.utils.text import ask_browser, ask_date
from moonlite.utils.dashboard import get_apps, get_cookies
from moonlite.utils.browsers import BrowserTypes

BROWSER_TYPES = [
    'Chrome',
    'Firefox',
    'Opera',
    'Edge',
    'Chromium',
]

_DATA_VISITS_VAR = re.compile(r'var dataViews = (\[.*?\]);', re.MULTILINE | re.DOTALL)
_MIN_DATE_PROPERTY = re.compile(r'minDate: \'(.*?)\',', re.MULTILINE | re.DOTALL)

def _find_data_script_elements(soup: BeautifulSoup) -> list:
    """
    Finds all the script elements containing a variable named data

    Args:
        soup: the soup to use to find the elements

    Returns:
        The list of all script elements containing a variable named "data" (should only be 1)
    """
    return list(filter(lambda script: bool(_DATA_VISITS_VAR.search(str(script.string))), soup.find_all('script')))

def insights_scrape(
        output: Path,
        browser_type: BrowserTypes,
        from_date: date,
        to_date: date,
        progress: Type[Progress],
        stop: threading.Event = None
):
    if stop is None:
        stop = threading.Event()

    # Then we get the cookies from the browser
    try:
        cookies = get_cookies(browser_type)
        apps = get_apps(cookies)
        app_lookup = {app['appid']: app['name'] for app in apps}
        print(f'Found {len(app_lookup)} Curve apps')
    except Exception as e:
        progress(0, 0, 0, 0, 0, 0, e)
        return

    # Start a thread for each game
    def app_thread(appid: int, ord: int, out_of: int):
        if stop.is_set():
            raise StopException

        yesterdays_soup = BeautifulSoup(
            requests.get(
                f'https://partner.steamgames.com/apps/navtrafficstats/{appid}/?attribution_filter=all&preset_date_range=yesterday',
                cookies=cookies
            ).content,
            'html.parser'
        )

        tries = 3
        while tries:
            data_script = _find_data_script_elements(yesterdays_soup)
            if len(data_script) == 1:
                # We set from date to be the maximum of either the minimum date possible or the given from_date
                # This will make sure that we aren't requesting for data for days we don't actually have data for
                min_date: date = max(datetime.strptime(_MIN_DATE_PROPERTY.search(str(data_script[0].string)).groups()[0], DATE_FORMAT).date(), from_date)
                max_date: date = to_date
                break
            else:
                tries -= 1

        if not tries:
            raise Exception(f'Found {len(data_script)} scripts with a data variable inside them after trying 3 times. Try refreshing partner.steamgames before contacting admin.')

        # Create directory
        app_save_location = output.joinpath(str(appid))
        app_save_location.mkdir(parents=True, exist_ok=True)

        def csv_thread(current_date: date):
            current_date_str = current_date.strftime(DATE_FORMAT)
            # print(f'Fetching CSV for {appid} from {current_start_date_str} -> {current_end_date_str}')
            while True:
                # If stop is set then we stop the thread instantly
                if stop.is_set():
                    raise StopException

                try:
                    with requests.get(
                        f'https://partner.steamgames.com/apps/navtrafficstats/{appid}?attribution_filter=all&preset_date_range=custom&start_date={current_date_str}&end_date={current_date_str}&format=csv',
                        cookies=cookies,
                        stream=True,
                        timeout=10
                    ) as r:
                        filename = f'app_{appid}_all_{current_date.strftime(DATE_FORMAT_FILE)}_{current_date.strftime(DATE_FORMAT_FILE)}.csv'
                        path = str(app_save_location.joinpath(filename))
                        with open(path, 'wb') as f:
                            for line in r.iter_lines():
                                f.write(line+'\n'.encode())
                        # print('\tSaved to:', path)
                except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
                    # print(f'\tTimeout occurred whilst fetching CSV for {appid} from {current_start_date_str} -> {current_end_date_str}. Trying again...')
                    continue
                else:
                    break

        # We create 5 worker threads and add all the available days as jobs
        # days_start = time.time()
        days = (max_date - min_date).days + 1
        p = progress(appid, days, ord, out_of, min_date, max_date)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5, thread_name_prefix=f'Day executor for {appid}') as csv:
            csv_threads = [csv.submit(csv_thread, max_date - timedelta(days=x)) for x in range(days)]
            get_exec_results(
                futures=csv_threads,
                executor=csv,
                progress=p
            )
        p.close()
        # print(f'Scraped {len(csv_threads)} days for {appid} in {time_taken_seconds(time.time() - days_start)}\n')

    with concurrent.futures.ThreadPoolExecutor(max_workers=5, thread_name_prefix='App executor') as app:
        app_threads = [app.submit(app_thread, appid, i, len(app_lookup)) for i, appid in enumerate(app_lookup.keys())]
        try:
            get_exec_results(app_threads, app, progress)
        except StopException:
            pass
        except Exception as e:
            raise e

if __name__ == '__main__':
    print(
        '''Enter a start and end date for the scrape. This will apply to all apps found using the publisher API key.
The minimum date for the scrape for each app will be found by taking the maximum of either the minimum 
date possible for the app or the date that you will provide below. From date defaults to 01/01/2000 as 
this is just the value that Steam uses to signify the "beginning of time".
        '''
    )

    all_time = date(2000, 1, 1)
    yesterday = date.today() - timedelta(days=1)
    while True:
        from_date = ask_date('start scrape', all_time)
        to_date = ask_date('end scrape', yesterday)
        if from_date >= to_date:
            print(f'From date ({from_date.strftime(DATE_FORMAT)}) must be before to date ({to_date.strftime(DATE_FORMAT)})')
        else:
            break
    print('From date:', from_date.strftime(DATE_FORMAT))
    print('To date:', to_date.strftime(DATE_FORMAT))

    browser = ask_browser()

    progress: Dict[int, Progress] = dict()

    class TqdmProgress(Progress):
        def __init__(self, appid: int, days: int, ord: int, out_of: int, min_date: date, max_date: date, exception: Exception = None):
            self.progress = None
            if exception is None:
                self.progress = tqdm(total=days, desc=f'Progress for app {ord}/{out_of}: {appid} ({min_date.strftime(DATE_FORMAT)} -> {max_date.strftime(DATE_FORMAT)})')
                progress[appid] = self
            else:
                traceback.print_tb(exception.__traceback__)
                print(exception)
                for p in progress:
                    progress[p].close()

        def update(self, n: int = 1):
            self.progress.update(n)

        def close(self):
            self.progress.close()

    insights_scrape(Path('CSVs'), browser, from_date, to_date, TqdmProgress)

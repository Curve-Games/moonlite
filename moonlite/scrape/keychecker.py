import csv
import itertools
import os
import traceback
from pathlib import Path
import threading
import concurrent.futures
from typing import List, Type
import requests
from datetime import date
from slugify import slugify
from bs4 import BeautifulSoup
from tqdm import tqdm

from moonlite.scrape.progress import Progress, get_exec_results, StopException
from moonlite.utils.browsers import BrowserTypes
from moonlite.utils.text import ask_browser
from moonlite.utils.dashboard import get_cookies

BROWSER_TYPES = [
    'Chrome',
    'Firefox',
    'Opera',
    'Edge',
    'Chromium',
]

def keychecker(output: Path, browser_type: BrowserTypes, keys: List[str], progress: Type[Progress], stop: threading.Event = None):
    """Keychecker will scrape the querycdkey page of the Steamworks portal for each provided key. The table found on
    this page will be serialised and written to a CSV file located in the given output filepath.

    Args:
        output: the filepath of the output CSV containing the results of the query for each key.
        browser_type: the type of the browser to fetch cookies from.
        keys: a list of the keys to query.
        progress: the progress class, that when instantiated, will return data on the progress of the scrape back to the
                  caller.
        stop: a threading.Event that can be passed through to stop the scrape at any point (optional).
    """
    # Create a stop event if one wasn't provided.
    if stop is None:
        stop = threading.Event()

    # Then we get the cookies from the browser.
    try:
        keys = [key.replace('\n', '') for key in keys if key]
        cookies = get_cookies(browser_type)
    except Exception as e:
        progress(0, e)
        return

    if len(keys):
        print('Keys:')
        [print(f'\t{key}') for key in keys]
        print(f'Fetching {len(keys)} keys in parallel...')

        with open(str(output), 'w+') as f:
            writer = csv.writer(f)
            # A lock that will need to be acquired by every worker thread to write to the output CSV.
            write_lock = threading.Lock()
            # This is an event that is global to every thread within ThreadPoolExecutor. If set it indicates that the
            # headers have been written to the output CSV and don't need to be written again.
            headers_written = threading.Event()

            # query_key is the target function for the ThreadPoolExecutor that will run the query for all the keys. It
            # takes the key as a string.
            def query_key(key: str) -> bool:
                if stop.is_set():
                    raise StopException

                try:
                    # We make a request to the querycdkey page with the given key, and parse the response HTML using
                    # BeautifulSoup.
                    soup = BeautifulSoup(requests.get(
                        f'https://partner.steamgames.com/querycdkey/cdkey?cdkey={key}&method=Query',
                        cookies=cookies
                    ).content, 'html.parser')

                    # We find all the table elements on this page.
                    tables = soup.find_all('table')
                    # We then collect the headers from each <th> element from the first two tables.
                    headers = [[header.get_text() for header in table.find('tr').find_all('th')] for i, table in enumerate(tables) if i < 2]
                    # And then collect the <td> elements themselves from the first two tables.
                    details = [[td.get_text() for td in table.find_all('tr')[1].find_all('td')] for i, table in enumerate(tables) if i < 2]
                    with write_lock:
                        # Write the header if it hasn't been written yet
                        if not headers_written.is_set():
                            writer.writerow(['Key'] + list(itertools.chain(*headers)))
                            headers_written.set()
                        # We then write a row containing the key as the lead value.
                        writer.writerow([key] + list(itertools.chain(*details)))
                except:
                    return False
                else:
                    return True

            p = progress(keys=len(keys))
            # We create a ThreadPoolExecutor, and then enqueue each key with the query_key function.
            with concurrent.futures.ThreadPoolExecutor(max_workers=10, thread_name_prefix='Keychecker executor') as executor:
                futures = [executor.submit(query_key, key) for key in keys]
                get_exec_results(
                    futures=futures,
                    executor=executor,
                    progress=p
                )
            p.close()
            rows_written = sum(1 for future in futures if future)
        print(f'Wrote {rows_written}/{len(keys)} key details to "{str(output)}"')

if __name__ == '__main__':
    # If you run this module it will have a command line based version of the keychecker tool.
    browser = ask_browser()

    path_or_list = input('Enter a comma seperated list of keys to check or the filepath to a text file with the keys: ')
    from_input = False
    keys = []
    if os.path.isfile(path_or_list):
        print('Given input was interpreted as a filepath')
        with open(path_or_list, 'r') as key_file:
            keys = [line.replace('\n', '') for line in key_file if line]
    else:
        keys = path_or_list.split(',')
        from_input = True
        print('Given input was interpreted as a comma seperated list of keys')

    class TqdmProgress(Progress):
        def __init__(self, keys: int, exception: Exception = None):
            if exception is None:
                self.progress = tqdm(total=keys, desc=f'Progress for {keys} keys')
            else:
                traceback.print_tb(exception.__traceback__)
                print(exception)
                self.close()

        def update(self, n: int = 1):
            self.progress.update(n)

        def close(self):
            self.progress.close()

    # f'{len(keys)}_keys_from_{"input" if from_input else slugify(path_or_list)}_{date.today().isoformat()}.csv'
    keychecker(Path(f'keys_from_{"input" if from_input else slugify(path_or_list)}_{date.today().isoformat()}.csv'), browser, keys, TqdmProgress)

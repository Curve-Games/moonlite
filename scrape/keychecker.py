import csv
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

from scrape.progress import Progress, get_exec_results, StopException
from utils.browsers import BrowserTypes
from utils.text import ask_browser
from utils.dashboard import get_cookies

BROWSER_TYPES = [
    'Chrome',
    'Firefox',
    'Opera',
    'Edge',
    'Chromium',
]

def keychecker(output: Path, browser_type: BrowserTypes, keys: List[str], progress: Type[Progress], stop: threading.Event = None):
    if stop is None:
        stop = threading.Event()

    # Then we get the cookies from the browser
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
            write_lock = threading.Lock()
            headers_written = threading.Event()

            def query_key(key: str) -> bool:
                if stop.is_set():
                    raise StopException

                try:
                    soup = BeautifulSoup(requests.get(f'https://partner.steamgames.com/querycdkey/cdkey?cdkey={key}&method=Query', cookies=cookies).content, 'html.parser')
                    tables = soup.find_all('table')
                    headers = [[header.get_text() for header in table.find('tr').find_all('th')] for table in tables]
                    details = [[td.get_text() for td in table.find_all('tr')[1].find_all('td')] for table in tables]
                    with write_lock:
                        if not headers_written.is_set():
                            writer.writerow(['Key'] + headers[0] + headers[1])
                            headers_written.set()
                        writer.writerow([key] + details[0] + details[1])
                except:
                    return False
                else:
                    return True

            p = progress(keys=len(keys))
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

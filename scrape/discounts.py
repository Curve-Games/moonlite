import concurrent.futures
import csv
import json
import threading
import traceback
from datetime import datetime
from pathlib import Path
from typing import Type

import pytz
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from scrape.progress import Progress, get_exec_results, StopException
from utils.browsers import BrowserTypes
from utils.dashboard import get_cookies, get_packages
from utils.text import ask_browser

CSV_HEADER = [
    'package',
    'app',
    'discount_id',
    'from_date',
    'to_date',
    'name',
    'description',
    'percentage',
    'amount',
    'quantity',
]

def discounts(
        output: Path,
        browser_type: BrowserTypes,
        progress: Type[Progress],
        stop: threading.Event = None
):
    if stop is None:
        stop = threading.Event()

    # Then we get the cookies from the browser
    try:
        cookies = get_cookies(browser_type)
        packages = get_packages(cookies)
        print(f'Found {len(set(packages.values()))} Curve apps and {len(packages)} packages')
    except Exception as e:
        progress(0, e)
        return

    file_lock = threading.Lock()

    with open(str(output), 'w+') as outfile:
        writer = csv.DictWriter(outfile, fieldnames=CSV_HEADER)
        writer.writeheader()

        def package_thread(packageid: int, appid: int):
            if stop.is_set():
                raise StopException

            soup = BeautifulSoup(requests.get(f'https://partner.steamgames.com/packages/discounts/{packageid}', cookies=cookies).content, 'html.parser')

            for row in soup.find_all('tr', attrs={'data-discount-data': True}):
                if stop.is_set():
                    raise StopException

                discount = json.loads(row['data-discount-data'])
                # We convert amount to a string so that we can insert a decimal point and convert to Decimal later
                discount['amount'] = str(discount.get('amount', '000'))
                obj = dict(
                    package=packageid,
                    app=appid,
                    discount_id=discount['id'],
                    # We parse the datetime from the timestamp and convert it to US/Pacific
                    from_date=datetime.fromtimestamp(discount['start_date']).astimezone(pytz.timezone('US/Pacific')).isoformat(),
                    to_date=datetime.fromtimestamp(discount['end_date']).astimezone(pytz.timezone('US/Pacific')).isoformat(),
                    name=discount['name'],
                    # We use the row element to find the description text
                    description=row.find('em').get_text(),
                    percentage=discount.get('percent', 0),
                    # Insert a decimal point 2 places before end and instantiate a Decimal instance
                    amount=discount['amount'][:-2] + '.' + discount['amount'][-2:],
                    quantity=discount.get('quantity', 1)
                )

                # Then we write the object to the file
                with file_lock:
                    writer.writerow(obj)

        packageids = list(packages.keys())
        print('Unwrapped packages:', packageids)
        p = progress(packages=len(packageids))
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
            futures = [pool.submit(package_thread, packageid, packages[packageid]) for packageid in packages]
            get_exec_results(
                futures=futures,
                executor=pool,
                progress=p
            )
        p.close()

if __name__ == '__main__':
    browser = ask_browser()

    class TqdmProgress(Progress):
        def __init__(self, packages: int, exception: Exception = None):
            if exception is None:
                self.progress = tqdm(total=packages, desc=f'Progress for {packages} packages')
            else:
                traceback.print_tb(exception.__traceback__)
                print(exception)
                self.close()

        def update(self, n: int = 1):
            self.progress.update(n)

        def close(self):
            self.progress.close()

    discounts(Path('CSVs/package_discounts.csv'), browser, TqdmProgress)

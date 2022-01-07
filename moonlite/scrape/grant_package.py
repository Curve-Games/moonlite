import concurrent.futures
import json
import threading
import time
import traceback
from itertools import product
from typing import List, Type

import requests
from tqdm import tqdm

from moonlite.scrape.progress import Progress, get_exec_results, StopException


def grant_package(
        steamids: List[str],
        packageids: List[int],
        publisher_key: str,
        progress: Type[Progress],
        stop: threading.Event = None
):
    if stop is None:
        stop = threading.Event()

    # The threading target. Will grant the given package to the given steamid.
    def grant(steamid: str, packageid: int):
        while True:
            if stop.is_set():
                raise StopException

            try:
                r = requests.post(
                    'https://partner.steam-api.com/ISteamUser/GrantPackage/v2/',
                    data={
                        'key': publisher_key,
                        'steamid': steamid,
                        'packageid': packageid
                    }
                ).json()
                print(json.dumps(r, sort_keys=True, indent=4))
            except:
                time.sleep(1)
            else:
                break

    # Find the cartesian product of steamids and packageids in order to "unwrap" the loop and make it so we only need
    # one thread pool
    relations = list(product(steamids, packageids))
    p = progress(grants=len(relations))
    with concurrent.futures.ThreadPoolExecutor(max_workers=10, thread_name_prefix='Grant package executor') as gp:
        futures = [gp.submit(grant, *relation) for relation in relations]
        get_exec_results(
            futures=futures,
            executor=gp,
            progress=p
        )
    p.close()

# 76561199186923348
# https://partner.steam-api.com/ISteamUser/GrantPackage/v2/?key=&steamid=&packageid=
if __name__ == '__main__':
    packagids = [int(p) for p in str(input('Enter package IDs to grant (seperated by commas): ')).split(',') if p.isnumeric()]
    steamids = str(input('Enter SteamIDs of users to grant packages to (seperated by commas): ')).split(',')
    publisher_key = str(input('Enter your publisher key: '))

    class TqdmProgress(Progress):
        def __init__(self, grants: int, exception: Exception = None):
            if exception is None:
                self.progress = tqdm(total=requests, desc=f'Progress for {grants} grants')
            else:
                traceback.print_tb(exception.__traceback__)
                print(exception)
                self.close()

        def update(self, n: int = 1):
            self.progress.update(n)

        def close(self):
            self.progress.close()

    grant_package(steamids, packagids, publisher_key, TqdmProgress)

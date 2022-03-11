import csv
import json
import re
import traceback
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

from moonlite.utils.browsers import BrowserTypes
from moonlite.utils.dashboard import Dashboards, get_apps
from moonlite.utils.scrape import bs_preprocess
from moonlite.utils.text import ask_date, ask_browser, ask_list
from moonlite.utils.time import DATE_FORMAT, DATE_FORMAT_FILE

GRAPH_NAMED_DATA = re.compile(r"(?:\$J\.jqplot\()\s*'(?P<name>\w+)'\s*,\s*(?P<data>\[.*])(?:\s*,\s*{)", re.MULTILINE)
GRAPH_LABELS = re.compile(r"label:\s*'(?P<label>[\s\w()-]+)'", re.MULTILINE | re.DOTALL)


def remote_play(output: Path, from_date: date, to_date: date, browser_type: BrowserTypes, apps: List[Dict[str, Any]] | None = None):
    # Then we get the cookies from the browser
    try:
        cookies = Dashboards.STEAMPOWERED.cookies(browser_type)
        if apps is None or not len(apps):
            apps = get_apps(Dashboards.STEAMGAMES.cookies(browser_type))
        app_lookup = {app['appid']: app['name'] for app in apps}
        print(f'Found {len(app_lookup)} Curve apps')
    except Exception as e:
        traceback.print_exc()
        print(e)
        return

    for app in apps:
        appid = app['appid']
        soup = BeautifulSoup(
            bs_preprocess(requests.get(
                f'https://partner.steampowered.com/app/remoteplay/{appid}/'
                f'?dateStart={from_date.isoformat()}'
                f'&dateEnd={to_date.isoformat()}',
                cookies=cookies
            ).text),
            'html.parser'
        )
        # The master dictionary that contains a mapping of days to graphs to metrics to values
        # {
        #     '2022-03-11': {
        #         'accounts_graph': {
        #             'Computer Users': 300,
        #             ...
        #         },
        #         'conversion_graph': {...},
        #         'sessions_graph': {...}
        #     }
        # }
        master = {}
        headers = ['Date']
        # Find the h2s for all graphs on the page which so happens to be all the h2s on the page
        h2s = soup.find_all('h2')
        assert len(h2s) == 3, 'Cannot find 3 "h2"s on the page. Target may have moved. Check cookies.'
        for h2 in h2s:
            script = h2.next_sibling
            assert script.name == 'script', 'Element after h2 tag is not a script. Target has moved.'

            # Find the name and data of the graph using the GRAPH_NAMED_DATA regular expression
            graph = GRAPH_NAMED_DATA.search(script.get_text()).groupdict()
            # We then reformat the data into a list of the datasets. Each dataset contains a mapping of dates to values
            # representing data points on the graph.
            graph['data'] = [
                {point[0]: point[1] for point in label}
                for label in json.loads(graph['data'].replace("'", '"'))
            ]
            # We then find the labels of the graph using the GRAPH_LABELS regular expression
            graph_labels = [label.group('label') for label in GRAPH_LABELS.finditer(script.get_text())]
            headers += [f'{graph["name"]}.{label}' for label in graph_labels]
            # We then zip the labels and the data into one list so that we can add to the master dict easily
            for label, data in zip(graph_labels, graph['data']):
                # We add the data points for each day to the master dict
                for day in data:
                    if day not in master:
                        master[day] = {graph['name']: {}}
                    elif graph['name'] not in master[day]:
                        master[day][graph['name']] = {}
                    master[day][graph['name']][label] = data[day]

        # Create directory
        app_save_location = output.joinpath(f'{appid} - {app["name"]}')
        app_save_location.mkdir(parents=True, exist_ok=True)

        print(json.dumps(master, sort_keys=True, indent=4))
        filename_suffix = f'{from_date.strftime(DATE_FORMAT_FILE)}_{to_date.strftime(DATE_FORMAT_FILE)}.csv'
        # Write the master graph data to a csv
        path = str(app_save_location.joinpath(f'app_{appid}_remote_play_graphs_{filename_suffix}'))
        with open(path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for day in sorted(master.keys()):
                writer.writerow({
                    header: master[day].get((hs := header.split('.'))[0], {}).get(hs[1], 0)
                    if header != 'Date' else day
                    for header in headers
                })

        # Then we also put the data in the table into a csv
        path = str(app_save_location.joinpath(f'app_{appid}_remote_play_table_{filename_suffix}'))
        table = soup.find('div', {'id': 'periodTable'}).find('table')
        headers = ['Metrics'] + [th.get_text() for th in table.find('tr').find_all('td') if th.get_text().strip()]
        with open(path, 'w') as f:
            wr = csv.writer(f)
            wr.writerow(headers)
            wr.writerows([
                [
                    td.get_text().split('(?)')[0].strip().replace('&nbsp', '')
                    for td in row.find_all("td")
                    if td.get_text().strip()
                ] for row in table.select("tr + tr")
            ])

if __name__ == '__main__':
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

    remote_play(
        output=Path('CSVs/remote_play'),
        from_date=from_date, to_date=to_date,
        browser_type=ask_browser()
    )

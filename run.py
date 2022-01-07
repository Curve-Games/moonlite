import logging
import sys
import time

from pyupdater.client import Client

import moonlite
from client_config import ClientConfig
from moonlite.main import Moonlite

logger = logging.getLogger(__name__)
STDERR_HANDLER = logging.StreamHandler(sys.stderr)
STDERR_HANDLER.setFormatter(logging.Formatter(logging.BASIC_FORMAT))

class UpdateStatus(object):
    """Enumerated data type"""
    # pylint: disable=invalid-name
    # pylint: disable=too-few-public-methods
    UNKNOWN = 0
    NO_AVAILABLE_UPDATES = 1
    UPDATE_DOWNLOAD_FAILED = 2
    EXTRACTING_UPDATE_AND_RESTARTING = 3
    UPDATE_AVAILABLE_BUT_APP_NOT_FROZEN = 4
    COULDNT_CHECK_FOR_UPDATES = 5

UPDATE_STATUS_STR = \
    ['Unknown', 'No available updates were found.',
     'Update download failed.', 'Extracting update and restarting.',
     'Update available but application is not frozen.',
     'Couldn\'t check for updates.']

status_info_dialog_callback = None
status_info_dialog_app = None

def status_info_dialog(info):
    # Retrieve the status from the info
    total = info.get(u'total')
    status = info.get(u'status')
    downloaded = info.get(u'downloaded')

    global status_info_dialog_callback
    global status_info_dialog_app
    if status_info_dialog_callback is None or status_info_dialog_app is None:
        status_info_dialog_app, status_info_dialog_callback = Moonlite.download(total)

    print(f'{downloaded} / {total} ({status})')
    status_info_dialog_callback(downloaded, status)
    if downloaded / total > 0.96:
        status_info_dialog_app.destroy()

def check_for_updates():
    """
    Check for updates.
    Channel options are stable, beta & alpha
    Patches are only created & applied on the stable channel
    """
    assert ClientConfig.PUBLIC_KEY is not None
    client = Client(ClientConfig())
    client.refresh()
    client.add_progress_hook(status_info_dialog)
    app_update = client.update_check(ClientConfig.APP_NAME, moonlite.__version__, channel='stable')
    if app_update:
        if hasattr(sys, "frozen"):
            downloaded = app_update.download()
            if downloaded:
                status = UpdateStatus.EXTRACTING_UPDATE_AND_RESTARTING
                logger.debug('Extracting update and restarting...')
                time.sleep(10)
                app_update.extract_restart()
            else:
                status = UpdateStatus.UPDATE_DOWNLOAD_FAILED
        else:
            status = UpdateStatus.UPDATE_AVAILABLE_BUT_APP_NOT_FROZEN
    else:
        status = UpdateStatus.NO_AVAILABLE_UPDATES
    return status

def run():
    """
    The main entry point.
    """
    status = check_for_updates()
    print(status)
    return Moonlite().run()

if __name__ == '__main__':
    run()

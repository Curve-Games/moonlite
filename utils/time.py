from datetime import timedelta

DATE_FORMAT = '%m/%d/%Y'
DATE_FORMAT_FILE = "%Y%m%d"

def time_taken_seconds(seconds: float) -> str:
    """Returns a string representation of the given number of seconds in HH:MM:SS format

    Will remove any microseconds

    Args:
        seconds (float): the number of seconds to convert

    Returns:
        str: the time in HH:MM:SS format
    """
    return str(timedelta(seconds=seconds)).split('.')[0]

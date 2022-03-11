import os
from datetime import date, datetime
from typing import Union, List
from moonlite.utils.browsers import BrowserTypes
from moonlite.utils.time import DATE_FORMAT

def ask_for(question: str, answers: list):
    answer = str(input(question + " " + str(answers) + ": ")).lower()
    while answer not in answers:
        print("Don't understand that input")
        answer = str(input(question + " " + str(answers))).lower()
    return answer if len(answers) > 2 else answers[0] == answer

def ask_date(date_meaning: str, default: date) -> Union[date, None]:
    input_str = f'Input the {date_meaning} date (format: {DATE_FORMAT.replace("%", "")}, leave empty for: {default.strftime(DATE_FORMAT)}): '
    date_input = str(input(input_str))
    while True:
        if date_input:
            try:
                d = datetime.strptime(date_input, DATE_FORMAT)
            except ValueError:
                print(f'Date must be in the format: {DATE_FORMAT}')
                date_input = str(input(input_str))
            else:
                break
        else:
            break
    return default if not date_input else d.date()

def ask_browser():
    print('Please open a browser, navigate to partner.steamgames.com and login.')
    print('If partner.steamgames.com is already open and logged into then please refresh the page.')

    for line_no in range(len(BrowserTypes)):
        print(str(line_no + 1) + ': ' + list(BrowserTypes)[line_no].name.strip('\n'))
    while True:
        try:
            line_no = int(input(('Which browser did you use to open the webpage? (enter number): ')))
            if line_no > len(BrowserTypes) or line_no - 1 < 0:
                print('List number is out of range. Try again.')
            else:
                if ask_for('Are you sure?', ['y', 'n']):
                    break
        except ValueError:
            print('Choice is not a integer. Try again.')
    return list(BrowserTypes)[line_no - 1]

def ask_list(things: str) -> List[str]:
    path_or_list = input(f'Enter a comma seperated list of {things} to check or '
                         f'the filepath to a text file with the {things}: ')
    l = []
    if os.path.isfile(path_or_list):
        print('Given input was interpreted as a filepath')
        with open(path_or_list, 'r') as key_file:
            l = [line.replace('\n', '') for line in key_file if line]
    else:
        l = path_or_list.split(',')
        print(f'Given input was interpreted as a comma seperated list of {things}')
    return l

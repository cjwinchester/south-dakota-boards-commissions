import os
from glob import glob
import time
from datetime import datetime
import csv

import requests
from bs4 import BeautifulSoup


REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36'  # noqa
}

HTML_DIR = 'member_pages'
CSV_FILE = 'sd-boards-and-commission-members.csv'


def get_board_ids():
    url = 'https://boardsandcommissions.sd.gov/SearchResults.aspx?Letter=ALL'

    r = requests.get(url, headers=REQUEST_HEADERS)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, 'html.parser')
    table = soup.find('table', {'id': 'gvResults'})

    ids = [int(x.get('href', '').split('=')[-1]) for x in table.find_all('a')]

    return ids


def download_member_pages(board_ids):
    for board_id in board_ids:
        filepath = os.path.join(
            HTML_DIR,
            f'{board_id}.html'
        )

        if os.path.exists(filepath):
            continue

        url = f'https://boardsandcommissions.sd.gov/boardmembers.aspx?BoardID={board_id}'  # noqa

        r = requests.get(url, headers=REQUEST_HEADERS)
        r.raise_for_status()
        time.sleep(1)

        with open(filepath, 'w', encoding='utf=8') as outfile:
            outfile.write(r.text)

        print(f'Downloaded {filepath}')

    return board_ids


def scrape_data():
    data = []

    field_map = {
        'bio': 'gvBoardMembers_lblAdditionalInfo',
        'city': 'gvBoardMembers_lblMemberCity',
        'name': 'gvBoardMembers_lblMemberFirstName',
        'term_end': 'gvBoardMembers_lblMemberTermEnd',
        'position': 'gvBoardMembers_lblMemberposition',
        'party': 'lblParty'
    }

    files = glob(f'{HTML_DIR}/*.html')

    for file in files:

        with open(file, 'r') as infile:
            html = infile.read()

        soup = BeautifulSoup(html, 'html.parser')

        board_div = soup.find('div', {'id': 'boardTitle'})

        board_link = board_div.find(
            'a',
            {'id': 'boardmenu_lnkBoard'}
        )

        board_name = ' '.join(board_link.text.split())
        board_url = board_link.get('href')

        board_phone = board_div.find(
            'a',
            {'id': 'boardmenu_contactCall'}
        )

        if board_phone:
            board_phone = board_phone.get('title')

        board_email = board_div.find(
            'a',
            {'id': 'boardmenu_contactEmail'}
        )

        if board_email:
            board_email = board_email.get('title')

        agency_affiliation_div = soup.find(
            'div',
            {'id': 'agencyAffiliation'}
        )

        agency_affiliation = ' '.join(
            agency_affiliation_div.text.split()
        ).lstrip('Agency Affiliation: ')

        agency_link = agency_affiliation_div.find('a')
        agency_url = ''

        if agency_link:
            agency_url = agency_link.get('href')

        table = soup.find('table', {'id': 'gvBoardMembers'})

        if not table:
            continue

        rows = table.find_all('tr')

        for row in rows:

            d = {
                'board_name': board_name,
                'board_website': board_url,
                'board_phone': board_phone,
                'board_email': board_email,
                'agency_affiliation': agency_affiliation,
                'agency_website': agency_url
            }

            picture, details = row.find_all('td')
            picture_url = None

            if picture.find('img'):
                picture_url = picture.find('img').get('src')

            d['picture_url'] = picture_url

            for field in field_map:
                span = details.find(
                    'span',
                    {
                        'id': lambda x: x and x.startswith(field_map[field])
                    }
                )

                if not span:
                    value = ''
                else:
                    value = ' '.join(span.text.split())

                    if field == 'bio':
                        value = value.lstrip('Biography:')

                        if value == 'Not Specified':
                            value = ''

                    if field == 'term_end':
                        try:
                            value = datetime.strptime(
                                value,
                                '%m/%d/%Y'
                            ).date().isoformat()
                        except ValueError:
                            value = ''

                d[field] = value

            data.append(d)

    return data


def write_csv(data, filepath):

    headers = [
        'board_name',
        'agency_affiliation',
        'name',
        'position',
        'city',
        'term_end',
        'party',
        'picture_url',
        'bio',
        'board_website',
        'board_phone',
        'board_email',
        'agency_website'
    ]

    with open(filepath, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.DictWriter(
            outfile,
            fieldnames=headers
        )

        writer.writeheader()
        writer.writerows(data)

    print(f'Wrote {filepath}')

    return filepath


if __name__ == '__main__':
    board_ids = get_board_ids()
    download_member_pages(board_ids)
    data = scrape_data()
    write_csv(data, CSV_FILE)

#!/usr/bin/env python


import argparse
import logging
import sys
from pathlib import Path

import gspread.utils
import xlsxwriter

GOOGLE_CREDENTIALS_FILE = Path(__file__).parent.parent / 'credentials' / 'google_service_account.json'
WORKSHEET_PATH = Path(__file__).parent.parent / 'data' / 'worksheets'

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(Path(__file__).name)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Download a Google Sheet as an XLSX file and store it in the `data/worksheets` directory.'
    )
    parser.add_argument('-s', '--sheet-url', type=str)
    args = parser.parse_args()
    return args.sheet_url


def clean_title(title: str) -> str:
    """Replace invalid characters in a spreadsheet or worksheet title with underscores.

    Parameters:
        title (str): The title to be cleaned.

    Returns:
        str: The cleaned title.
    """
    return ''.join(c if c.isalnum() else '_' for c in title)


if __name__ == '__main__':
    sheet_url = parse_args()
    google_client = gspread.service_account(filename=str(GOOGLE_CREDENTIALS_FILE.resolve()))

    try:
        spreadsheet = google_client.open_by_url(sheet_url)
    except gspread.exceptions.SpreadsheetNotFound:
        _logger.error(f'Google Sheet at "{sheet_url}" was not found.')
        sys.exit(1)

    WORKSHEET_PATH.mkdir(parents=True, exist_ok=True)
    with xlsxwriter.Workbook(WORKSHEET_PATH / f'{clean_title(spreadsheet.title)}.xlsx') as workbook:
        # Add a note to the workbook to indicate that it was generated by this script.
        workbook.add_worksheet('README').write(
            0, 0, f'This file was generated by {Path(__file__).name} and fetched from {sheet_url}.'
        )
        for worksheet in spreadsheet.worksheets():
            worksheet_data = worksheet.get_all_values()
            worksheet = workbook.add_worksheet(clean_title(worksheet.title))
            for row_index, row in enumerate(worksheet_data):
                for column_index, cell in enumerate(row):
                    worksheet.write(row_index, column_index, cell)

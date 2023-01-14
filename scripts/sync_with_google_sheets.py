#!/usr/bin/env python

import argparse
import logging
import sys
from pathlib import Path
from typing import Tuple, List, Any, Optional

import gspread
import pandas as pd

GOOGLE_CREDENTIALS_FILE = Path(__file__).parent.parent / 'credentials' / 'google_service_account.json'

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(Path(__file__).name)


def parse_args() -> Tuple[str, Path, str, int, bool, bool]:
    parser = argparse.ArgumentParser(description='Sync the submissions with Google Sheets.')
    parser.add_argument('subreddit', type=str, help='The subreddit to sync with.')
    parser.add_argument('google_sheet_url', type=str, help='The URL of the Google Sheet to sync with.')
    parser.add_argument('google_sheet_number', type=int, help='The number of the Google Sheet to sync with.')
    parser.add_argument(
        '-f',
        '--filename',
        type=str,
        help="The name of the JSON file that stores the data without the file suffix. Defaults to the "
             "lowercase name of the subreddit. For example, if the subreddit is 'r/Python', the default "
             "filename is 'r_python'.",
    )
    parser.add_argument(
        '-a',
        '--always-sync',
        action='store_true',
        help='Sync the data with Google Sheets even if the data is already synced.',
    )
    # add argument to resize columns
    parser.add_argument(
        '-r',
        '--resize-cols',
        action='store_true',
        help='Resize the columns to fit the data.',
    )
    args = parser.parse_args()
    filename = f'r_{args.filename or args.subreddit.lower()}.json'
    file_path = Path(__file__).parent.parent / 'data' / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)  # Create the directory if it doesn't exist.
    return args.subreddit, file_path, args.google_sheet_url, args.google_sheet_number, args.always_sync, args.resize_cols


def to_sheets_hyperlink(url: str, label: Optional[str] = None) -> str:
    """Turn a URL into a hyperlink.

    Parameters:
        url: The URL to turn into a hyperlink.
        label: The label of the hyperlink. If `None`, no label is used.

    Returns:
        The URL as a hyperlink.
    """
    if label is None:
        return f'=HYPERLINK("{url}")'
    else:
        return f'=HYPERLINK("{url}","{label}")'


# Parse the data for the Google Sheets API:
def parse_data_for_google_sheets(df: pd.DataFrame) -> List[List[Any]]:
    """Parse the data for the Google Sheets API.

    Parameters:
        df: The dataframe to parse.

    Returns:
        The parsed data.
    """
    # Copy the dataframe, so we don't modify the original.
    df = df.copy()
    # Remove non-research submissions.
    df = df[df['_is_research']]
    # Remove rows where `removed_by_category` is not `None`, i.e. where the submission has been removed.
    df = df[df['removed_by_category'].isna()]
    # Add 'https://www.reddit.com' to the beginning of the permalink.
    df['permalink'] = 'https://www.reddit.com' + df['permalink']
    # Turn both URL and permalink into hyperlinks.
    df['_real_url'] = df['_real_url'].apply(to_sheets_hyperlink)
    df['permalink'] = df['permalink'].apply(to_sheets_hyperlink)
    # Remove unwanted columns.
    header = ['title', '_real_url', 'permalink', 'link_flair_text', 'author_name', 'created_utc', '_summary', 'score']
    df = df[header]
    # Rename the columns.
    df = df.rename({
        'title': 'Title',
        '_real_url': 'URL',
        'permalink': 'Reddit Link',
        'link_flair_text': 'Flair',
        'author_name': 'Author',
        'created_utc': 'Date',
        '_summary': 'Summary',
    }, axis=1)
    # Fill `null` values with '—' (em dash).
    df = df.fillna(value='—')
    # Convert the dataframe to a list of lists.
    data = [df.columns.tolist()] + df.values.tolist()
    return data


if __name__ == '__main__':
    # Parse the command line arguments and read the subreddit's JSON file into a dataframe.
    subreddit, subreddit_path, sheet_url, sheet_number, always_sync, resize_cols = parse_args()
    df = pd.read_json(subreddit_path) if subreddit_path.exists() else pd.DataFrame()

    # Add the `synced_with_google_sheets` column if it does not exist yet and update `null` values to `False`.
    if '_synced_with_google_sheets' not in df.columns or always_sync:
        df['_synced_with_google_sheets'] = False
    df['_synced_with_google_sheets'] = df['_synced_with_google_sheets'].fillna(False)

    # Check if one of the submissions has not been synced with Google Sheets yet.
    if df['_synced_with_google_sheets'].all():
        _logger.info('Nothing to upload to Google Sheets...')
        sys.exit(0)
    else:
        _logger.info('Uploading new submissions to Google Sheets...')

    # Parse the data for the Google Sheets API.
    data = parse_data_for_google_sheets(df)

    # Connect to the Google Sheets API. If permission is denied, make sure that the Google service account has access
    # to the Google Sheet.
    try:
        google_client = gspread.service_account(filename=str(GOOGLE_CREDENTIALS_FILE.resolve()))
    except gspread.exceptions.APIError as e:
        _logger.exception(
            'Permission denied. Make sure that the Google service account has access to the Google Sheet.'
        )
        sys.exit(1)

    # Open the Google Sheet.
    try:
        spreadsheet = google_client.open_by_url(sheet_url)
    except gspread.exceptions.SpreadsheetNotFound:
        _logger.error(f'Google Sheet at "{sheet_url}" was not found.')
        sys.exit(1)

    # Get the Google Sheet's worksheet or create a new one if it doesn't exist yet.
    try:
        worksheet = spreadsheet.get_worksheet(sheet_number)
    except gspread.exceptions.WorksheetNotFound:
        _logger.info(f'Creating a new worksheet at {sheet_url} with sheet number {sheet_number}...')
        worksheet = spreadsheet.add_worksheet(title=f'{subreddit}', rows='1000', cols='26')

    # Send the data to the Google Sheets API.
    response = worksheet.clear()
    _logger.debug(f'Google Sheets API response: {response}')
    worksheet.format(f'A1:Z{len(data)}', {'horizontalAlignment': 'LEFT'})
    response = worksheet.format(f'A2:Z{len(data)}', {'textFormat': {'bold': False}})
    _logger.info(f'Google Sheets API response: {response}')
    response = worksheet.format('A1:Z1', {'textFormat': {'bold': True, 'underline': True}})
    _logger.info(f'Google Sheets API response: {response}')
    response = worksheet.resize(rows=len(data), cols=len(data[0]))
    _logger.info(f'Google Sheets API response: {response}')
    response = worksheet.update('A1', data, value_input_option='USER_ENTERED')
    _logger.info(f'Google Sheets API response: {response}')

    if resize_cols:
        # The following code ensures that the columns are resized to fit the content.
        _logger.info('Resizing columns...')
        body = {
            'requests': [
                {
                    'autoResizeDimensions': {
                        'dimensions': {
                            'sheetId': worksheet._properties['sheetId'],
                            'dimension': 'COLUMNS',
                            'startIndex': 0,
                            'endIndex': len(data[0])
                        }
                    }
                }
            ]
        }
        response = spreadsheet.batch_update(body)
        _logger.info('Resizing columns done.')
        _logger.info(f'Google Sheets API response: {response}')

    # For all rows, set a new field `synced_with_google_sheets` to `True`.
    df['_synced_with_google_sheets'] = True

    # Write the updated dataframe back to the JSON file.
    df.to_json(subreddit_path, orient='records', indent=4)
    _logger.info('Done syncing with Google Sheets.')

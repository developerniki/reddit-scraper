#!/usr/bin/env python

import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Tuple, List, Dict, Any

import pandas as pd
import toml
from pyzotero import zotero, zotero_errors
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(Path(__file__).name)

with open(Path(__file__).parent.parent / 'credentials' / 'zotero_credentials.json') as f:
    ZOT_CRED = json.load(f)


def parse_args() -> Tuple[str, Path]:
    parser = argparse.ArgumentParser(description='Sync with Zotero.')
    parser.add_argument('subreddit', type=str, help='The subreddit to sync with.')
    parser.add_argument(
        '-f',
        '--filename',
        type=str,
        help="The name of the JSON file that stores the data without the file suffix. Defaults to the "
             "lowercase name of the subreddit. For example, if the subreddit is 'r/Python', the default "
             "filename is 'python'.",
    )
    args = parser.parse_args()
    filename = f'{args.filename or args.subreddit.lower()}.json'
    file_path = Path(__file__).parent.parent / 'data' / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)  # Create the directory if it doesn't exist.
    return args.subreddit, file_path


def parse_data_for_zotero(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Parse the data for Zotero.

    Skip the following submissions:
    - Submissions that have been removed (i.e., where `removed_by_category` is not `None`).
    - Submissions that are not research (i.e., where `_is_research` is `False`).
    - Submissions that have already been added (i.e., where `_synced_with_zotero` is `True`).
    - Submissions that raised an error last time (i.e., where `_zotero_sync_error` is not `None`).

    Parameters:
        df: The data to parse.

    Returns:
        A list of dictionaries, where each dictionary represents a Zotero item.
    """
    # Copy the dataframe, so we don't modify the original.
    df = df.copy()
    # Remove non-research submissions.
    df = df[df['_is_research']]
    # Remove rows where `removed_by_category` is not `None`, i.e. where the submission has been removed.
    df = df[df['removed_by_category'].isna()]
    # Remove rows where `metadata` is `NaN` or `None`.
    df = df[df['_metadata'].notna()]

    # Convert the metadata to a Zotero-friendly format.
    items = []
    for index, row in df.iterrows():
        if row['_synced_with_zotero'] or ('zotero_sync_error' in row and row['zotero_sync_error'].notna()):
            continue

        title = row['_metadata'].get('title')
        title = title[0] if title and len(title) > 0 else row['title']
        creators = row['_metadata'].get('author') or []
        creators = [
            {
                'creatorType': 'author',
                'firstName': creator.get('given'),
                'lastName': creator.get('family'),
            }
            for creator in creators
        ]
        date = row['_metadata']['issued']['date-parts'][0][0] if 'issued' in row['_metadata'] else None
        url = row['url']
        doi = row['_metadata'].get('DOI')
        abstract = row['_metadata'].get('abstract')

        # Handle preprints, theses, journal articles, book sections, and conference papers.
        paper_type_to_item_type = defaultdict(lambda: 'journalArticle')
        paper_type_to_item_type.update({
            'thesis': 'thesis',
            'book-section': 'bookSection',
            'conference-paper': 'conferencePaper'
        })
        reddit_paper_type = row['_metadata'].get('type')
        paper_type = row['_metadata']['type'] or reddit_paper_type
        item_type = paper_type_to_item_type[paper_type]
        extra = {
            'reddit_link': row['permalink'],
            'summary': row['_summary'],
            'paper_type': paper_type,
            'reddit_paper_type': reddit_paper_type,
        }
        # leave a blank line between every entry
        extra = toml.dumps(extra)

        item = {
            'itemType': item_type,
            'title': title,
            'creators': creators,
            'date': date,
            'url': url,
            'DOI': doi,
            'abstractNote': abstract,
            'extra': extra,
        }

        if item_type == 'thesis':
            item['university'] = row['_metadata'].get('publisher')
        elif item_type == 'bookSection':
            item['bookTitle'] = row['_metadata'].get('container-title')
        elif item_type == 'conferencePaper':
            event = row['_metadata'].get('event')
            item['conferenceName'] = event and event.get('name')

        items.append(item)

    return items


if __name__ == '__main__':
    _logger.info('Uploading to Zotero...')
    subreddit, subreddit_path = parse_args()
    df = pd.read_json(subreddit_path)

    # Add the `_synced_with_zotero` column if it does not exist yet and update `null` values to `False`.
    if '_synced_with_zotero' not in df.columns:
        df['_synced_with_zotero'] = False
    df['_synced_with_zotero'] = df['_synced_with_zotero'].fillna(False)

    # Add the `_zotero_sync_error` column if it does not exist yet.
    if '_zotero_sync_error' not in df.columns:
        df['_zotero_sync_error'] = None

    # Parse the data for Zotero.
    items = parse_data_for_zotero(df)

    # Initialize the Zotero library.
    zot = zotero.Zotero(**ZOT_CRED)

    # Upload items to Zotero, 50 at a time.
    _logger.info(f'Uploading {len(items)} items to Zotero in batches of 50...')
    batch = 50
    with tqdm(total=len(items)) as pbar:
        for i in range(0, len(items), batch):
            j = min(i + batch, len(items))

            try:
                cur_items = zot.check_items(items[i:j])
            except zotero_errors.InvalidItemFields:
                _logger.exception('Invalid item fields.')
                sys.exit(1)

            try:
                resp = zot.create_items(cur_items)

                for key, _val in resp['success'].items():
                    # Set the `_synced_with_zotero` column to `True` for the uploaded items.
                    row = int(key) + i
                    df.loc[row, '_synced_with_zotero'] = True

                for key, val in resp['failed'].items():
                    _logger.error(f'Failed to upload item {key} with response {val}.')
                    # Set the `zotero_sync_error` column to the error message of the failed items.
                    row = int(key) + i
                    df.at[row, '_zotero_sync_error'] = val
            except zotero_errors.UserNotAuthorised:
                _logger.error(
                    f'User not authorized to upload to the Zotero library with ID {ZOT_CRED["library_id"]}. Please check '
                    f'your credentials in the file "credentials/zotero_credentials.json" and the permissions of your API '
                    f'key at "https://www.zotero.org/settings/keys".'
                )
                sys.exit(1)
            except zotero_errors.HTTPError:
                _logger.exception('HTTP error.')
                sys.exit(1)

            pbar.update(j - i)

    # Save the updated dataframe to indicate that the items have been synced to Zotero.
    df.to_json(subreddit_path, orient='records', indent=4)
    _logger.info('Done syncing with Zotero.')

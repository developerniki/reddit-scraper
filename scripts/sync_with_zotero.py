#!/usr/bin/env python

import argparse
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from typing import Tuple, List, Dict, Any

import pandas as pd
from pyzotero import zotero, zotero_errors
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(Path(__file__).name)

with open(Path(__file__).parent.parent / 'credentials' / 'zotero_credentials.json') as f:
    ZOTERO_API_KEY = json.load(f)['api_key']


def parse_args() -> Tuple[str, Path, str, str]:
    parser = argparse.ArgumentParser(description='Sync with Zotero.')
    parser.add_argument('subreddit', type=str, help='The subreddit to sync with.')
    parser.add_argument(
        'library_type',
        type=str,
        help="The type of the library to sync with. Defaults to the library type stored in the credentials file.",
    )
    parser.add_argument(
        'library_id',
        type=str,
        help="The ID of the library to sync with. Defaults to the library ID stored in the credentials file.",
    )
    parser.add_argument(
        '-f',
        '--filename',
        type=str,
        help="The name of the JSON file that stores the data without the file suffix. Defaults to the "
             "lowercase name of the subreddit. For example, if the subreddit is 'r/Python', the default "
             "filename is 'r_python'.",
    )
    args = parser.parse_args()
    filename = f'r_{args.filename or args.subreddit.lower()}.json'
    file_path = Path(__file__).parent.parent / 'data' / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)  # Create the directory if it doesn't exist.
    return args.subreddit, file_path, args.library_type, args.library_id


def parse_data_for_zotero(zot: zotero.Zotero, df: pd.DataFrame, collection_map: Dict[str, str]) -> List[Dict[str, Any]]:
    """Parse the data for Zotero.

    Skip the following submissions:
    - Submissions that have been removed (i.e., where `removed_by_category` is not `None`).
    - Submissions that are not research (i.e., where `_is_research` is `False`).
    - Submissions that have already been added (i.e., where `_synced_with_zotero` is `True`).
    - Submissions that raised an error last time (i.e., where `_zotero_sync_error` is not `None`).

    Parameters:
        zot: The Zotero instance.
        df: The data to parse.
        collection_map: A mapping from collection names to collection keys.

    Returns:
        A list of dictionaries, where each dictionary represents a Zotero item.
    """
    # Copy the dataframe, so we don't modify the original.
    df = df.copy()
    # Remove non-research submissions.
    df = df[df['_is_research']]
    # Remove rows where `removed_by_category` is not `None`, i.e. where the submission has been removed.
    df = df[df['removed_by_category'].isna()]

    # Convert the metadata to a Zotero-friendly format.
    items = []
    for index, row in df.iterrows():
        already_synced = row['_synced_with_zotero']
        errored_last_time = row['_zotero_sync_error'] is not None
        if already_synced or errored_last_time:
            continue

        link_flair_text = row['link_flair_text'] if row['link_flair_text'] != 'Criminal Justice' else 'Criminology'
        collections = [collection_map.get(link_flair_text, collection_map['Uncategorized'])]

        if row['_metadata'] is None:
            item = {
                'itemType': 'document',
                'collections': collections,
                'title': row['title'],
                'url': row['_real_url'],
                'accessDate': row['created_utc'],
                'extra': json.dumps({
                    'paper_type': '',
                    'reddit_title_paper_type': row['_paper_type'],
                    'reddit_link': row['permalink'],
                    'reddit_title': row['title'],
                    'reddit_author': row['author_name'],
                    'reddit_flair': row['link_flair_text'],
                    'reddit_upvotes': row['score'],
                    'reddit_summary': row['_summary'],
                }, indent=2),
            }
        else:
            # Handle preprints, theses, journal articles, book sections, and conference papers.
            paper_type_to_item_type = defaultdict(lambda: 'journalArticle')
            paper_type_to_item_type.update({
                'thesis': 'thesis',
                'book-section': 'bookSection',
                'conference-paper': 'conferencePaper'
            })
            reddit_title_paper_type = row['_paper_type']
            paper_type = row['_metadata'].get('type') or reddit_title_paper_type
            item_type = paper_type_to_item_type[paper_type]

            title = row['_metadata'].get('title')
            title = title[0] if title and len(title) > 0 else row['title']
            creators = [{'creatorType': 'author', 'firstName': creator.get('given'), 'lastName': creator.get('family')}
                        for creator in row['_metadata'].get('author') or []
                        if creator.get('given') and creator.get('family')]
            publication_title = row['_metadata'].get('container-title')
            publication_title = ', '.join(publication_title) if publication_title else None
            volume = row['_metadata'].get('volume')
            issue = row['_metadata'].get('issue')
            pages = row['_metadata'].get('page')
            date = row['_metadata'].get('issued')
            date = date['date-parts'][0] if date and 'date-parts' in date else None
            date = '-'.join(map(str, date)) if date else None
            journal_abbreviation = row['_metadata'].get('short-container-title')
            journal_abbreviation = ', '.join(journal_abbreviation) if journal_abbreviation else None
            language = row['_metadata'].get('language')
            doi = row['_metadata'].get('DOI')
            issn = row['_metadata'].get('ISSN')
            issn = ', '.join(issn) if issn else None
            short_title = row['_metadata'].get('short-title')
            short_title = ', '.join(short_title) if short_title else None
            url = row['_real_url'] or row['_metadata'].get('URL')
            access_date = row['created_utc']
            extra = json.dumps({
                'paper_type': paper_type,
                'reddit_title_paper_type': reddit_title_paper_type,
                'reddit_link': row['permalink'],
                'reddit_title': row['title'],
                'reddit_author': row['author_name'],
                'reddit_flair': row['link_flair_text'],
                'reddit_upvotes': row['score'],
                'reddit_summary': row['_summary'],
            }, indent=2)
            tags = [{'tag': tag} for tag in row['_metadata'].get('subject') or []]
            abstract = row['_metadata'].get('abstract')

            item = {
                'itemType': item_type,
                'collections': collections,
                'title': title,
                'creators': creators,
                'publicationTitle': publication_title,
                'volume': volume,
                'issue': issue,
                'pages': pages,
                'date': date,
                'journalAbbreviation': journal_abbreviation,
                'language': language,
                'DOI': doi,
                'ISSN': issn,
                'shortTitle': short_title,
                'url': url,
                'accessDate': access_date,
                'extra': extra,
                'tags': tags,
                'abstractNote': abstract,
            }

            valid_keys = zot.item_template(item_type).keys()
            item = {key: value for key, value in item.items() if key in valid_keys}

            if item_type == 'thesis':
                item['university'] = row['_metadata'].get('publisher')
            elif item_type == 'bookSection':
                item['bookTitle'] = row['_metadata'].get('container-title')
            elif item_type == 'conferencePaper':
                event = row['_metadata'].get('event')
                item['conferenceName'] = event and event.get('name')

        items.append(item)

    return items


def add_sync_cols(df: pd.DataFrame):
    """Add the columns that are used to keep track of the sync status to the dataframe."""
    # Add the `_synced_with_zotero` column if it does not exist yet and update `null` values to `False`.
    if '_synced_with_zotero' not in df.columns:
        df['_synced_with_zotero'] = False
    df['_synced_with_zotero'] = df['_synced_with_zotero'].fillna(False)

    # Add the `_zotero_sync_error` column if it does not exist yet.
    if '_zotero_sync_error' not in df.columns:
        df['_zotero_sync_error'] = None


if __name__ == '__main__':
    _logger.info('Uploading to Zotero...')
    subreddit, subreddit_path, library_type, library_id = parse_args()
    df = pd.read_json(subreddit_path)

    # Add the columns that are used to keep track of the sync status to the dataframe.
    add_sync_cols(df)

    # Initialize the Zotero library.
    zot = zotero.Zotero(library_id=library_id, library_type=library_type, api_key=ZOTERO_API_KEY)

    # Get the sub-collections of the library.
    collections = zot.collections()
    collection_map = {collection['data']['name']: collection['data']['key'] for collection in collections}

    # Parse the data for Zotero.
    items = parse_data_for_zotero(zot, df, collection_map)

    # Get current items in the library.
    existing_items = defaultdict(list)
    for i, item in enumerate(zot.everything(zot.items())):
        try:
            existing_items[json.loads(item['data']['extra'])['reddit_link']].append(item)
        except (json.JSONDecodeError, KeyError):
            continue

    # Check if the item already exists in the library; if yes, take its `key` and `version`.
    for i, item in enumerate(items):
        # Compare Reddit permalinks in the `extra` field by parsing the JSON.
        matches = existing_items.get(json.loads(item['extra'])['reddit_link'])
        if matches:
            m = matches[0]
            if m := m.get('data'):
                item['key'] = m['key']
                item['version'] = m['version'] + 1

    # Upload items to Zotero, 50 at a time.
    _logger.info(f'Uploading {len(items)} items to Zotero in batches of 50...')
    batch = 50
    total_created, total_updated, total_failed = 0, 0, 0
    with tqdm(total=len(items)) as pbar:
        for i in range(0, len(items), batch):
            j = min(i + batch, len(items))

            try:
                item_batch = zot.check_items(items[i:j])
            except zotero_errors.InvalidItemFields:
                _logger.exception('Invalid item fields.')
                sys.exit(1)

            try:
                resp = zot.create_items(item_batch)

                for k, v in resp['success'].items():
                    permalink = json.loads(item_batch[int(k)]['extra'])['reddit_link']
                    df.loc[df['permalink'] == permalink, '_synced_with_zotero'] = True
                    df.loc[df['permalink'] == permalink, '_zotero_sync_error'] = None

                for k, v in resp['unchanged'].items():
                    permalink = json.loads(item_batch[int(k)]['extra'])['reddit_link']
                    df.loc[df['permalink'] == permalink, '_synced_with_zotero'] = True
                    df.loc[df['permalink'] == permalink, '_zotero_sync_error'] = None

                for k, v in resp['failed'].items():
                    # Set the `zotero_sync_error` column to the error message of the failed items.
                    permalink = json.loads(item_batch[int(k)]['extra'])['reddit_link']
                    _logger.error(f'Failed to upload item with permalink {permalink} to Zotero: {v}')
                    df.loc[df['permalink'] == permalink, '_zotero_sync_error'] = v

                total_created += len(resp['success'])
                total_updated += len(resp['unchanged'])
                total_failed += len(resp['failed'])
            except zotero_errors.UserNotAuthorised:
                _logger.error(
                    f'User not authorized to upload to the Zotero library with ID {library_id}. Please check your '
                    f'credentials in the file "credentials/zotero_credentials.json" and the permissions of your API '
                    f'key at "https://www.zotero.org/settings/keys".'
                )
                sys.exit(1)
            except zotero_errors.HTTPError:
                _logger.exception('HTTP error.')
                sys.exit(1)

            pbar.update(j - i)

    # Save the updated dataframe to indicate that the items have been synced to Zotero.
    df.to_json(subreddit_path, orient='records', indent=4)
    _logger.info(
        f'Done syncing with Zotero. Summary: {total_created} created, {total_updated} updated, {total_failed} failed.'
    )

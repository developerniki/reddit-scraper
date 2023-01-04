#!/usr/bin/env python


import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Tuple

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(Path(__file__).name)


def parse_args() -> Tuple[str, Path, Path]:
    parser = argparse.ArgumentParser(
        description='The `create_manual_zotero_checklist.py` script creates a checklist of submissions that encountered '
                    'a failure when fetching metadata or syncing with Zotero in Markdown format. The to do boxes can '
                    'be checked off in a Markdown viewer to keep track of which submissions have been manually synced '
                    'with Zotero. This script takes this Markdown output and notes the submissions that have been '
                    'manually synced with Zotero into the respective file in the `data` directory.'
    )

    parser.add_argument('subreddit', type=str, help='The subreddit to fetch metadata for.')
    parser.add_argument(
        '-f',
        '--filename',
        type=str,
        help="The name of the JSON file that stores the data without the file suffix. Defaults to the lowercase name "
             "of the subreddit. For example, if the subreddit is 'r/Python', the default filename is 'python'.",
    )
    args = parser.parse_args()
    filename = f'{args.filename or args.subreddit.lower()}.json'
    submissions_file_path = Path(__file__).parent.parent / 'data' / filename
    submissions_file_path.parent.mkdir(parents=True, exist_ok=True)  # Create the directory if it doesn't exist.
    checklist_file_path = submissions_file_path.with_suffix('.checklist.md')

    return args.subreddit, submissions_file_path, checklist_file_path


if __name__ == '__main__':
    _logger.info('Noting manually synced submissions in the JSON file...')

    subreddit, submissions_file_path, checklist_file_path = parse_args()

    if not submissions_file_path.is_file():
        _logger.info(f'The file `{submissions_file_path}` does not exist. Aborting...')
        sys.exit(0)

    if not checklist_file_path.is_file():
        _logger.info(f'The file `{checklist_file_path}` does not exist. Aborting...')
        sys.exit(0)

    md = checklist_file_path.read_text()
    manually_synced = []
    for line in md.splitlines():
        pattern = r'( {2}| {4})- \[x\] (url=.+, )?permalink=https://www.reddit.com(?P<permalink>.+)(, error=".+")?'
        if permalink := re.fullmatch(pattern, line):
            manually_synced.append(permalink.group('permalink'))
    _logger.info(f'Found {len(manually_synced)} manually synced submissions...')

    submissions = json.loads(submissions_file_path.read_text()) if submissions_file_path.exists() else []
    for submission in submissions:
        if submission['permalink'] in manually_synced:
            print(f'Found manually synced submission: {submission["permalink"]}')
            submission['_manually_synced_with_zotero'] = True

    submissions_file_path.write_text(json.dumps(submissions, indent=4))
    _logger.info(f'Noted {len(manually_synced)} manually synced submissions in {submissions_file_path}.')

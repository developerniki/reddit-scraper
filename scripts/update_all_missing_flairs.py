#!/usr/bin/env python

import argparse
import json
import logging
from pathlib import Path
from typing import Tuple

from tqdm import tqdm

from utils import reddit_utils

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(Path(__file__).name)


def parse_args() -> Tuple[str, Path]:
    parser = argparse.ArgumentParser(description='Update all missing flairs.')
    parser.add_argument('subreddit', type=str, help='The subreddit to update flairs for.')
    parser.add_argument(
        '-f',
        '--filename',
        type=str,
        help="The name of the JSON file that stores the data without the file suffix. Defaults to the lowercase name "
             "of the subreddit. For example, if the subreddit is 'r/Python', the default filename is 'r_python'.",
    )
    args = parser.parse_args()
    filename = f'r_{args.filename or args.subreddit.lower()}.json'
    file_path = Path(__file__).parent.parent / 'data' / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)  # Create the directory if it doesn't exist.
    return args.subreddit, file_path


if __name__ == '__main__':
    _logger.info('Updating all missing flairs...')
    subreddit, file_path = parse_args()
    reddit = reddit_utils.get_reddit_client()

    submissions = [] if not file_path.exists() else json.loads(file_path.read_text())

    for submission in tqdm(submissions):
        if submission.get('link_flair_text') is None:
            updated_submission = reddit.submission(submission['id'])
            if submission['link_flair_text'] != updated_submission.link_flair_text:
                submission['link_flair_text'] = updated_submission.link_flair_text
                # Set the `synced_with_google_sheets` and `synced_with_zotero` flags to `False` to force a re-sync.
                submission['_synced_with_google_sheets'] = False
                submission['_synced_with_zotero'] = False

    file_path.write_text(json.dumps(submissions, indent=4))
    _logger.info('Done updating all missing flairs.')

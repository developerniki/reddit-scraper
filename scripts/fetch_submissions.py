#!/usr/bin/env python

import argparse
import json
import logging
from pathlib import Path
from typing import Tuple

from utils import reddit_utils

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(Path(__file__).name)


def parse_args() -> Tuple[str, Path]:
    parser = argparse.ArgumentParser(description='Fetch new submissions from a subreddit.')
    parser.add_argument('subreddit', type=str, help='The subreddit to fetch submissions from.')
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


if __name__ == '__main__':
    _logger.info('Fetching and storing new submissions...')
    subreddit, file_path = parse_args()
    reddit = reddit_utils.get_reddit_client()

    # Fetch new submissions and store them in a JSON file.
    old_submissions = json.loads(file_path.read_text()) if file_path.exists() else []
    most_recent_submission_id = old_submissions[0]['id'] if len(old_submissions) > 0 else None
    new_submissions = reddit_utils.fetch_submissions(reddit, subreddit, most_recent_submission_id)
    file_path.write_text(json.dumps(new_submissions + old_submissions, indent=4))
    _logger.info('Done fetching and storing new submissions.')

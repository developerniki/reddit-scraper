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


def parse_args() -> Tuple[str, Path, int]:
    parser = argparse.ArgumentParser(description='Fetch comments for all stored submissions.')
    parser.add_argument('subreddit', type=str, help='The subreddit to fetch comments for.')
    parser.add_argument(
        '-f',
        '--filename',
        type=str,
        help="The name of the JSON file that stores the data without the file suffix. Defaults to the "
             "lowercase name of the subreddit. For example, if the subreddit is 'r/Python', the default "
             "filename is 'r_python'.",
    )
    parser.add_argument('-m', '--max-comments', type=int, default=None, help='The maximum number of comments to expand '
                                                                             'per submission. If not specified, expand '
                                                                             'all comments.')
    args = parser.parse_args()
    filename = f'r_{args.filename or args.subreddit.lower()}.json'
    file_path = Path(__file__).parent.parent / 'data' / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)  # Create the directory if it doesn't exist.
    return args.subreddit, file_path, args.max_comments


if __name__ == '__main__':
    _logger.info('Fetching comments for submissions...')
    subreddit, file_path, max_comments = parse_args()
    reddit = reddit_utils.get_reddit_client()

    submissions = json.loads(file_path.read_text()) if file_path.exists() else []
    for submission in tqdm(submissions):
        # Only fetch comments for submissions that don't have any comments yet.
        if submission.get('comments') is None:
            submission['comments'] = reddit_utils.fetch_comments(reddit.submission(submission['id']),
                                                                 limit=max_comments)

    file_path.write_text(json.dumps(submissions, indent=4))
    _logger.info('Done fetching comments.')

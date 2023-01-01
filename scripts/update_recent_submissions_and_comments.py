#!/usr/bin/env python

import argparse
import json
import logging
from pathlib import Path
from typing import Tuple

from praw import Reddit
from tqdm import tqdm

from utils import reddit_utils

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(Path(__file__).name)


def parse_args() -> Tuple[str, Path, int, int]:
    parser = argparse.ArgumentParser(
        description='Update submissions and comments of the specified subreddit of the last n hours.'
    )
    parser.add_argument('subreddit', type=str, help='The subreddit to update submissions and comments for.')
    parser.add_argument(
        '-f', '--filename', type=str,
        help="The name of the JSON file that stores the data without the file suffix. Defaults to the lowercase name "
             "of the subreddit. For example, if the subreddit is 'r/Python', the default filename is 'python'."
    )
    parser.add_argument(
        '-n', '--hours', type=int, default=7 * 24, help='The last n hours to update submissions and comments for.'
    )
    parser.add_argument(
        '-m', '--max-comments', type=int, default=None,
        help='The maximum number of comments to expand per submission. If not specified, expand all comments.'
    )

    args = parser.parse_args()
    filename = f'{args.filename or args.subreddit.lower()}.json'
    file_path = Path(__file__).parent.parent / 'data' / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)  # Create the directory if it doesn't exist.
    return args.subreddit, file_path, args.hours, args.max_comments


def update_submission(reddit: Reddit, submission: dict, max_comments: int = None) -> None:
    updated_submission_unparsed = reddit.submission(submission['id'])
    updated_submission = reddit_utils.parse_submission(updated_submission_unparsed)
    updated_submission['comments'] = reddit_utils.fetch_comments(updated_submission_unparsed, limit=max_comments)
    # Update any changed fields.
    for key in updated_submission:
        if submission[key] != updated_submission[key]:
            # Set the `synced_with_google_sheets` and `synced_with_zotero` flags to `False` to force a re-sync.
            submission[key] = updated_submission[key]
            submission['_synced_with_google_sheets'] = False
            submission['_synced_with_zotero'] = False


if __name__ == '__main__':
    _logger.info('Updating recent submissions and their comments...')
    subreddit, file_path, hours, max_comments = parse_args()
    reddit = reddit_utils.get_reddit_client()

    submissions = json.loads(file_path.read_text()) if file_path.exists() else []

    for submission in tqdm(submissions):
        if reddit_utils.is_submission_created_in_last_n_hours(submission, hours):
            update_submission(reddit, submission, max_comments)

    file_path.write_text(json.dumps(submissions, indent=4))
    _logger.info('Done updating recent submissions.')

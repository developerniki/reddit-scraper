#!/usr/bin/env python

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any

from praw import Reddit
from praw.models import Submission
from tqdm import tqdm


def parse_args() -> Tuple[str, Path]:
    parser = argparse.ArgumentParser(description='Fetch new submissions from a subreddit.')
    parser.add_argument('subreddit', type=str, help='The subreddit to fetch submissions from.')
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
    file_path = Path(__file__).parents[1].absolute() / 'data' / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)  # Create the directory if it doesn't exist.
    return args.subreddit, file_path


def parse_submission(submission: Submission, datetime_fmt='%Y-%m-%d %H:%M:%S') -> Dict[str, Any]:
    submission_parsed = {
        'author_name': submission.author and submission.author.name,
        'author_flair_text': submission.author_flair_text,
        'comments': None,
        'created_utc': datetime.fromtimestamp(submission.created_utc).strftime(datetime_fmt),
        'distinguished': submission.distinguished,
        'edited': submission.edited,
        'id': submission.id,
        'is_original_content': submission.is_original_content,
        'link_flair_text': submission.link_flair_text,
        'locked': submission.locked,
        'name': submission.name,
        'num_comments': submission.num_comments,  # Includes deleted, removed, and spam comments.
        'over_18': submission.over_18,
        'permalink': submission.permalink,
        'removed_by_category': submission.removed_by_category,
        'score': submission.score,
        'selftext': submission.selftext,
        'spoiler': submission.spoiler,
        'stickied': submission.stickied,
        'subreddit_display_name': submission.subreddit.display_name,
        'title': submission.title,
        'upvote_ratio': submission.upvote_ratio,
        'url': submission.url,
    }
    return submission_parsed


def main() -> None:
    print('Fetching and storing new submissions...')
    subreddit, file_path = parse_args()
    praw_credentials_file = Path(__file__).parents[1].absolute() / 'credentials' / 'praw_credentials.json'
    praw_credentials = json.loads(praw_credentials_file.read_text())
    reddit = Reddit(**praw_credentials)
    reddit.read_only = True

    # Fetch new submissions and store them in a JSON file.
    old_submissions = json.loads(file_path.read_text(encoding='utf-8')) if file_path.exists() else []
    most_recent_submission_id = old_submissions[0]['id'] if len(old_submissions) > 0 else None
    new_submissions = []
    for submission in tqdm(reddit.subreddit(subreddit).new(limit=None)):
        # Only fetch submissions we didn't already fetch.
        if most_recent_submission_id is not None and submission.id == most_recent_submission_id:
            break
        submission_parsed = parse_submission(submission)
        new_submissions.append(submission_parsed)

    file_path.write_text(json.dumps(new_submissions + old_submissions, indent=4), encoding='utf-8')
    print('Done fetching and storing new submissions.')


if __name__ == '__main__':
    main()

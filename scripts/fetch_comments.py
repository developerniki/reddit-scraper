#!/usr/bin/env python

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Tuple, Dict, Any

from praw import Reddit
from praw.models import Comment
from tqdm import tqdm


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
    file_path = Path(__file__).parents[1].absolute() / 'data' / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)  # Create the directory if it doesn't exist.
    return args.subreddit, file_path, args.max_comments


def parse_comment(comment: Comment, datetime_fmt='%Y-%m-%d %H:%M:%S') -> Dict[str, Any]:
    comment_parsed = {
        # The author is `None` if the Reddit account does not exist anymore.
        'author_name': comment.author and comment.author.name,
        'body': comment.body,
        'created_utc': datetime.fromtimestamp(comment.created_utc).strftime(datetime_fmt),
        'distinguished': comment.distinguished,
        'edited': comment.edited,
        'id': comment.id,
        'is_submitter': comment.is_submitter,
        'link_id': comment.link_id,
        'parent_id': comment.parent_id,
        'permalink': comment.permalink,
        'replies': [parse_comment(comment) for comment in comment.replies],
        'score': comment.score,
        'stickied': comment.stickied,
    }
    return comment_parsed


def main() -> None:
    print('Fetching comments for submissions...')
    subreddit, file_path, max_comments = parse_args()
    praw_credentials_file = Path(__file__).parents[1].absolute() / 'credentials' / 'praw_credentials.json'
    praw_credentials = json.loads(praw_credentials_file.read_text())
    reddit = Reddit(**praw_credentials)
    reddit.read_only = True

    submissions = json.loads(file_path.read_text(encoding='utf-8')) if file_path.exists() else []
    for submission in tqdm(submissions, total=sum(1 for s in submissions if s.get('comments') is None)):
        # Only fetch comments for submissions that don't have any comments yet.
        if submission.get('comments') is None:
            comments = reddit.submission(submission['id']).comments
            comments.replace_more(limit=None)
            comments = [parse_comment(top_level_comment) for top_level_comment in comments]
            submission['comments'] = comments

    file_path.write_text(json.dumps(submissions, indent=4), encoding='utf-8')
    print('Done fetching comments.')


if __name__ == '__main__':
    main()

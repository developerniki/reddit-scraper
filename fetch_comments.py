#!/usr/bin/env python

from typing import Dict

import praw
from praw import reddit
from datetime import datetime
import json
from tqdm import tqdm

DATIME_FMT = '%Y-%m-%d %H:%M:%S'


def parse_comment(comment: reddit.Comment) -> Dict:
    """Parse a reddit comment object and write the relevant attributes into a dictionary."""
    comment_parsed = {
        'author_name': comment.author and comment.author.name,  # TODO Figure out which author is `None`.
        'body': comment.body,
        'created_utc': datetime.fromtimestamp(comment.created_utc).strftime(DATIME_FMT),
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


if __name__ == '__main__':
    reddit = praw.Reddit('bot1')
    reddit.read_only = True

    with open('data/posts.json', 'r') as file:
        submissions = json.load(file)

    for submission in tqdm(submissions):
        # Only fetch comments for new submissions and do not update comments for old submissions.
        if submission.get('comments') is None:
            comments = reddit.submission(submission['id']).comments
            comments.replace_more(limit=None)
            submission['comments'] = []
            for top_level_comment in comments:
                comment_parsed = parse_comment(top_level_comment)
                submission['comments'].append(comment_parsed)

    with open('data/posts.json', 'w') as file:
        json.dump(submissions, file, indent=4)

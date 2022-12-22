#!/usr/bin/env python

from typing import Dict

import praw
from praw import reddit
from datetime import datetime
import json
from pathlib import Path
from tqdm import tqdm

DATIME_FMT = '%Y-%m-%d %H:%M:%S'


def parse_submission(submission: reddit.Submission) -> Dict:
    """Parse a reddit submission object and write the relevant attributes into a dictionary."""
    submission_parsed = {
        'author_name': submission.author.name,
        'author_flair_text': submission.author_flair_text,
        'comments': None,
        'created_utc': datetime.fromtimestamp(submission.created_utc).strftime(DATIME_FMT),
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


if __name__ == '__main__':
    reddit = praw.Reddit('bot1')
    reddit.read_only = True

    submissions_old = []
    most_recent_id = None

    if Path('data/posts.json').exists():
        with open('data/posts.json', 'r') as file:
            submissions_old = json.load(file)
            if submissions_old and len(submissions_old) > 0:
                most_recent_id = submissions_old[0]['id']

    submissions = []

    submission_iter = reddit.subreddit('male_studies').new(limit=None)
    for submission in tqdm(submission_iter):
        if submission.id == most_recent_id:
            # Only fetch posts we didn't already fetch.
            break
        submission_parsed = parse_submission(submission)
        submissions.append(submission_parsed)

    with open('data/posts.json', 'w') as file:
        json.dump(submissions + submissions_old, file, indent=4)

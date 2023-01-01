import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from praw import Reddit
from praw.models import Submission, Comment
from tqdm import tqdm

_logger = logging.getLogger(Path(__file__).name)


def get_reddit_client() -> Reddit:
    """Initialize the Reddit API.

    Returns:
        A praw.Reddit instance.
    """
    praw_credentials_file = Path(__file__).parent.parent.parent / 'credentials' / 'praw_credentials.json'
    praw_credentials = json.loads(praw_credentials_file.read_text())
    reddit = Reddit(**praw_credentials)
    reddit.read_only = True
    return reddit


def parse_submission(submission: Submission, datetime_fmt='%Y-%m-%d %H:%M:%S') -> Dict[str, Any]:
    """Parse a reddit submission object and write the relevant attributes into a dictionary.

    Parameters:
        submission: A praw.reddit.Submission instance.
        datetime_fmt: The format to use when parsing the submission's creation date.

    Returns:
        A dictionary containing the parsed submission.
    """
    submission_parsed = {
        'author_name': submission.author.name,
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


def fetch_submissions(reddit: Reddit, subreddit: str, until_id: Optional[str] = None) -> List[Dict]:
    """Fetch submissions from the subreddit. If `until_id` is provided, only submissions newer than the one with the
    given ID will be fetched.

    Parameters:
        reddit: A praw.Reddit instance.
        subreddit: The name of the subreddit to fetch submissions from.
        until_id: The ID of the most recent stored submission.

    Returns:
        A list of dictionaries containing the parsed submissions.
    """
    submissions = []
    submission_iter = reddit.subreddit(subreddit).new(limit=None)
    for submission in tqdm(submission_iter):
        # Only fetch submissions we didn't already fetch.
        if until_id is not None and submission.id == until_id:
            break
        submission_parsed = parse_submission(submission)
        submissions.append(submission_parsed)
    return submissions


def parse_comment(comment: Comment, datetime_fmt='%Y-%m-%d %H:%M:%S') -> Dict[str, Any]:
    """Parse a reddit comment object and write the relevant attributes into a dictionary.

    Parameters:
        comment: A praw.reddit.Comment instance.
        datetime_fmt: The format to use when parsing the comment's creation date.

    Returns:
        A dictionary containing the parsed comment.
    """
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


def fetch_comments(submission: Submission, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Fetch comments for the given submission.

    Parameters:
        submission: A praw.reddit.Submission instance.
        limit: How many `MoreComments` objects to replace. If `None`, all `MoreComments` objects will be replaced.

    Returns:
        A list of dictionaries containing the parsed comments.
    """
    comments = submission.comments
    comments.replace_more(limit=limit)
    comments = [parse_comment(top_level_comment) for top_level_comment in comments]
    return comments


def is_submission_created_in_last_n_hours(submission: Submission | Dict[str, Any], hours: int,
                                          datetime_fmt='%Y-%m-%d %H:%M:%S') -> bool:
    """Check if the submission was created in the last `hours` hours.

    Parameters:
        submission: A `praw.reddit.Submission` instance or a dictionary containing the parsed submission.
        hours: The number of hours.
        datetime_fmt: The format to use when parsing the submission's creation date.

    Returns:
        `True` if the submission was created in the last `hours` hours, `False` otherwise.
    """
    submission_created = submission['created_utc'] if isinstance(submission, dict) else submission.created_utc
    submission_created = datetime.strptime(submission_created, datetime_fmt)
    now = datetime.now()
    return (now - submission_created).total_seconds() < hours * 3600

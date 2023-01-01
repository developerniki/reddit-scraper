#!/usr/bin/env python

import argparse
import logging
from pathlib import Path
from typing import Tuple

import pandas as pd

from utils import metadata_utils

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(Path(__file__).name)


def parse_args() -> Tuple[str, Path]:
    parser = argparse.ArgumentParser(description='Process the raw data.')
    parser.add_argument('subreddit', type=str, help='The subreddit to process the raw data for.')
    parser.add_argument(
        '-f',
        '--filename',
        type=str,
        help="The name of the JSON file that stores the data without the file suffix. Defaults to the lowercase name "
             "of the subreddit. For example, if the subreddit is 'r/Python', the default filename is 'python'.",
    )
    args = parser.parse_args()
    filename = f'{args.filename or args.subreddit.lower()}.json'
    file_path = Path(__file__).parent.parent / 'data' / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)  # Create the directory if it doesn't exist.
    return args.subreddit, file_path


def process_raw_data(df: pd.DataFrame) -> None:
    """Extract the actual URL from the submission body if the URL matches the permalink (and mark the row with a new
    `_is_url_from_selftext` column), extract  the summary from the comments into a new `_summary` column of the
    dataframe, and extract the paper type from the title, and mark every row with an '_is_research' flag to indicate
    whether the submission is or just a moderation post.

    Parameters:
        df: The Reddit submission dataframe to process.
    """
    # If the URL matches the permalink, then extract the actual URL from the submission body.
    df['_is_url_from_selftext'] = df['url'] == 'https://www.reddit.com' + df['permalink']
    df['url'] = df['url'].where(~df['_is_url_from_selftext'], df['selftext'].apply(metadata_utils.extract_markdown_url))

    # Extract the summary.
    # If the URL is from the selftext, then the summary is the first comment.
    df.loc[df['_is_url_from_selftext'], '_summary'] = df['selftext']
    # Otherwise, it is in the comments.
    mask = ~df['_is_url_from_selftext'] & df['comments'].notna()
    df.loc[mask, '_summary'] = df.loc[mask, 'comments'].apply(metadata_utils.extract_article_summary_from_comments)
    df['_title_paper_type'] = df['title'].apply(metadata_utils.extract_paper_type_from_title)

    # Make a field to indicate whether the submission is research.
    non_research_flairs = ('Active Research', 'Mod Announcement', 'Mod News', 'Poll', 'Requests')
    df['_is_research'] = df['link_flair_text'].apply(lambda flair: flair not in non_research_flairs)


if __name__ == '__main__':
    _logger.info('Processing raw data...')
    subreddit, file_path = parse_args()
    df = pd.read_json(file_path) if file_path.exists() else pd.DataFrame()
    # We re-process the raw data every time because it is low-cost and ensures that the data is always up-to-date.
    process_raw_data(df)
    df.to_json(file_path, orient='records', indent=4)
    _logger.info('Done processing raw data.')

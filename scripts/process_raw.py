#!/usr/bin/env python

import argparse
import json
import logging
from pathlib import Path
from typing import Tuple, List, Dict, Any

from utils import reddit_utils, metadata_utils

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
             "of the subreddit. For example, if the subreddit is 'r/Python', the default filename is 'r_python'.",
    )
    args = parser.parse_args()
    filename = f'r_{args.filename or args.subreddit.lower()}.json'
    file_path = Path(__file__).parent.parent / 'data' / filename
    file_path.parent.mkdir(parents=True, exist_ok=True)  # Create the directory if it doesn't exist.
    return args.subreddit, file_path


def process_raw_data(submissions: List[Dict[str, Any]]) -> None:
    """Extract the URL and summary from the raw data and store them in the '_real_url' and '_summary' fields.

    The following cases are considered:
    1. The URL is equal to 'https://www.reddit.com' + the permalink.
        a. The URL is in the title and the summary is the selftext.
        b. The real URL is the selftext and the summary is in the comments.
        c. The real URL is the first link in which the description stripped from '*' and '_' characters is the same
              as the URL, otherwise just the first link. The summary is the selftext.
    2. The URL is a permalink to another subreddit. Use praw to get the selftext of the URL and extract the real URL and
       the summary from the selftext.
    3. The URL is not equal to the permalink. The real URL is the URL and the summary is in the comments.


    Parameters:
        submissions: The submissions to process.
    """
    # Make a field to indicate whether the submission is research.
    non_research_flairs = ('Active Research', 'Mod Announcement', 'Mod News', 'Poll', 'Requests')

    for submission in submissions:
        submission['_is_research'] = submission['link_flair_text'] not in non_research_flairs

        if not submission['_is_research']:
            continue

        # Extract the paper type from the title.
        submission['_paper_type'] = metadata_utils.extract_paper_type_from_title(submission['title'])

        if submission['url'] == 'https://www.reddit.com' + submission['permalink']:
            # Case 1. The URL is equal to 'https://www.reddit.com' + the permalink.
            descriptions_and_urls = metadata_utils.extract_markdown_urls(submission['selftext'])
            if len(descriptions_and_urls) == 0:
                # Case 1a. The URL is in the title and the summary is the selftext.
                title_urls = metadata_utils.extract_urls(submission['title'])
                submission['_real_url'] = title_urls[0] if len(title_urls) > 0 else None
                submission['_summary'] = submission['selftext']
            elif submission['selftext'] == f'[{descriptions_and_urls[0][0]}]({descriptions_and_urls[0][1]})':
                # Case 1b. The real URL is the selftext and the summary is in the comments.
                submission['_real_url'] = descriptions_and_urls[0][1]
                submission['_summary'] = metadata_utils.extract_article_summary_from_comments(submission['comments'])
            else:
                # Case 1c. The real URL is the first link in which the description stripped from '*' and '_' characters
                # is the same as the URL, otherwise just the first link. The summary is the selftext.
                for description, url in descriptions_and_urls:
                    if description.strip('*_') == url:
                        submission['_real_url'] = url
                        break
                else:  # No break.
                    submission['_real_url'] = descriptions_and_urls[0][1]
                submission['_summary'] = submission['selftext']
        elif submission['url'].startswith('/r/'):
            # Case 2. The URL is a permalink to another subreddit. Use praw to get the selftext of the URL and extract
            # the real URL and the summary from the selftext.
            reddit = reddit_utils.get_reddit_client()
            submission['_crosspost_selftext'] = reddit.submission(
                url=f'https://www.reddit.com{submission["url"]}'
            ).selftext
            real_urls = metadata_utils.extract_markdown_urls(submission['_crosspost_selftext'])
            if len(real_urls) > 0:
                submission['_real_url'] = real_urls[0][1]
            else:
                real_urls = metadata_utils.extract_urls(submission['_crosspost_selftext'])
                submission['_real_url'] = real_urls[0] if len(real_urls) > 0 else None
            submission['_summary'] = submission['_crosspost_selftext']
        else:
            # Case 3. The URL is not equal to the permalink. The real URL is the URL and the summary is in the comments.
            submission['_real_url'] = submission['url']
            submission['_summary'] = metadata_utils.extract_article_summary_from_comments(submission['comments'] or [])


if __name__ == '__main__':
    _logger.info('Processing raw data...')
    subreddit, file_path = parse_args()
    submissions = json.loads(file_path.read_text()) if file_path.exists() else []
    # We re-process the raw data every time because it is low-cost and ensures that the data is always up-to-date.
    process_raw_data(submissions)

    file_path.write_text(json.dumps(submissions, indent=4))
    _logger.info('Done processing raw data.')

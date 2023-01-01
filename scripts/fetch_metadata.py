#!/usr/bin/env python

import argparse
import logging
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm

from utils import metadata_utils

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(Path(__file__).name)


def parse_args() -> Tuple[str, Path]:
    parser = argparse.ArgumentParser(description='Fetch metadata for all stored submissions.')
    parser.add_argument('subreddit', type=str, help='The subreddit to fetch metadata for.')
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


def fetch_metadata(df: pd.DataFrame) -> None:
    """Fetch metadata for each row in the dataframe into a new `metadata` column of the dataframe and mark any rows that
    failed to fetch by setting the `metadata` column to `None`. Only fetch metadata for rows that don't already have it.

    Parameters:
        df: The dataframe to process.
    """

    if '_metadata' not in df.columns:
        df['_metadata'] = np.nan
    rows_without_metadata = df[(df['_is_research']) & (df['_metadata'].isna())]

    # Iterate through the rows that need to fetch metadata
    for index, row in tqdm(rows_without_metadata.iterrows(), total=len(rows_without_metadata)):
        article_metadata = metadata_utils.fetch_article_metadata(row['title'], row['url'])

        if article_metadata is None:
            df.at[index, '_metadata'] = np.nan
        else:
            if 'items' in article_metadata:
                # If there are multiple items, then take the closest match to the title.
                article_metadata = metadata_utils.closest_match(row['title'], article_metadata['items'])
            df.at[index, '_metadata'] = article_metadata


if __name__ == '__main__':
    _logger.info('Fetching and storing metadata for all stored submissions...')
    subreddit, file_path = parse_args()
    if file_path.exists():
        df = pd.read_json(file_path)
        fetch_metadata(df)
        df.to_json(file_path, orient='records', indent=4)
        _logger.info('Done fetching and storing metadata for all stored submissions.')
    else:
        _logger.info(f'No data found for {subreddit}.')

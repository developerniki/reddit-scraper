#!usr/bin/env python

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Tuple, List

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    _logger = logging.getLogger(Path(__file__).name)


    def parse_args() -> Tuple[str, Path]:
        parser = argparse.ArgumentParser(
            description='Print submissions that encountered a failure when fetching metadata or syncing with Zotero.')
        parser.add_argument('subreddit', type=str, help='The subreddit to fetch metadata for.')
        parser.add_argument(
            '-f',
            '--filename',
            type=str,
            help="The name of the JSON file that stores the data without the file suffix. Defaults to the lowercase "
                 "name of the subreddit. For example, if the subreddit is 'r/Python', the default filename is "
                 "'python'.",
        )
        args = parser.parse_args()
        filename = f'{args.filename or args.subreddit.lower()}.json'
        file_path = Path(__file__).parent.parent / 'data' / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)  # Create the directory if it doesn't exist.
        return args.subreddit, file_path


    def print_metadata_fails(submissions: List) -> None:
        """Print the submissions that failed to fetch metadata.

        Parameters:
            submissions: The list of submissions to print the failed ones from.
        """

        no_meta_no_domain = [s for s in submissions if s.get('_metadata') is None and s.get('url') is None]
        no_meta_by_domain = defaultdict(list)
        for s in submissions:
            if s.get('_metadata') is None and s.get('url') is not None:
                no_meta_by_domain[s['url'].split('/')[2]].append(s)
        no_meta_by_domain = dict(sorted(no_meta_by_domain.items(), key=lambda x: len(x[1]), reverse=True))

        print(f'- Failed to fetch metadata for {len(no_meta_no_domain) + len(no_meta_by_domain)} '
              f'submission{"s" if len(no_meta_by_domain) != 1 else ""}:')

        print(f'\n  - {len(no_meta_no_domain)} submission{"s" if len(no_meta_no_domain) != 1 else ""} with no URL:')
        for s in no_meta_no_domain:
            print(f'    - permalink=https://reddit.com{s["permalink"]}')

        for k, v in no_meta_by_domain.items():
            print(f'\n  - {len(v)} submission{"s" if len(v) > 1 else ""} {"are" if len(v) > 1 else "is"} from {k}:')
            for s in v:
                print(f'    - url={s["url"]}, permalink=https://reddit.com{s["permalink"]}')


    def print_zot_fails(submissions: List) -> None:
        """Print the submissions that failed to sync with Zotero.

        Parameters:
            submissions: The list of submissions to print the failed ones from.
        """
        zot_fails = [s for s in submissions if s.get('_zotero_sync_error')]
        print(f'\n- Failed to sync with Zotero for {len(zot_fails)} submissions:')
        for s in zot_fails:
            print(f'  - url={s["url"]}, error={s["_zotero_sync_error"]}')


    if __name__ == '__main__':
        subreddit, file_path = parse_args()

        submissions = json.loads(file_path.read_text()) if file_path.exists() else []
        submissions = [submission for submission in submissions if submission['_is_research']]

        print_metadata_fails(submissions)
        print_zot_fails(submissions)

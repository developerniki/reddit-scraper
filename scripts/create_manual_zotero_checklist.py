#!/usr/bin/env python

import argparse
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Tuple, List

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(Path(__file__).name)

if __name__ == '__main__':
    def parse_args() -> Tuple[str, Path, Path]:
        parser = argparse.ArgumentParser(
            description='Create a checklist of submissions that encountered a failure when fetching metadata or syncing '
                        'with Zotero in the `<filename>.checklist.md` file. When the items in the '
                        'generated file are checked off and the `handle_manually_synced_files.py` script is run, the '
                        'submissions will be marked as manually synced with Zotero which will prevent them from being '
                        'synced with Zotero again and being included in the generated Markdown file.')
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
        submissions_file_path = Path(__file__).parent.parent / 'data' / filename
        submissions_file_path.parent.mkdir(parents=True, exist_ok=True)  # Create the directory if it doesn't exist.
        checklist_file_path = submissions_file_path.with_suffix('.checklist.md')
        return args.subreddit, submissions_file_path, checklist_file_path


    def get_metadata_fail_md(submissions: List) -> Tuple[str, int]:
        """Get the Markdown for the submissions that had a metadata failure.

        Parameters:
            submissions: The submissions to get the Markdown for.

        Returns:
            The Markdown for the submissions that had a metadata failure and the number of submissions that had a
            metadata failure.
        """
        md = ''

        no_meta_no_domain = [s for s in submissions if s.get('_metadata_failed') and s.get('url') is None]
        no_meta_by_domain = defaultdict(list)
        for s in submissions:
            if s.get('_metadata_failed') and s.get('url') is not None:
                no_meta_by_domain[s['url'].split('/')[2]].append(s)

        no_meta_by_domain = dict(sorted(no_meta_by_domain.items(), key=lambda item: (-len(item[1]), item[0])))

        n_meta_fail = len(no_meta_no_domain) + len(no_meta_by_domain)
        md += (f'- Failed to fetch metadata for {n_meta_fail} submission{"s" if n_meta_fail != 1 else ""}')
        md += f'{":" if n_meta_fail > 0 else "."}'

        if no_meta_no_domain:
            md += f'\n\n  - {len(no_meta_no_domain)} submission{"s" if len(no_meta_no_domain) != 1 else ""} with no URL:'
            for s in no_meta_no_domain:
                md += f'\n    - [ ] permalink=https://www.reddit.com{s["permalink"]}'

        if no_meta_by_domain:
            for k, v in no_meta_by_domain.items():
                md += f'\n\n  - {len(v)} submission{"s" if len(v) > 1 else ""} {"are" if len(v) != 1 else "is"} from {k}:'
                for s in v:
                    md += f'\n    - [ ] url={s["url"]}, permalink=https://www.reddit.com{s["permalink"]}'

        return md, n_meta_fail


    def get_zot_fails_md(submissions: List) -> Tuple[str, int]:
        """Get the Markdown for the submissions that failed to sync with Zotero.

        Parameters:
            submissions: The submissions to get the Markdown for.

        Returns:
            The Markdown for the submissions that failed to sync with Zotero and the number of submissions that failed
            to sync with Zotero.
        """
        md = ''
        zot_fails = [s for s in submissions if s.get('_zotero_sync_error')]
        md += f'\n- Failed to sync with Zotero for {len(zot_fails)} submissions'
        md += f'{":" if len(zot_fails) > 0 else "."}'
        if len(zot_fails) > 0:
            for s in zot_fails:
                md += (f'\n  - [ ] url={s["url"]}, permalink=https://www.reddit.com{s["permalink"]}, '
                       f'error="{s["_zotero_sync_error"]}"')
        return md, len(zot_fails)


    if __name__ == '__main__':
        _logger.info('Creating checklist of submissions that failed to fetch metadata or sync with Zotero...')
        subreddit, submissions_file_path, checklist_file_path = parse_args()

        submissions = json.loads(submissions_file_path.read_text()) if submissions_file_path.exists() else []
        submissions = [submission for submission in submissions if
                       submission['_is_research'] and not submission.get('_manually_synced_with_zotero')]

        meta_fail_md, n_meta_fail = get_metadata_fail_md(submissions)
        zot_fail_md, n_zot_fail = get_zot_fails_md(submissions)
        n_fail = n_meta_fail + n_zot_fail

        if n_fail > 0:
            md = meta_fail_md + '\n' + zot_fail_md
            checklist_file_path.write_text(md)
            _logger.info(f'Created checklist with {n_fail} failed submission{"s" if n_fail != 1 else ""} in '
                         f'{checklist_file_path}')
        else:
            if checklist_file_path.exists():
                checklist_file_path.unlink()
                _logger.info('No failed submissions found. Deleted the checklist file.')
            else:
                _logger.info('No failed submissions found. Did not create a checklist file.')

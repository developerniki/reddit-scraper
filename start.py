#!/usr/bin/env python

"""Execute the full pipeline to fetch new submissions and metadata for r/Male_Studies and r/FemaleStudies and then
upload the data to a Google Sheet and a Zotero library. Before executing the pipeline, the data is backed up to a
`backups/<current timestamp>` folder.
"""

import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

GOOGLE_SHEETS_URL = 'https://docs.google.com/spreadsheets/d/1BaOq-cgq7IXPcVn0plo__giy_GGKGPsLOnz3zEgh4EM'
SUBREDDITS = ('Male_Studies', 'FemaleStudies')
PYTHON = str((Path(__file__).parent / '.venv' / 'bin' / 'python'))
DATA_PATH = Path(__file__).parent / 'data'
BACKUP_PATH = DATA_PATH / 'backups'

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(Path(__file__).name)


def backup_data() -> None:
    """Backup the `data` folder to a timestamped folder in the `data/backups` folder."""
    if DATA_PATH.exists():
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        _logger.info(f'Backing up data to {BACKUP_PATH / timestamp}...')
        (BACKUP_PATH / timestamp).mkdir(parents=True, exist_ok=True)
        for file in filter(lambda p: p.is_file(), DATA_PATH.iterdir()):
            shutil.copyfile(file, BACKUP_PATH / timestamp / file.name)
    else:
        _logger.info(f'No data to backup... {DATA_PATH} does not exist...')


if __name__ == '__main__':
    _logger.info('Executing full scraping pipeline...')
    backup_data()
    for google_sheets_num, subreddit in enumerate(SUBREDDITS):
        google_sheets_num = str(google_sheets_num)
        subprocess.run([PYTHON, 'scripts/fetch_submissions.py', subreddit])
        subprocess.run([PYTHON, 'scripts/fetch_comments.py', subreddit])
        subprocess.run([PYTHON, 'scripts/update_recent_submissions_and_comments.py', subreddit])
        subprocess.run([PYTHON, 'scripts/process_raw.py', subreddit])
        subprocess.run([PYTHON, 'scripts/fetch_metadata.py', subreddit])
        subprocess.run([PYTHON, 'scripts/sync_with_google_sheets.py', subreddit, GOOGLE_SHEETS_URL, google_sheets_num])
        # TODO Uncomment the following line when the `sync_with_zotero.py` script is ready.
        # subprocess.run([PYTHON, 'scripts/sync_with_zotero.py', subreddit])
    _logger.info('Finished executing full scraping pipeline.')

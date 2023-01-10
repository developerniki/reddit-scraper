# reddit-scraper

This repository contains scripts for scraping research articles from Reddit and uploading them to Google Sheets and
Zotero, although the scripts `fetch_submissions.py`, `fetch_comments.py`, `update_recent_submissions_and_comments.py`,
and `update_all_missing_flairs.py` can be used to fetch any Reddit content.

## Installation

In order to use these scripts, you will need:

- A Reddit account and a Reddit app. You will need to provide your Reddit credentials (client ID, client secret,
  password, username, and user agent) in a file called `credentials/praw_credentials.json`.
- A Google account and a Google Sheet. You will also need to create a Google service account and provide its credentials
  in a file called `credentials/google_service_account.json`.
- A Zotero account and library. If you want to upload the articles to Zotero, you will need to provide your Zotero API
  key in a file called `credentials/zotero_credentials.json`.

The `zotero_credentials.json` has the following structure:

```json
{
  "api_key": "<API key>"
}
  ```

Before running the scripts, make sure to create a virtual environment and install the required packages from
`requirements.txt`:

```commandline
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

## Usage

The scraping process is divided into multiple steps:

1. `fetch_submissions.py`: Fetch the articles from Reddit using the Reddit API and store them into a JSON
   file `data/<subreddit>.json`.
2. `fetch_comments.py`: Scrape the comments from the articles and store them in the same JSON file.
3. `process_raw.py`: Process the raw data and store it in the same JSON file.
    - If the URL matches the permalink of the submission, then the URL is extracted from the submission's selftext.
      Submissions like this are marked as `_is_url_from_selftext = True`, otherwise `_is_url_from_selftext = False`.
    - A summary of the article is extracted by either taking the submission text if `_is_url_from_selftext = True`,
      otherwise by concatenating OP comments/replies that are not interrupted by a comment/reply from another user.
    - The paper type is extracted by looking for keywords of the form `[keyword]` in the submission title.
    - The field `_is_research` is set to `False` if the submission flair is one of 'Active Research', 'Mod
      Announcement', 'Mod News', 'Poll', or 'Requests'. Otherwise, it is set to `True`.
    - Generally, all added fields start with an underscore to clearly distinguish them from the original fields.
4. `fetch_metadata.py`: Fetch the metadata for the articles using the Crossref API and store it in the same JSON file.
   For this, it is first attempted to get the DOI of the submission URL from its URL, and if that does not work from the
   HMTL of the URL. If the DOI is found, then the title is used to search for the metadata. In both cases, if there are
   multiple results, then the most similar result is chosen. Results that are not at least 80% similar are discarded.
5. `sync_with_google_sheets.py` and `sync_with_zotero.py`: Upload the processed data to Google Sheets and/or Zotero.

Additionally, there are three scripts for keeping the data up-to-date and downloading a Google Sheet as an Excel file:

- `update_all_missing_flairs.py`: Update the flair of all submissions that are missing a flair.
- `update_recent_submissions_and_comments.py`: Update the comments and flairs of all submissions that have been posted
  in the last 7 days or delete the submission if it has been removed in the meantime.
- `download_google_sheet_as_xlsx.py`: Download a Google Sheet as an XLSX (Excel) file.

Both scripts set `_synced_with_google_sheets` and `_synced_with_zotero` to `False` so that the data is re-uploaded to
Google Sheets and Zotero if it has been updated. This is useful if you want to run the scripts on a regular basis, e.g.
using a cron job.

Each script under the `scripts` folder accepts the subreddit name as a command-line argument. For example, to scrape the
posts of the `r/Psychology` subreddit, run `python fetch_submissions.py Psychology`.

An example of how to use the various scripts can be found in `start.py`. This script will use the Reddit API to scrape
articles from Reddit, process the raw data, fetch metadata using the Crossref API, and upload the processed data to
Google Sheets and Zotero. Additionally, at the beginning of the script, it will copy the data to
the `data/backup/<current timestamp>` directory.

## Note on deleted submissions

If a submission is deleted, then the script `fetch_submissions.py` will not be able to scrape the submission. However,
if the submission was scraped before it was deleted, the field `removed_by_category` will be set to a value that is
not `null`. If the submission was not scraped before it was deleted, then the field `removed_by_category` will be set
to `null` when the submission is being updated using the `update_recent_submissions_and_comments.py` script. This is to
ensure no data is lost if a submission is deleted but to still mark the submission as deleted, so it can be ignored in
further processing.

## Future work

- [ ] Store the metadata separately from the raw data in a file called `metadata/<filename>.json` and move the original
  data to a file called `raw/<filename>.json`.

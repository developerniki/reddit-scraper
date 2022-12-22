# reddit-scraper
Various scripts to scrape research articles from Reddit and upload them to Google sheets.

You will need a working `praw.ini` file containing the credentials for a bot account and a file `google_credentials/google_service_account.json` containing the credentials for a Google service account.

This is an example `praw.ini` file:
```
[DEFAULT]
# A boolean to indicate whether or not to check for package updates.
check_for_updates=True

# Object to kind mappings
comment_kind=t1
message_kind=t4
redditor_kind=t2
submission_kind=t3
subreddit_kind=t5
trophy_kind=t6

# The URL prefix for OAuth-related requests.
oauth_url=https://oauth.reddit.com

# The amount of seconds of ratelimit to sleep for upon encountering a specific type of 429 error.
ratelimit_seconds=5

# The URL prefix for regular requests.
reddit_url=https://www.reddit.com

# The URL prefix for short URLs.
short_url=https://redd.it

# The timeout for requests to Reddit in number of seconds
timeout=16

[bot1]
client_id= # Known when you make a Reddit bot account.
client_secret= # Known when you make a Reddit bot account.
password= # The password of the Reddit account the bot account belongs to.
username= # # The username of the Reddit account the bot account belongs to (the <username> in r/<username>).
user_agent= # Should contain your bot name, version, and username.
```

The `start.sh` script assumes that a virtual environment `.venv` that has installed all requirements from the `requirements.txt` exists:
```commandline
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

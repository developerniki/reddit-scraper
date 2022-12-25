#!/usr/bin/env python

import html
import re
from collections import deque

import gspread
import pandas as pd

SHEET_URL = 'https://docs.google.com/spreadsheets/d/1BaOq-cgq7IXPcVn0plo__giy_GGKGPsLOnz3zEgh4EM'


def extract_url(text: str) -> str:
    url = re.search(r'\[.+\]\((?P<url>https?://\S+)\)', text)
    url = None if url is None else url.group('url')
    return url


def extract_summary(comments):
    """Use depth first search to concatenate uninterrupted submitter comment/reply chain."""
    summary = []
    queue = deque(comments)
    while queue:
        comment = queue.popleft()
        if comment['is_submitter']:
            summary.append(comment['body'])
            replies = comment['replies']
            queue.extendleft(replies)
    summary = '\n\n∴\n\n'.join(summary)
    summary = html.unescape(summary)
    return summary


if __name__ == '__main__':
    header = ['title', 'url', 'permalink', 'link_flair_text', 'author_name', 'created_utc', 'summary']
    df = pd.read_json('data/posts.json')

    # Extract the summary.
    df['summary'] = df['comments'].apply(extract_summary)

    # If the URL matches the permalink, then extract the actual url from the post body.
    df['permalink'] = 'https://www.reddit.com' + df['permalink']
    df_urls = df[['selftext']].rename(columns={'selftext': 'url'})
    df_urls['url'] = df_urls['url'].apply(extract_url)
    df.loc[df['url'] == df['permalink'], 'url'] = df_urls['url']

    # Parse data for Google API.
    df = df[header]
    df = df.fillna(value='—')
    df = df[df['link_flair_text'] != 'Mod Announcement']
    data = [df.columns.tolist()] + df.values.tolist()

    # Connect to Google sheets API.
    google_client = gspread.service_account('google_credentials/google_service_account.json')
    sheet = google_client.open_by_url(SHEET_URL).sheet1

    # Send data to Google sheets API.
    response = sheet.update('A1', data)
    sheet.format(f'A2:Z{len(data) + 1}', {'textFormat': {'bold': False}})
    sheet.format('A1:Z1', {'textFormat': {'bold': True}})

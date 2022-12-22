#!/usr/bin/env python

import gspread
import pandas as pd
import re

SHEET_URL = 'https://docs.google.com/spreadsheets/d/1BaOq-cgq7IXPcVn0plo__giy_GGKGPsLOnz3zEgh4EM'


def extract_url(text: str) -> str:
    url = re.search(r'\[.+\]\((?P<url>https?://\S+)\)', text)
    url = None if url is None else url.group('url')
    return url


if __name__ == '__main__':
    header = ['title', 'url', 'permalink', 'link_flair_text', 'author_name', 'created_utc']
    df = pd.read_json('data/posts.json')

    # If the URL matches the permalink, then extract the actual url from the post body.
    df['permalink'] = 'https://www.reddit.com' + df['permalink']
    df_urls = df[['selftext']].rename(columns={'selftext': 'url'})
    df_urls['url'] = df_urls['url'].apply(extract_url)
    df.loc[df['url'] == df['permalink'], 'url'] = df_urls['url']

    # Write data into list of lists before sending it to the Google API.
    df = df[header]
    df = df.fillna(value='—')
    data = [df.columns.tolist()] + df.values.tolist()

    google_client = gspread.service_account('google_credentials/google_service_account.json')
    sheet = google_client.open_by_url(SHEET_URL).sheet1

    response = sheet.update('A1', data)
    sheet.format(f'A2:Z{len(data) + 1}', {'textFormat': {'bold': False}})
    sheet.format('A1:Z1', {'textFormat': {'bold': True}})

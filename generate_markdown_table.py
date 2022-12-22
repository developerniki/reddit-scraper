#!/usr/bin/env python

import re

import pandas as pd
import json


def extract_url(text: str) -> str:
    url = re.search(r'\[.+\]\((?P<url>https?://\S+)\)', text)
    url = '—' if url is None else url.group('url')
    return url


if __name__ == '__main__':
    with open('data/posts.json', 'r') as file:
        submissions = json.load(file)

    df = pd.DataFrame(submissions)[['title', 'url', 'permalink']]
    df['permalink'] = 'https://www.reddit.com' + df['permalink']

    # If the URL matches the permalink, then extract the actual URL from the post body.
    df_urls = pd.DataFrame(submissions)[['selftext']].rename(columns={'selftext': 'url'})
    df_urls['url'] = df_urls['url'].apply(extract_url)
    df['url'][df['url'] == df['permalink']] = df_urls['url']

    with open('data/posts_table.md', 'w') as file:
        file.write(df.to_markdown(index=False, tablefmt='github'))

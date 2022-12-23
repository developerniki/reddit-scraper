#!/usr/bin/env python

import json

import praw
from tqdm import tqdm

if __name__ == '__main__':
    reddit = praw.Reddit('bot1')
    reddit.read_only = True

    with open('data/posts.json', 'r') as file:
        submissions = json.load(file)

    for submission in tqdm(submissions):
        if submission['link_flair_text'] is None:
            submission['link_flair_text'] = reddit.submission(submission['id']).link_flair_text

    with open('data/posts.json', 'w') as file:
        json.dump(submissions, file, indent=4)

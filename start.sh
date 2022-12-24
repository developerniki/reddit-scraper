#!/usr/bin/env bash

md5f1=$(md5sum 'data/posts.json' | cut -d' ' -f1)
.venv/bin/python fetch_posts.py
.venv/bin/python update_missing_flair_posts.py
md5f2=$(md5sum 'data/posts.json' | cut -d' ' -f1)

if [ "$md5f2" != "$md5f1" ]; then
  .venv/bin/python write_to_google_sheets.py
  .venv/bin/python fetch_comments.py
fi

import html
import re
from collections import deque


def extract_url(text: str) -> str:
    """Extract the first URL from a string."""
    url = re.search(r'\[.+\]\((?P<url>https?://\S+)\)', text)
    url = None if url is None else url.group('url')
    return url


def extract_article_summary(comments):
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

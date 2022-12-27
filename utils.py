import html
import re
from collections import deque
from typing import Dict



def extract_markdown_url(text: str) -> str:
    """Extract the first URL from a Markdown string.

    Parameters:
        text (str): The Markdown string to extract the URL from.

    Returns:
        str: The first URL found in the string, or `None` if no URL was found.
    """
    url = re.search(r'\[.+\]\((?P<url>https?://\S+)\)', text)
    url = None if url is None else url.group('url')
    return url


def extract_article_summary(comments: List[Dict]) -> str:
    """Extract the chain of comments and replies made by the submitter by traversing the hierarchical structure of
    comments and replies using depth first search, until a comment or reply from another user is encountered.

    Parameters:
        comments: A list of dictionaries of comments and replies. Each dictionary has the following structure:
            ```
            {
                'is_submitter': bool,
                'body': str,
                'replies': [
                    {
                        'is_submitter': bool,
                        'body': str,
                        'replies': [
                            {...},
                            ...
                        ]
                    },
                    ...
                ]
            }
            ```

    Returns:
        A string containing the concatenated comment/reply chain of the submitter, separated by '\n\n∴\n\n'.
    """
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

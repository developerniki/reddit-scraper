import asyncio
import difflib
import html
import logging
import re
from collections import deque
from pathlib import Path
from typing import Dict
from typing import List
from typing import Optional

import habanero
import pyppeteer.errors
import requests
from bs4 import BeautifulSoup
from pyppeteer import launch
from pyppeteer_stealth import stealth

_logger = logging.getLogger(Path(__file__).name)

# Compile regular expression patterns.
PATTERN_MARKDOWN_URL = re.compile(r'\[.+\]\((?P<url>https?://\S+)\)')
PATTERN_STR_DOI = r'10.\d{4,9}/[-._;()/:\w]+'  # https://www.crossref.org/blog/dois-and-matching-regular-expressions/
# After the `\S+`, we could use `/|doi=` but the second part is part of a query string which we cannot rely on.
PATTERN_DOI_URL = re.compile(fr'https?://\S+/(?P<doi>{PATTERN_STR_DOI})(/|\?.*)?')


def extract_markdown_url(text: str) -> Optional[str]:
    """Extract the first URL in `text` containing a Markdown string.

    Parameters:
        text: The Markdown string to extract the URL from.

    Returns:
        The first URL found in the string, or `None` if no URL was found.
    """
    m = PATTERN_MARKDOWN_URL.search(text)
    return m.group('url') if m else None


def extract_article_summary_from_comments(comments: List[Dict]) -> str:
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


def get_doi_from_url(url: str) -> str:
    """Extract the DOI from the given URL.

    Parameters:
        url: The URL to extract the DOI from.

    Supported URL patterns:
        - https://doi.org/{DOI}
        - https://link.springer.com/article/{DOI}
        - https://journals.sagepub.com/doi/abs/{DOI}

    Examples:
        - https://doi.org/10.1111/j.1745-9125.2010.00186.x
        - https://link.springer.com/article/10.1007/s11757-021-00698-1
        - https://journals.sagepub.com/doi/abs/10.1177/0146167284101014

    Returns:
        The DOI string, or `None` if the DOI could not be found.
    """

    m = PATTERN_DOI_URL.fullmatch(requests.utils.unquote(url))
    if m := m and m.group('doi'):
        return m

    # No DOI found.
    return None


def _get_html_from_url(url: str) -> Optional[str]:
    """Retrieve the HTML content of the page at the given URL.

    Parameters:
        url: The URL of the website to retrieve.

    Returns:
        The HTML content of the page, or `None` if the page could not be retrieved.
    """

    async def _get_url_content(url: str) -> Optional[str | bytes]:
        # Set `autoClose = False` to prevent an error when the browser is already closed at the end of this function.
        browser = await launch(headless=True, args=['--no-sandbox'], autoClose=False)
        page = await browser.newPage()
        await stealth(page)

        timeout_in_seconds = 60
        try:
            await page.goto(url, timeout=1000 * timeout_in_seconds)
        except pyppeteer.errors.TimeoutError:
            _logger.warning(f'Could not retrieve HTML from {url} within {timeout_in_seconds} seconds.')
            return None
        except pyppeteer.errors.PageError:
            _logger.warning(f'There was a page/frame related error when retrieving HTML from {url}.')
            return None

        await page.goto(url)
        await page.waitForSelector('body')
        res = await page.evaluate('document.documentElement.outerHTML')
        await browser.close()
        return res

    try:
        return asyncio.run(_get_url_content(url))
    except Exception as e:
        _logger.error(f'Error while retrieving content of URL "{url}": {e}')
        return None


def get_doi_from_html(html: str) -> Optional[str]:
    """Extract the DOI from the `<head>` element of an HTML page at the given URL.

    Parameters:
        html: The HTML content of the page to extract the DOI from.

    Returns:
        The DOI string, or `None` if the DOI could not be found.

    Examples:
        APA PsycNet:
            - URL: https://psycnet.apa.org/record/2010-04166-010
            - HTML: <meta name="citation_doi" content="10.1111/j.1745-9125.2010.00186.x">

        ResearchGate:
            - URL: https://www.researchgate.net/publication/269173761_Health_Problems_of_Partner_Violence_Victims_Comparing_Help-Seeking_Men_to_a_Population-Based_Sample
            - HTML: <meta property="citation_doi" content="10.1016/j.amepre.2014.08.022">
    """
    if html is not None:
        soup = BeautifulSoup(html, 'html.parser')
        for attr_name in ('name', 'property'):
            if doi_meta := soup.find('meta', attrs={attr_name: 'citation_doi'}):
                doi = doi_meta.get('content')
                return doi

    # No DOI found.
    return None


def get_doi(url: str) -> Optional[str]:
    """Extract the DOI from the given URL, if possible directly and otherwise from the <head> of the HTML page.

    Parameters:
        url: The URL to extract the DOI from.

    Returns:
        The DOI string, or `None` if the DOI could not be found.
    """
    return get_doi_from_url(url) or get_doi_from_html(_get_html_from_url(url))


def fetch_article_metadata(title: Optional[str], url: Optional[str] = None) -> Optional[Dict]:
    """Fetch metadata for research articles that match a title/DOI search from the CrossRef API. Either `title` or `url`
       have to not be `None`.

    Parameters:
        title: The title of the research articles to search for.
        url: The URL of the research articles to search for. If it is possible to extract a DOI from this URL, it is the
             preferred option.

    Returns:
        A dictionary containing metadata for the research articles that match the search, or `None` if the article was
        not found or an error occurred.
    """
    if title is None and url is None:
        raise ValueError('Either `title` or `url` has to contain a value.')

    # Initialize the CrossRef API client.
    cr = habanero.Crossref()
    doi = get_doi(url) if url is not None else None

    if doi is not None:
        try:
            res = cr.works(ids=doi)
            if isinstance(res, dict):
                return res.get('message')
            else:
                _logger.error(f'Error while fetching metadata for DOI "{doi}": {res=} is not a dictionary.')
                return None
        except requests.exceptions.HTTPError:
            pass

    # If the DOI search was unsuccessful, search by title.
    if title is not None:
        try:
            return cr.works(query=title).get('message')
        except requests.exceptions.HTTPError:
            pass

    # Metadata could not be fetched.
    return None


def closest_match(target: str, choices: List[dict], min_similarity: float = 0.8) -> Optional[dict]:
    """Find the first dictionary in `choices` with the title most similar to `target`.

    Parameters:
        target: The string to compare against the titles in the choices.
        choices: A list of dictionaries to search, each of which contains a 'title' key.
        min_similarity: The minimum required similarity between the `title` field and the `target` string. (default: 0.8)

    Returns:
        The dictionary with the closest matching `title` field, or `None` if no dictionary has a `title` field with a
        similarity greater than or equal to `min_similarity`.
    """
    closest_dict = None
    highest_similarity = 0

    for choice in choices:
        if choice.get('title') is None:
            continue
        for title in choice['title']:
            similarity = difflib.SequenceMatcher(None, target, title).ratio()
            if similarity > highest_similarity:
                closest_dict = choice
                highest_similarity = similarity

    return closest_dict if highest_similarity >= min_similarity else None


def extract_paper_type_from_title(title: str) -> str:
    """Extract the paper type from the title.

    Args:
        title: The title of the paper.

    Returns:
        The paper type.
    """
    title = title.lower()

    preprint_strs = ('[preprint]', '[pre-print]', '[pre print]')
    thesis_strs = ('[thesis]', '[dissertation]')

    if title.startswith(preprint_strs) or title.endswith(preprint_strs):
        return 'preprint'
    elif title.startswith(thesis_strs) or title.endswith(thesis_strs):
        return 'thesis'
    else:
        return 'paper'

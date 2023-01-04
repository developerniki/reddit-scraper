#!/usr/bin/env python

"""This file contains functions for downloading PDFs from URLs and extracting the identifier (e.g., DOI) from the PDF.
It was created as a test file and is intended to be integrated into `utils/metadata_utils.py` once it works.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Tuple

import pdf2doi
import pyppeteer
from pyppeteer import launch, errors
from pyppeteer_stealth import stealth

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger(Path(__file__).name)


# TODO It appears this may monly be possible with the JavaScript version of pyppeteer.
def get_pdf_from_url(url: str) -> Optional[Tuple[bytes, str]]:
    """Download a PDF from a URL and return the PDF as a byte string and the filename."""

    async def _get() -> Optional[Tuple[bytes, str]]:
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
        except pyppeteer.errors.PageError as e:
            _logger.warning(f'There was a page/frame related error when retrieving HTML from {url} ({e}).')
            return None

        pdf = await page.pdf()
        filename = await page.evaluate('document.title')

        await browser.close()
        return pdf, filename

    try:
        return asyncio.run(_get())
    except Exception as e:
        _logger.error(f'Error while retrieving PDF from URL "{url}": {e}')
        return None


def pdf_to_identifier(pdf: bytes, filename: str) -> Tuple[Optional[str], Optional[str]]:
    """Extract the identifier from a PDF file.

    Parameters:
        pdf: The PDF file as a byte string.
        filename: The filename of the PDF file.

    Returns:
        A tuple containing the identifier and type of the identifier ('doi' or 'arxiv'), both optional.
    """
    #  TODO Use a temporary file.
    with open(filename, 'wb') as file:
        file.write(pdf)
        out = pdf2doi.pdf2doi_singlefile(file)
        return out['identifier'], out['identifier_type']


if __name__ == '__main__':
    # filename = 'New Phytologist - 2019 - Borghi - Flowers and climate change a metabolic perspective.pdf'
    # file = Path(f'~/Desktop/{filename}').expanduser()
    # out = pdf2doi.pdf2doi_singlefile(file)
    # print(out)

    url = 'https://nph.onlinelibrary.wiley.com/doi/pdfdirect/10.1111/nph.16031'
    if res := get_pdf_from_url(url):
        pdf, filename = res
        identifier, identifier_type = pdf_to_identifier(pdf, filename)
        print(identifier, identifier_type)
    else:
        print('Could not retrieve PDF.')

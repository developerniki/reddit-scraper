from typing import Optional, Dict

import requests


# TODO When this works, move it to `metadata_utils.py`.


def get_pmid_from_url(url: str) -> Optional[int]:
    """Extract the PubMed ID from the given URL, if possible.

    Parameters:
        url: The URL to extract the PubMed ID from.

    Returns:
        The PubMed ID string, or `None` if the PubMed ID could not be found.
    """
    # TODO Use a regex.
    if 'pubmed' in url:
        pmid = url.split('/')[-1]
        if pmid.isdigit():
            return int(pmid)
    return None


def get_pmcid_from_url(url: str) -> Optional[str]:
    """Extract the PubMed Central ID from the given URL, if possible.

    Parameters:
        url: The URL to extract the PubMed Central ID from.

    Returns:
        The PubMed Central ID string, or `None` if the PubMed Central ID could not be found.
    """
    # TODO Use a regex.
    if 'pmc' in url:
        pmcid = url.split('/')[-1]
        if pmcid.isdigit():
            return pmcid
    return None


def get_pubmed_metadata(pmid: int) -> Optional[Dict]:
    """Fetch metadata for a PubMed article from the PubMed API.
    
    Parameters:
        pmid: The PubMed ID of the article to fetch metadata for.
    
    Returns:
        A dictionary containing metadata for the article, or `None` if the article was not found or an error occurred. 
    """
    # TODO Also handle PMCIDs.

    query_url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={pmid}&retmode=json'
    try:
        res = requests.get(query_url)
        res.raise_for_status()
        return res.json()
    except requests.exceptions.HTTPError:
        return None
    except requests.exceptions.JSONDecodeError:
        return None


def pubmed_to_doi(pmid: int) -> Optional[str]:
    """Fetch the DOI for a PubMed article from the PubMed API.

    Parameters:
        pmid: The PubMed ID of the article to fetch metadata for.

    Returns:
        The DOI string, or `None` if the DOI could not be found.
    """
    doi = get_pubmed_metadata(pmid)

    for field in ('result', str(pmid), 'elocationid'):
        if (doi := doi.get(field)) is None:
            return None

    return doi[5:] if doi.startswith('doi:') else None

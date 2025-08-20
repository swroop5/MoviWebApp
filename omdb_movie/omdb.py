"""Lightweight OMDb API helper.

Reads the OMDB_API_KEY from environment variables. Provides a function to
fetch movie info by title using the OMDb API.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import dotenv
import requests

dotenv.load_dotenv()
OMDB_API_KEY = os.getenv("OMDB_API_KEY")


def fetch_omdb_by_title(title: str) -> Optional[Dict[str, Any]]:
    """Fetch movie information by title from the OMDb API.

    Args:
        title: The movie title to look up.

    Returns:
        dict | None: A dictionary of OMDb fields on success (may include
        keys like "Title", "Director", "Year", "Poster", "Response"),
        or None if the request fails.

    Raises:
        RuntimeError: If OMDB_API_KEY is not set.
    """
    if not OMDB_API_KEY:
        raise RuntimeError(
            "OMDB_API_KEY is not set. Create a .env file or export the variable."
        )

    url = "https://www.omdbapi.com/"
    params = {"t": title, "apikey": OMDB_API_KEY, "type": "movie"}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()
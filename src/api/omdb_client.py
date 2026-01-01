"""
OMDB API client for fetching movie metadata and IMDb IDs.
"""

import logging
import os
from time import sleep
from typing import Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class OMDBClient:
    """Client for interacting with the OMDB API."""

    BASE_URL = "http://www.omdbapi.com/"
    RATE_LIMIT_DELAY = 0.5  # seconds between requests

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OMDB client.

        Args:
            api_key: OMDB API key. If None, reads from OMDB_API_KEY env var.

        Raises:
            ValueError: If no API key is provided or found in environment
        """
        self.api_key = api_key or os.getenv('OMDB_API_KEY')

        if not self.api_key:
            raise ValueError(
                "OMDB API key is required. Set OMDB_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.session = requests.Session()
        self._cache = {}  # Simple in-memory cache

    def search_movie(
        self,
        title: str,
        year: Optional[str] = None,
        use_cache: bool = True
    ) -> Optional[Dict]:
        """
        Search for a movie by title and optional year.

        Args:
            title: Movie title to search for
            year: Optional release year to narrow search
            use_cache: Whether to use cached results

        Returns:
            Dictionary with movie data, or None if not found

        Raises:
            requests.RequestException: If API request fails
        """
        # Create cache key
        cache_key = f"{title}:{year or 'no_year'}"

        # Check cache
        if use_cache and cache_key in self._cache:
            logger.debug(f"Cache hit for: {title} ({year})")
            return self._cache[cache_key]

        # Prepare query parameters
        params = {
            'apikey': self.api_key,
            't': title,
            'type': 'movie',
        }

        if year:
            params['y'] = year

        try:
            logger.debug(f"Querying OMDB for: {title} ({year})")
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Check if movie was found
            if data.get('Response') == 'False':
                logger.warning(f"Movie not found: {title} ({year}) - {data.get('Error', 'Unknown error')}")
                self._cache[cache_key] = None
                return None

            # Validate essential fields
            if 'imdbID' not in data:
                logger.warning(f"No IMDb ID in response for: {title}")
                self._cache[cache_key] = None
                return None

            # Cache and return
            self._cache[cache_key] = data
            logger.info(f"Found movie: {data.get('Title')} ({data.get('Year')}) - IMDb ID: {data.get('imdbID')}")

            # Rate limiting
            sleep(self.RATE_LIMIT_DELAY)

            return data

        except requests.RequestException as e:
            logger.error(f"Error querying OMDB for {title}: {e}")
            raise

    def search_movies_batch(
        self,
        titles: List[str],
        years: Optional[List[str]] = None
    ) -> List[Optional[Dict]]:
        """
        Search for multiple movies.

        Args:
            titles: List of movie titles
            years: Optional list of years (must match length of titles)

        Returns:
            List of movie data dictionaries (None for not found)

        Raises:
            ValueError: If years list doesn't match titles length
        """
        if years and len(years) != len(titles):
            raise ValueError("Years list must match length of titles list")

        if years is None:
            years = [None] * len(titles)

        results = []
        total = len(titles)

        logger.info(f"Searching OMDB for {total} movies")

        for idx, (title, year) in enumerate(zip(titles, years), 1):
            logger.info(f"Processing {idx}/{total}: {title}")

            try:
                result = self.search_movie(title, year)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to search for {title}: {e}")
                results.append(None)

        successful = sum(1 for r in results if r is not None)
        logger.info(f"Successfully found {successful}/{total} movies in OMDB")

        return results

    def get_movie_by_imdb_id(self, imdb_id: str) -> Optional[Dict]:
        """
        Get movie details by IMDb ID.

        Args:
            imdb_id: IMDb ID (e.g., 'tt0092099')

        Returns:
            Dictionary with movie data, or None if not found
        """
        params = {
            'apikey': self.api_key,
            'i': imdb_id,
            'type': 'movie',
        }

        try:
            response = self.session.get(self.BASE_URL, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            if data.get('Response') == 'False':
                logger.warning(f"Movie not found for IMDb ID: {imdb_id}")
                return None

            sleep(self.RATE_LIMIT_DELAY)
            return data

        except requests.RequestException as e:
            logger.error(f"Error fetching movie with IMDb ID {imdb_id}: {e}")
            raise

    def clear_cache(self):
        """Clear the internal cache."""
        self._cache.clear()
        logger.info("OMDB cache cleared")

    def close(self):
        """Close the requests session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def search_movies_omdb(titles: List[str], years: Optional[List[str]] = None) -> List[Optional[Dict]]:
    """
    Convenience function to search for movies using OMDB API.

    Args:
        titles: List of movie titles
        years: Optional list of years

    Returns:
        List of movie data dictionaries
    """
    with OMDBClient() as client:
        return client.search_movies_batch(titles, years)

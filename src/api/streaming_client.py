"""
Streaming Availability API client for finding where movies can be watched.
Uses RapidAPI's Streaming Availability API.
"""

import logging
import os
from time import sleep
from typing import Dict, List, Optional
import requests

logger = logging.getLogger(__name__)


class StreamingAvailabilityClient:
    """Client for the Streaming Availability API via RapidAPI."""

    BASE_URL = "https://streaming-availability.p.rapidapi.com"
    RATE_LIMIT_DELAY = 1.0  # seconds between requests for free tier

    # Supported streaming services
    SUPPORTED_SERVICES = [
        'netflix', 'prime', 'disney', 'hbo', 'hulu',
        'peacock', 'paramount', 'apple', 'mubi', 'stan'
    ]

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the Streaming Availability client.

        Args:
            api_key: RapidAPI key. If None, reads from RAPIDAPI_KEY env var.

        Raises:
            ValueError: If no API key is provided or found in environment
        """
        self.api_key = api_key or os.getenv('RAPIDAPI_KEY')

        if not self.api_key:
            raise ValueError(
                "RapidAPI key is required. Set RAPIDAPI_KEY environment variable "
                "or pass api_key parameter."
            )

        self.session = requests.Session()
        self.session.headers.update({
            'X-RapidAPI-Key': self.api_key,
            'X-RapidAPI-Host': 'streaming-availability.p.rapidapi.com'
        })

        self._cache = {}  # Simple in-memory cache

    def get_streaming_options(
        self,
        imdb_id: str,
        country: str = 'us',
        use_cache: bool = True
    ) -> Optional[Dict]:
        """
        Get streaming availability for a movie by IMDb ID.

        Args:
            imdb_id: IMDb ID (e.g., 'tt0092099')
            country: Country code (default: 'us')
            use_cache: Whether to use cached results

        Returns:
            Dictionary with streaming options, or None if not found/error

        Example return structure:
        {
            'imdb_id': 'tt0092099',
            'title': 'Top Gun',
            'year': 1986,
            'streaming_options': [
                {
                    'service': 'netflix',
                    'type': 'subscription',
                    'quality': 'hd',
                    'link': 'https://...'
                },
                {
                    'service': 'prime',
                    'type': 'rent',
                    'price': '$3.99',
                    'quality': 'hd',
                    'link': 'https://...'
                }
            ]
        }
        """
        cache_key = f"{imdb_id}:{country}"

        # Check cache
        if use_cache and cache_key in self._cache:
            logger.debug(f"Cache hit for IMDb ID: {imdb_id}")
            return self._cache[cache_key]

        try:
            logger.debug(f"Querying streaming availability for IMDb ID: {imdb_id}")

            # Using the 'get' endpoint with IMDb ID
            url = f"{self.BASE_URL}/get"
            params = {
                'imdb_id': imdb_id,
                'output_language': 'en'
            }

            response = self.session.get(url, params=params, timeout=15)

            # Handle rate limiting
            if response.status_code == 429:
                logger.warning("Rate limit hit, waiting before retry...")
                sleep(5)
                response = self.session.get(url, params=params, timeout=15)

            response.raise_for_status()
            data = response.json()

            # Parse the response
            result = self._parse_streaming_data(data, imdb_id, country)

            # Cache the result
            self._cache[cache_key] = result

            # Rate limiting
            sleep(self.RATE_LIMIT_DELAY)

            return result

        except requests.RequestException as e:
            logger.error(f"Error querying streaming availability for {imdb_id}: {e}")
            # Return None instead of raising to allow graceful degradation
            return None

    def _parse_streaming_data(self, data: Dict, imdb_id: str, country: str) -> Dict:
        """
        Parse API response into simplified streaming options format.

        Args:
            data: Raw API response
            imdb_id: IMDb ID
            country: Country code

        Returns:
            Simplified streaming options dictionary
        """
        result = {
            'imdb_id': imdb_id,
            'title': data.get('title', ''),
            'year': data.get('year'),
            'streaming_options': []
        }

        # Get streaming info for the specified country
        streaming_info = data.get('streamingInfo', {}).get(country, {})

        for service_name, service_data in streaming_info.items():
            # service_data is a list of streaming options for this service
            for option in service_data:
                streaming_option = {
                    'service': service_name,
                    'type': option.get('type', 'subscription'),  # subscription, rent, buy, free
                    'quality': option.get('quality', 'sd'),
                    'link': option.get('link', '')
                }

                # Add price if available (for rent/buy)
                if 'price' in option:
                    streaming_option['price'] = f"${option['price'].get('amount', 'N/A')}"

                result['streaming_options'].append(streaming_option)

        logger.info(
            f"Found {len(result['streaming_options'])} streaming options for "
            f"{result['title']} ({result['year']})"
        )

        return result

    def get_streaming_options_batch(
        self,
        imdb_ids: List[str],
        country: str = 'us'
    ) -> List[Optional[Dict]]:
        """
        Get streaming options for multiple movies.

        Args:
            imdb_ids: List of IMDb IDs
            country: Country code

        Returns:
            List of streaming option dictionaries (None for errors)
        """
        results = []
        total = len(imdb_ids)

        logger.info(f"Fetching streaming options for {total} movies")

        for idx, imdb_id in enumerate(imdb_ids, 1):
            logger.info(f"Processing {idx}/{total}: {imdb_id}")

            try:
                result = self.get_streaming_options(imdb_id, country)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to get streaming options for {imdb_id}: {e}")
                results.append(None)

        successful = sum(1 for r in results if r is not None)
        logger.info(f"Successfully fetched streaming info for {successful}/{total} movies")

        return results

    def clear_cache(self):
        """Clear the internal cache."""
        self._cache.clear()
        logger.info("Streaming API cache cleared")

    def close(self):
        """Close the requests session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def get_streaming_availability(imdb_ids: List[str], country: str = 'us') -> List[Optional[Dict]]:
    """
    Convenience function to get streaming availability for movies.

    Args:
        imdb_ids: List of IMDb IDs
        country: Country code (default: 'us')

    Returns:
        List of streaming option dictionaries
    """
    with StreamingAvailabilityClient() as client:
        return client.get_streaming_options_batch(imdb_ids, country)

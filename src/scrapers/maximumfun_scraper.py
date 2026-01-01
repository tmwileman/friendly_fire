"""
Scraper for Maximum Fun podcast website to extract Friendly Fire episodes.
"""

import logging
from time import sleep
from random import uniform
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)


class MaximumFunScraper:
    """Scraper for Friendly Fire podcast episodes from maximumfun.org"""

    BASE_URL = "https://maximumfun.org/podcasts/friendly-fire/"
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # seconds

    def __init__(self, max_pages: int = 15):
        """
        Initialize the scraper.

        Args:
            max_pages: Maximum number of pages to scrape
        """
        self.max_pages = max_pages
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'FriendlyFireBot/1.0 (Educational Project)'
        })

    def scrape_episodes(self) -> List[Dict[str, str]]:
        """
        Scrape all episode titles from the podcast website.

        Returns:
            List of dictionaries with episode information

        Raises:
            Exception: If scraping fails after max retries
        """
        logger.info(f"Starting to scrape episodes from {self.BASE_URL}")
        episodes = []

        for page in range(1, self.max_pages):
            logger.info(f"Scraping page {page}/{self.max_pages - 1}")

            page_episodes = self._scrape_page(page)

            if not page_episodes:
                logger.warning(f"No episodes found on page {page}, stopping pagination")
                break

            episodes.extend(page_episodes)

            # Be polite: random delay between requests
            if page < self.max_pages - 1:
                delay = uniform(1, 3)
                logger.debug(f"Waiting {delay:.2f} seconds before next request")
                sleep(delay)

        logger.info(f"Successfully scraped {len(episodes)} episodes")
        return episodes

    def _scrape_page(self, page_num: int, retry_count: int = 0) -> List[Dict[str, str]]:
        """
        Scrape a single page of episodes.

        Args:
            page_num: Page number to scrape
            retry_count: Current retry attempt

        Returns:
            List of episode dictionaries from this page
        """
        url = f"{self.BASE_URL}?_paged={page_num}"

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            # Validate response
            if not response.text or len(response.text) < 100:
                raise ValueError("Response too short, likely empty page")

            soup = BeautifulSoup(response.text, 'html.parser')

            # Find episode containers
            pod_containers = soup.find_all('div', class_='latest-panel-loop-item-title')

            if not pod_containers:
                logger.warning(f"No episode containers found on page {page_num}")
                return []

            episodes = []
            for container in pod_containers:
                h4_tag = container.find('h4')
                if h4_tag:
                    title = h4_tag.text.strip()
                    if title:
                        episodes.append({
                            'raw_title': title,
                            'page': page_num,
                            'url': url
                        })

            logger.debug(f"Found {len(episodes)} episodes on page {page_num}")
            return episodes

        except (requests.RequestException, ValueError) as e:
            if retry_count < self.MAX_RETRIES:
                logger.warning(
                    f"Error scraping page {page_num} (attempt {retry_count + 1}/{self.MAX_RETRIES}): {e}"
                )
                sleep(self.RETRY_DELAY * (retry_count + 1))  # Exponential backoff
                return self._scrape_page(page_num, retry_count + 1)
            else:
                logger.error(f"Failed to scrape page {page_num} after {self.MAX_RETRIES} retries: {e}")
                raise

    def close(self):
        """Close the requests session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


def scrape_friendly_fire_episodes(max_pages: int = 15) -> List[Dict[str, str]]:
    """
    Convenience function to scrape Friendly Fire episodes.

    Args:
        max_pages: Maximum number of pages to scrape

    Returns:
        List of episode dictionaries
    """
    with MaximumFunScraper(max_pages=max_pages) as scraper:
        return scraper.scrape_episodes()

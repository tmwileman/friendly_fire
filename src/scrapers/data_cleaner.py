"""
Data cleaning utilities for Friendly Fire episode data.
"""

import logging
import re
from typing import List, Dict
import pandas as pd

logger = logging.getLogger(__name__)


class EpisodeDataCleaner:
    """Clean and parse raw episode data from Maximum Fun scraper."""

    # Patterns to exclude (not actual movie episodes)
    EXCLUDE_PATTERNS = [
        'TRANSCRIPT',
        'Rogue One',
        'Pork Chop Feed',
        'Bonus',
        'Live Show',
        'Special',
    ]

    def __init__(self):
        """Initialize the data cleaner."""
        pass

    def clean_episodes(self, raw_episodes: List[Dict[str, str]]) -> pd.DataFrame:
        """
        Clean and parse raw episode data into structured DataFrame.

        Args:
            raw_episodes: List of dictionaries with 'raw_title', 'episode_url' keys

        Returns:
            pandas DataFrame with columns: number, episode, year, movie_year, episode_url

        Raises:
            ValueError: If no valid episodes found after cleaning
        """
        logger.info(f"Cleaning {len(raw_episodes)} raw episodes")

        # Extract episode numbers from TRANSCRIPT entries
        episode_mapping = {}
        for i, ep in enumerate(raw_episodes):
            title = ep['raw_title']
            if 'TRANSCRIPT' in title and 'Ep.' in title:
                # Extract episode number and movie title from transcript
                # Format: "TRANSCRIPT Friendly Fire Ep. 155: Operation Amsterdam (1959)"
                match = re.search(r'Ep\.\s*(\d+):\s*(.+?)(?:\s*\((\d{4})\))?$', title)
                if match:
                    ep_num = match.group(1)
                    movie_title = match.group(2).strip()
                    # Find the actual episode with matching title
                    for other_ep in raw_episodes:
                        other_title = other_ep['raw_title']
                        # Check if the other title contains the movie title and is not a transcript
                        if 'TRANSCRIPT' not in other_title and movie_title.lower() in other_title.lower():
                            episode_mapping[other_title] = {
                                'number': ep_num,
                                'url': other_ep.get('episode_url')
                            }
                            break

        # Parse into DataFrame
        df = self._parse_titles(raw_episodes, episode_mapping)

        # Clean and validate
        df = self._clean_episode_names(df)
        df = self._extract_years(df)
        df = self._filter_invalid_episodes(df)
        df = self._normalize_episode_numbers(df)
        df = self._create_search_field(df)

        # Drop rows with missing critical data
        df = df.dropna(subset=['episode', 'year'])

        if df.empty:
            raise ValueError("No valid episodes found after cleaning")

        logger.info(f"Successfully cleaned {len(df)} valid episodes")
        return df

    def _parse_titles(self, raw_episodes: List[Dict[str, str]], episode_mapping: Dict) -> pd.DataFrame:
        """
        Parse episode titles into components.

        Args:
            raw_episodes: List of episode dictionaries
            episode_mapping: Mapping of titles to episode numbers and URLs

        Returns:
            DataFrame with parsed episode data
        """
        parsed_data = []

        for ep_dict in raw_episodes:
            title = ep_dict['raw_title']
            episode_url = ep_dict.get('episode_url')

            # Check if we have episode number from transcript mapping
            if title in episode_mapping:
                number = episode_mapping[title]['number']
                episode_url = episode_mapping[title]['url'] or episode_url
                parsed_data.append([number, title, episode_url])
            else:
                # No episode number found, but still include the episode
                parsed_data.append([None, title, episode_url])

        df = pd.DataFrame(parsed_data, columns=['number', 'episode', 'episode_url'])
        return df

    def _clean_episode_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove quotes and clean episode names."""
        df = df.copy()
        df['episode'] = df['episode'].str.replace("'", '', regex=False)
        df['episode'] = df['episode'].str.replace('"', '', regex=False)
        return df

    def _extract_years(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract year from episode strings (format: 'Movie Title (Year)')."""
        df = df.copy()

        # Split on opening parenthesis, expand to multiple columns
        split_cols = df['episode'].str.split('(', expand=True)

        # First column is episode name, second is year with closing paren
        df['episode'] = split_cols[0].str.strip() if 0 in split_cols.columns else None

        # Extract year and remove closing parenthesis
        if 1 in split_cols.columns:
            df['year'] = split_cols[1].str.replace(')', '', regex=False).str.strip()
        else:
            df['year'] = None

        return df

    def _filter_invalid_episodes(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove non-movie episodes (transcripts, bonus content, etc.)."""
        df = df.copy()

        # Create a mask for valid episodes
        valid_mask = pd.Series([True] * len(df), index=df.index)

        # Apply each exclusion pattern
        for pattern in self.EXCLUDE_PATTERNS:
            if 'number' in df.columns and df['number'].notna().any():
                valid_mask &= ~df['number'].astype(str).str.contains(pattern, case=False, na=False)
            if 'episode' in df.columns and df['episode'].notna().any():
                valid_mask &= ~df['episode'].astype(str).str.contains(pattern, case=False, na=False)

        filtered_df = df[valid_mask]
        excluded_count = len(df) - len(filtered_df)

        if excluded_count > 0:
            logger.info(f"Filtered out {excluded_count} non-movie episodes")

        return filtered_df

    def _normalize_episode_numbers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and normalize episode numbers."""
        df = df.copy()

        if 'number' in df.columns:
            # Remove common prefixes
            df['number'] = df['number'].str.replace('Ep ', '', regex=False)
            df['number'] = df['number'].str.replace('Episode ', '', regex=False)
            df['number'] = df['number'].str.replace('Ep', '100', regex=False)  # Handle special case

            # Handle special episode name fix (from original code)
            if 'episode' in df.columns:
                df.loc[df['episode'].str.contains('100 Tora', na=False), 'episode'] = \
                    df.loc[df['episode'].str.contains('100 Tora', na=False), 'episode'].str.replace(
                        '100 Tora! Tora! Tora!', 'Tora! Tora! Tora!', regex=False
                    )

            # Convert to numeric where possible, keep as string otherwise
            df['number'] = df['number'].str.strip()

        return df

    def _create_search_field(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Create normalized search field for API queries.

        Combines episode name and year, removes special characters,
        converts to lowercase for better matching.
        """
        df = df.copy()

        if 'episode' in df.columns:
            # Remove special characters, keep only alphanumeric and spaces
            df['episode_normalized'] = df['episode'].apply(
                lambda x: re.sub(r'\W+', ' ', str(x)) if pd.notna(x) else ''
            )

            # Convert to lowercase
            df['episode_normalized'] = df['episode_normalized'].str.lower().str.strip()

        # Create combined movie-year field for OMDB searching
        if 'episode_normalized' in df.columns and 'year' in df.columns:
            df['movie_year'] = df['episode_normalized'] + df['year'].astype(str)

        return df


def clean_friendly_fire_data(raw_episodes: List[Dict[str, str]]) -> pd.DataFrame:
    """
    Convenience function to clean episode data.

    Args:
        raw_episodes: List of episode dictionaries from scraper

    Returns:
        Cleaned pandas DataFrame
    """
    cleaner = EpisodeDataCleaner()
    return cleaner.clean_episodes(raw_episodes)

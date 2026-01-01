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
            raw_episodes: List of dictionaries with 'raw_title' key

        Returns:
            pandas DataFrame with columns: number, episode, year, movie_year

        Raises:
            ValueError: If no valid episodes found after cleaning
        """
        logger.info(f"Cleaning {len(raw_episodes)} raw episodes")

        # Extract raw titles
        raw_titles = [ep['raw_title'] for ep in raw_episodes]

        # Parse into DataFrame
        df = self._parse_titles(raw_titles)

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

    def _parse_titles(self, titles: List[str]) -> pd.DataFrame:
        """
        Parse episode titles into components.

        Expected format: "Ep 123: Movie Title (Year)"
        """
        parsed_data = []

        for title in titles:
            # Split on first colon to separate episode number from content
            parts = title.strip().split(':', 1)

            if len(parts) == 2:
                number_part = parts[0].strip()
                content_part = parts[1].strip()
                parsed_data.append([number_part, content_part])
            else:
                # Handle edge cases where there's no colon
                logger.debug(f"Skipping malformed title: {title}")
                parsed_data.append([None, title])

        df = pd.DataFrame(parsed_data, columns=['number', 'episode'])
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

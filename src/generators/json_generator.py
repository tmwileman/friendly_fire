"""
JSON generator for creating output data files for the web interface.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class JSONGenerator:
    """Generate JSON output files for the Friendly Fire web interface."""

    def __init__(self, output_dir: str = 'docs/data'):
        """
        Initialize the JSON generator.

        Args:
            output_dir: Directory to write JSON files to
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_movies_json(
        self,
        episodes_df: pd.DataFrame,
        omdb_data: List[Optional[Dict]],
        streaming_data: List[Optional[Dict]],
        output_file: str = 'movies.json'
    ) -> Path:
        """
        Generate the main movies.json file combining all data sources.

        Args:
            episodes_df: DataFrame with episode data (from data_cleaner)
            omdb_data: List of OMDB API responses
            streaming_data: List of Streaming API responses
            output_file: Output filename

        Returns:
            Path to the generated JSON file
        """
        logger.info("Generating movies.json")

        movies = []

        # Iterate through episodes and combine data
        for position, (idx, row) in enumerate(episodes_df.iterrows()):
            # Get corresponding OMDB data using position, not DataFrame index
            omdb_info = omdb_data[position] if position < len(omdb_data) else None

            # Get IMDb ID if available
            imdb_id = omdb_info.get('imdbID') if omdb_info else None

            # Get corresponding streaming data
            streaming_info = None
            if imdb_id:
                for stream in streaming_data:
                    if stream and stream.get('imdb_id') == imdb_id:
                        streaming_info = stream
                        break

            # Build movie entry (include all movies)
            # If no IMDb data, use episode data from scraper
            if omdb_info and imdb_id:
                movie = {
                    'episode_number': str(row.get('number', '')) if pd.notna(row.get('number')) else None,
                    'episode_url': row.get('episode_url'),
                    'title': omdb_info.get('Title', row.get('episode', '')),
                    'year': omdb_info.get('Year', row.get('year', '')),
                    'imdb_id': imdb_id,
                    'imdb_rating': omdb_info.get('imdbRating', 'N/A'),
                    'imdb_votes': omdb_info.get('imdbVotes', 'N/A'),
                    'imdb_url': f"https://www.imdb.com/title/{imdb_id}",
                    'runtime': omdb_info.get('Runtime', 'N/A'),
                    'genre': omdb_info.get('Genre', 'N/A'),
                    'director': omdb_info.get('Director', 'N/A'),
                    'plot': omdb_info.get('Plot', 'N/A'),
                    'poster': omdb_info.get('Poster', ''),
                    'streaming_options': []
                }
            else:
                # No IMDb data - use scraped data with disclaimer
                logger.warning(f"No IMDb data for episode {row.get('number')}: {row.get('episode')}")
                movie = {
                    'episode_number': str(row.get('number', '')) if pd.notna(row.get('number')) else None,
                    'episode_url': row.get('episode_url'),
                    'title': row.get('episode', 'Unknown'),
                    'year': row.get('year', 'N/A'),
                    'imdb_id': None,
                    'imdb_rating': 'N/A',
                    'imdb_votes': 'N/A',
                    'imdb_url': None,
                    'runtime': 'N/A',
                    'genre': 'N/A',
                    'director': 'N/A',
                    'plot': 'IMDb data not found for this movie. Episode information scraped from podcast website.',
                    'poster': '',
                    'streaming_options': []
                }

            # Add streaming options if available
            if streaming_info and streaming_info.get('streaming_options'):
                movie['streaming_options'] = streaming_info['streaming_options']

            movies.append(movie)

        # Create final JSON structure
        output_data = {
            'last_updated': datetime.utcnow().isoformat() + 'Z',
            'total_movies': len(movies),
            'movies': movies
        }

        # Write to file
        output_path = self.output_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)

        logger.info(f"Successfully generated {output_path} with {len(movies)} movies")
        return output_path

    def generate_metadata_json(
        self,
        total_movies: int,
        successful_omdb: int,
        successful_streaming: int,
        output_file: str = 'metadata.json'
    ) -> Path:
        """
        Generate metadata file with information about the last update.

        Args:
            total_movies: Total number of movies processed
            successful_omdb: Number of successful OMDB queries
            successful_streaming: Number of successful streaming queries
            output_file: Output filename

        Returns:
            Path to the generated JSON file
        """
        logger.info("Generating metadata.json")

        metadata = {
            'last_updated': datetime.utcnow().isoformat() + 'Z',
            'last_updated_readable': datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC'),
            'statistics': {
                'total_movies': total_movies,
                'successful_omdb_queries': successful_omdb,
                'successful_streaming_queries': successful_streaming,
                'omdb_success_rate': f"{(successful_omdb / total_movies * 100):.1f}%" if total_movies > 0 else "0%",
                'streaming_success_rate': f"{(successful_streaming / total_movies * 100):.1f}%" if total_movies > 0 else "0%"
            },
            'data_sources': {
                'podcast': 'Maximum Fun - Friendly Fire',
                'movie_metadata': 'OMDB API',
                'streaming_availability': 'Streaming Availability API (RapidAPI)'
            }
        }

        output_path = self.output_dir / output_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"Successfully generated {output_path}")
        return output_path

    def generate_all(
        self,
        episodes_df: pd.DataFrame,
        omdb_data: List[Optional[Dict]],
        streaming_data: List[Optional[Dict]]
    ) -> Dict[str, Path]:
        """
        Generate all JSON output files.

        Args:
            episodes_df: DataFrame with episode data
            omdb_data: List of OMDB API responses
            streaming_data: List of Streaming API responses

        Returns:
            Dictionary mapping file type to output path
        """
        # Generate movies JSON
        movies_path = self.generate_movies_json(
            episodes_df,
            omdb_data,
            streaming_data
        )

        # Calculate statistics
        total_movies = len(episodes_df)
        successful_omdb = sum(1 for d in omdb_data if d and d.get('imdbID'))
        successful_streaming = sum(1 for d in streaming_data if d and d.get('streaming_options'))

        # Generate metadata JSON
        metadata_path = self.generate_metadata_json(
            total_movies,
            successful_omdb,
            successful_streaming
        )

        return {
            'movies': movies_path,
            'metadata': metadata_path
        }


def generate_json_output(
    episodes_df: pd.DataFrame,
    omdb_data: List[Optional[Dict]],
    streaming_data: List[Optional[Dict]],
    output_dir: str = 'docs/data'
) -> Dict[str, Path]:
    """
    Convenience function to generate all JSON output files.

    Args:
        episodes_df: DataFrame with episode data
        omdb_data: List of OMDB API responses
        streaming_data: List of Streaming API responses
        output_dir: Directory to write JSON files to

    Returns:
        Dictionary mapping file type to output path
    """
    generator = JSONGenerator(output_dir)
    return generator.generate_all(episodes_df, omdb_data, streaming_data)

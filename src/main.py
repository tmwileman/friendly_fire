#!/usr/bin/env python
"""
Friendly Fire Movie Tracker - Main Orchestration Script

This script coordinates the entire data pipeline:
1. Scrape Maximum Fun for podcast episodes
2. Clean and parse episode data
3. Query OMDB API for movie metadata
4. Query Streaming Availability API for where to watch
5. Generate JSON output files for the web interface
"""

import logging
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.maximumfun_scraper import scrape_friendly_fire_episodes
from scrapers.data_cleaner import clean_friendly_fire_data
from api.omdb_client import OMDBClient
from api.streaming_client import StreamingAvailabilityClient
from generators.json_generator import generate_json_output

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('friendly_fire.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main execution function."""
    logger.info("="*60)
    logger.info("Friendly Fire Movie Tracker - Starting Data Pipeline")
    logger.info("="*60)

    try:
        # Load environment variables from .env file if it exists
        load_dotenv()
        logger.info("Environment variables loaded")

        # Step 1: Scrape podcast episodes
        logger.info("\n[Step 1/5] Scraping Maximum Fun for episodes...")
        raw_episodes = scrape_friendly_fire_episodes(max_pages=20)
        logger.info(f"✓ Scraped {len(raw_episodes)} raw episodes")

        if not raw_episodes:
            logger.error("No episodes found. Exiting.")
            return 1

        # Step 2: Clean and parse episode data
        logger.info("\n[Step 2/5] Cleaning and parsing episode data...")
        episodes_df = clean_friendly_fire_data(raw_episodes)
        logger.info(f"✓ Cleaned data: {len(episodes_df)} valid movie episodes")

        if episodes_df.empty:
            logger.error("No valid episodes after cleaning. Exiting.")
            return 1

        # Step 3: Query OMDB API
        logger.info("\n[Step 3/5] Querying OMDB API for movie metadata...")

        # Extract titles and years for OMDB queries
        titles = episodes_df['episode_normalized'].tolist()
        years = episodes_df['year'].tolist()

        with OMDBClient() as omdb:
            omdb_data = omdb.search_movies_batch(titles, years)

        successful_omdb = sum(1 for d in omdb_data if d and d.get('imdbID'))
        logger.info(f"✓ OMDB queries complete: {successful_omdb}/{len(titles)} successful")

        # Step 4: Query Streaming Availability API
        logger.info("\n[Step 4/5] Querying Streaming Availability API...")

        # Extract IMDb IDs from OMDB data
        imdb_ids = [d.get('imdbID') for d in omdb_data if d and d.get('imdbID')]

        if not imdb_ids:
            logger.warning("No IMDb IDs found. Skipping streaming queries.")
            streaming_data = []
        else:
            with StreamingAvailabilityClient() as streaming:
                streaming_data = streaming.get_streaming_options_batch(imdb_ids, country='us')

            successful_streaming = sum(1 for d in streaming_data if d)
            logger.info(f"✓ Streaming queries complete: {successful_streaming}/{len(imdb_ids)} successful")

        # Step 5: Generate JSON output
        logger.info("\n[Step 5/5] Generating JSON output files...")

        output_paths = generate_json_output(
            episodes_df,
            omdb_data,
            streaming_data,
            output_dir='docs/data'
        )

        logger.info(f"✓ Generated {output_paths['movies']}")
        logger.info(f"✓ Generated {output_paths['metadata']}")

        # Summary
        logger.info("\n" + "="*60)
        logger.info("Pipeline Complete!")
        logger.info("="*60)
        logger.info(f"Total episodes scraped: {len(raw_episodes)}")
        logger.info(f"Valid movie episodes: {len(episodes_df)}")
        logger.info(f"Successful OMDB queries: {successful_omdb}/{len(titles)}")
        logger.info(f"Successful streaming queries: {len([d for d in streaming_data if d])}/{len(imdb_ids)}")
        logger.info(f"Output files: {', '.join(str(p) for p in output_paths.values())}")
        logger.info("="*60)

        return 0

    except Exception as e:
        logger.error(f"\n❌ Pipeline failed with error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

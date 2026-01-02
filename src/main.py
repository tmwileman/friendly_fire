#!/usr/bin/env python
"""
Friendly Fire Movie Tracker - Main Orchestration Script

This script coordinates the entire data pipeline:
1. Scrape Maximum Fun for podcast episodes
2. Clean and parse episode data
3. Query OMDB API for movie metadata
4. Query Streaming Availability API for where to watch
5. Generate JSON output files for the web interface

Usage:
    python src/main.py                    # Run full pipeline
    python src/main.py --skip-apis        # Skip OMDB and streaming APIs (use cached data)
    python src/main.py --skip-streaming   # Skip only streaming API
    python src/main.py --skip-scraping    # Skip scraping, use existing data
"""

import argparse
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


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Friendly Fire Movie Tracker - Data Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python src/main.py                    # Run full pipeline
  python src/main.py --skip-apis        # Skip all API calls (use existing data)
  python src/main.py --skip-streaming   # Skip only streaming API
  python src/main.py --skip-scraping    # Use existing scraped data
        """
    )
    parser.add_argument(
        '--skip-apis',
        action='store_true',
        help='Skip both OMDB and streaming API calls (uses existing cached data)'
    )
    parser.add_argument(
        '--skip-streaming',
        action='store_true',
        help='Skip streaming API calls only'
    )
    parser.add_argument(
        '--skip-scraping',
        action='store_true',
        help='Skip scraping podcast episodes (uses existing data files)'
    )
    return parser.parse_args()


def main():
    """Main execution function."""
    args = parse_args()

    logger.info("="*60)
    logger.info("Friendly Fire Movie Tracker - Starting Data Pipeline")
    if args.skip_apis:
        logger.info("⚠️  Running in API-SKIP mode (using cached data)")
    elif args.skip_streaming:
        logger.info("⚠️  Skipping streaming API calls")
    if args.skip_scraping:
        logger.info("⚠️  Skipping scraping (using existing data)")
    logger.info("="*60)

    try:
        # Load environment variables from .env file if it exists
        load_dotenv()
        logger.info("Environment variables loaded")

        # Step 1: Scrape podcast episodes (or load from cache)
        if args.skip_scraping:
            logger.info("\n[Step 1/5] Loading existing episode data...")
            import json
            with open('docs/data/movies.json', 'r') as f:
                existing_data = json.load(f)
            # Reconstruct raw episodes format
            raw_episodes = []
            for movie in existing_data['movies']:
                raw_episodes.append({
                    'raw_title': f"{movie.get('title', '')} ({movie.get('year', '')})",
                    'episode_url': movie.get('episode_url', '')
                })
            logger.info(f"✓ Loaded {len(raw_episodes)} episodes from existing data")
        else:
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

        # Step 3: Query OMDB API (or use cache)
        if args.skip_apis:
            logger.info("\n[Step 3/5] Skipping OMDB API (using cached data)...")
            import json
            with open('docs/data/movies.json', 'r') as f:
                existing_data = json.load(f)
            # Reconstruct OMDB data format
            omdb_data = []
            for movie in existing_data['movies']:
                if movie.get('imdb_id'):
                    omdb_data.append({
                        'imdbID': movie.get('imdb_id'),
                        'Title': movie.get('title'),
                        'Year': movie.get('year'),
                        'imdbRating': movie.get('imdb_rating'),
                        'imdbVotes': movie.get('imdb_votes'),
                        'Runtime': movie.get('runtime'),
                        'Genre': movie.get('genre'),
                        'Director': movie.get('director'),
                        'Plot': movie.get('plot'),
                        'Poster': movie.get('poster')
                    })
                else:
                    omdb_data.append(None)
            successful_omdb = len([d for d in omdb_data if d])
            logger.info(f"✓ Using cached OMDB data: {successful_omdb}/{len(omdb_data)} movies")
        else:
            logger.info("\n[Step 3/5] Querying OMDB API for movie metadata...")
            titles = episodes_df['episode_normalized'].tolist()
            years = episodes_df['year'].tolist()

            with OMDBClient() as omdb:
                omdb_data = omdb.search_movies_batch(titles, years)

            successful_omdb = sum(1 for d in omdb_data if d and d.get('imdbID'))
            logger.info(f"✓ OMDB queries complete: {successful_omdb}/{len(titles)} successful")

        # Step 4: Query Streaming Availability API (or use cache/skip)
        if args.skip_apis or args.skip_streaming:
            logger.info("\n[Step 4/5] Skipping Streaming API (using cached data)...")
            import json
            with open('docs/data/movies.json', 'r') as f:
                existing_data = json.load(f)
            # Reconstruct streaming data format
            streaming_data = []
            for movie in existing_data['movies']:
                if movie.get('streaming_options'):
                    streaming_data.append({
                        'imdb_id': movie.get('imdb_id'),
                        'streaming_options': movie.get('streaming_options')
                    })
                else:
                    streaming_data.append(None)
            successful_streaming = len([d for d in streaming_data if d and d.get('streaming_options')])
            logger.info(f"✓ Using cached streaming data: {successful_streaming} movies with streaming info")
        else:
            logger.info("\n[Step 4/5] Querying Streaming Availability API...")
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
        logger.info(f"Total episodes processed: {len(raw_episodes)}")
        logger.info(f"Valid movie episodes: {len(episodes_df)}")
        logger.info(f"Movies with OMDB data: {len([d for d in omdb_data if d])}")
        logger.info(f"Movies with streaming data: {len([d for d in streaming_data if d])}")
        logger.info(f"Output files: {', '.join(str(p) for p in output_paths.values())}")
        logger.info("="*60)

        return 0

    except Exception as e:
        logger.error(f"\n❌ Pipeline failed with error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)

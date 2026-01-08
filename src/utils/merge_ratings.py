#!/usr/bin/env python3
"""
One-time script to merge host ratings from Notion CSV export into movies.json

Usage:
    python src/utils/merge_ratings.py ratings.csv
    python src/utils/merge_ratings.py ratings.csv --dry-run
    python src/utils/merge_ratings.py ratings.csv --output docs/data/movies.json
"""

import argparse
import json
import csv
import sys
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
from datetime import datetime
import shutil


class RatingMerger:
    """Merges host ratings from CSV into movies.json"""

    def __init__(self, movies_json_path: str, csv_path: str):
        self.movies_json_path = Path(movies_json_path)
        self.csv_path = Path(csv_path)
        self.movies_data = {}
        self.movies = []
        self.ratings = []

    def load_movies(self):
        """Load existing movies.json"""
        if not self.movies_json_path.exists():
            print(f"Error: {self.movies_json_path} does not exist")
            sys.exit(1)

        with open(self.movies_json_path, 'r', encoding='utf-8') as f:
            self.movies_data = json.load(f)
            self.movies = self.movies_data.get('movies', [])
            print(f"✓ Loaded {len(self.movies)} movies from {self.movies_json_path}")

    def load_ratings(self):
        """Load ratings from CSV"""
        if not self.csv_path.exists():
            print(f"Error: {self.csv_path} does not exist")
            sys.exit(1)

        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            self.ratings = list(reader)
            print(f"✓ Loaded {len(self.ratings)} ratings from {self.csv_path}")

            # Validate expected columns (support both "Title" and "Name")
            if self.ratings:
                actual = set(self.ratings[0].keys())
                # Check for either Title or Name column
                has_title = 'Title' in actual or 'Name' in actual
                has_year = 'Year' in actual
                has_ratings = {'AR', 'BR', 'JR', 'Rating'}.issubset(actual)

                if not (has_title and has_year and has_ratings):
                    print(f"Warning: CSV may be missing required columns")
                    print(f"Available columns: {actual}")

                # If using "Name" instead of "Title", normalize it
                if 'Name' in actual and 'Title' not in actual:
                    print(f"Note: Using 'Name' column as 'Title'")

    def clean_title(self, title: str) -> str:
        """Clean title by removing year and extra metadata"""
        if not title:
            return ""
        import re
        # Remove year in parentheses and everything after it
        # e.g., "Movie Title (1999) (LIVE) (Bonus)" -> "Movie Title"
        title = re.sub(r'\s*\(\d{4}\).*$', '', title).strip()
        return title

    def normalize_title(self, title: str) -> str:
        """Normalize title for fuzzy matching"""
        if not title:
            return ""
        # First clean the title
        title = self.clean_title(title)
        # Lowercase, remove "the", strip punctuation
        title = title.lower().strip()
        if title.startswith('the '):
            title = title[4:]
        # Remove common punctuation
        for char in [':', ',', '.', '!', '?', '-', "'", '"']:
            title = title.replace(char, '')
        return title.strip()

    def fuzzy_match_score(self, title1: str, title2: str) -> float:
        """Calculate fuzzy match score (0.0 to 1.0)"""
        norm1 = self.normalize_title(title1)
        norm2 = self.normalize_title(title2)
        return SequenceMatcher(None, norm1, norm2).ratio()

    def find_matching_movie(self, rating: Dict) -> Tuple[Optional[Dict], float]:
        """
        Find best matching movie for a rating entry.
        Returns (movie, confidence_score) or (None, 0.0)
        """
        import re

        # Support both "Title" and "Name" columns
        rating_title = rating.get('Title') or rating.get('Name', '')
        rating_year_raw = rating.get('Year', '')

        # Convert year to string, handling floats (e.g., 1985.0 -> "1985")
        if isinstance(rating_year_raw, float):
            rating_year = str(int(rating_year_raw)) if not math.isnan(rating_year_raw) else ''
        else:
            rating_year = str(rating_year_raw).strip()

        # Extract year from title if present (e.g., "Movie Name (1999)")
        if rating_title and '(' in rating_title:
            match = re.search(r'\((\d{4})\)', rating_title)
            if match:
                extracted_year = match.group(1)
                if not rating_year or rating_year == 'nan':
                    rating_year = extracted_year

        # Clean the title (remove year and extra metadata)
        rating_title = self.clean_title(rating_title)

        if not rating_title or not rating_year or rating_year == 'nan':
            return None, 0.0

        best_match = None
        best_score = 0.0

        for movie in self.movies:
            movie_year = str(movie.get('year', '')).strip()

            # Require exact year match
            if movie_year != rating_year:
                continue

            # Fuzzy title match
            movie_title = movie.get('title', '')
            score = self.fuzzy_match_score(rating_title, movie_title)

            if score > best_score:
                best_score = score
                best_match = movie

        # Require 90% similarity threshold
        if best_score >= 0.90:
            return best_match, best_score

        return None, best_score

    def sanitize_value(self, value: str) -> Optional[str]:
        """Sanitize rating value - handle empty strings, None, etc."""
        if value is None or value == '':
            return None
        value = str(value).strip()
        if value.lower() in ['', 'n/a', 'none', '-']:
            return None
        return value

    def merge(self) -> Dict:
        """
        Merge ratings into movies.
        Returns statistics about the merge operation.
        """
        matched = 0
        unmatched = []
        match_details = []

        for rating in self.ratings:
            movie, confidence = self.find_matching_movie(rating)

            if movie and confidence >= 0.90:
                # Merge rating data
                movie['ar'] = self.sanitize_value(rating.get('AR'))
                movie['br'] = self.sanitize_value(rating.get('BR'))
                movie['jr'] = self.sanitize_value(rating.get('JR'))
                movie['rating'] = self.sanitize_value(rating.get('Rating'))
                movie['rating_notes'] = rating.get('Rating Notes', '').strip()

                matched += 1
                csv_title = rating.get('Title') or rating.get('Name', '')
                csv_year = rating.get('Year', '')
                match_details.append({
                    'csv_title': csv_title,
                    'csv_year': csv_year,
                    'matched_title': movie.get('title'),
                    'matched_year': movie.get('year'),
                    'confidence': f"{confidence:.1%}"
                })
            else:
                csv_title_raw = rating.get('Title') or rating.get('Name', '')
                csv_year_raw = rating.get('Year', '')
                # Convert year properly for display
                if isinstance(csv_year_raw, float):
                    csv_year = str(int(csv_year_raw)) if not math.isnan(csv_year_raw) else ''
                else:
                    csv_year = str(csv_year_raw).strip()
                unmatched.append({
                    'title': csv_title_raw,
                    'year': csv_year,
                    'best_confidence': f"{confidence:.1%}" if confidence > 0 else "No match"
                })

        # Add empty rating fields to unmatched movies
        for movie in self.movies:
            if 'ar' not in movie:
                movie['ar'] = None
                movie['br'] = None
                movie['jr'] = None
                movie['rating'] = None
                movie['rating_notes'] = ''

        return {
            'matched': matched,
            'unmatched': unmatched,
            'match_details': match_details,
            'total_ratings': len(self.ratings),
            'total_movies': len(self.movies)
        }

    def print_report(self, stats: Dict):
        """Print merge statistics report"""
        print("\n" + "="*60)
        print("MERGE REPORT")
        print("="*60)
        print(f"Total movies in database: {stats['total_movies']}")
        print(f"Total ratings in CSV: {stats['total_ratings']}")
        print(f"Successfully matched: {stats['matched']} ({stats['matched']/stats['total_ratings']*100:.1f}%)")
        print(f"Unmatched: {len(stats['unmatched'])}")

        if stats['match_details']:
            print("\n" + "-"*60)
            print("MATCHED MOVIES:")
            print("-"*60)
            for detail in stats['match_details'][:10]:  # Show first 10
                print(f"  {detail['csv_title']} ({detail['csv_year']})")
                print(f"    → {detail['matched_title']} ({detail['matched_year']}) - {detail['confidence']}")
            if len(stats['match_details']) > 10:
                print(f"  ... and {len(stats['match_details']) - 10} more")

        if stats['unmatched']:
            print("\n" + "-"*60)
            print("UNMATCHED RATINGS:")
            print("-"*60)
            for item in stats['unmatched']:
                print(f"  {item['title']} ({item['year']}) - {item['best_confidence']}")

        print("="*60 + "\n")

    def create_backup(self):
        """Create backup of original movies.json"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = self.movies_json_path.with_suffix(f'.backup_{timestamp}.json')
        shutil.copy(self.movies_json_path, backup_path)
        print(f"✓ Backup created: {backup_path}")
        return backup_path

    def save(self):
        """Save updated movies.json"""
        with open(self.movies_json_path, 'w', encoding='utf-8') as f:
            json.dump(self.movies_data, f, indent=2, ensure_ascii=False)
        print(f"✓ Saved updated data to {self.movies_json_path}")


def main():
    parser = argparse.ArgumentParser(
        description='Merge host ratings from CSV into movies.json'
    )
    parser.add_argument(
        'csv_file',
        help='Path to CSV file with ratings (columns: Title, Year, AR, BR, JR, Rating, Rating Notes)'
    )
    parser.add_argument(
        '--output',
        default='docs/data/movies.json',
        help='Path to movies.json file (default: docs/data/movies.json)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without saving'
    )

    args = parser.parse_args()

    # Initialize merger
    merger = RatingMerger(args.output, args.csv_file)

    # Load data
    merger.load_movies()
    merger.load_ratings()

    # Perform merge
    print("\nMatching and merging ratings...")
    stats = merger.merge()

    # Print report
    merger.print_report(stats)

    # Save if not dry run
    if args.dry_run:
        print("DRY RUN MODE - No files were modified")
        print(f"Run without --dry-run to save changes to {args.output}")
    else:
        merger.create_backup()
        merger.save()
        print("\n✓ Merge complete!")
        print(f"  Matched: {stats['matched']}/{stats['total_ratings']}")
        print(f"  Review the backup file if you need to rollback")


if __name__ == '__main__':
    main()

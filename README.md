# 🎬 Friendly Fire Movie Tracker

> Track movies from the [Friendly Fire podcast](https://maximumfun.org/podcasts/friendly-fire/) and find where to watch them online.

[![Update Data](https://github.com/thwile/friendly_fire/actions/workflows/update-data.yml/badge.svg)](https://github.com/thwile/friendly_fire/actions/workflows/update-data.yml)

## Overview

An automated web application that tracks all movies reviewed on the Friendly Fire podcast, enriches them with IMDb metadata, finds streaming availability across major platforms, and presents everything in an interactive, searchable interface.

**Live Site:** [View the tracker](https://thwile.github.io/friendly_fire/) _(will be available once GitHub Pages is enabled)_

## Features

- 🔄 **Automated Updates** - Runs weekly via GitHub Actions to check for new episodes
- 🎯 **Comprehensive Data** - IMDb ratings, genres, directors, and more
- 📺 **Streaming Availability** - Find where to watch across Netflix, Prime, Hulu, Disney+, HBO Max, and more
- 🔍 **Interactive Search** - Search, filter, and sort by any criteria
- 📱 **Mobile-Friendly** - Responsive design works on all devices
- 🆓 **Completely Free** - Uses free tiers of GitHub Pages, OMDB, and Streaming APIs

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Repository                        │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │         GitHub Actions (Weekly Schedule)           │    │
│  │                                                      │    │
│  │  1. Scrape maximumfun.org for episodes             │    │
│  │  2. Clean and parse episode data                   │    │
│  │  3. Query OMDB API (IMDb metadata)                 │    │
│  │  4. Query Streaming Availability API               │    │
│  │  5. Generate JSON data files                       │    │
│  │  6. Deploy to GitHub Pages                         │    │
│  └────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│  ┌────────────────────────────────────────────────────┐    │
│  │              GitHub Pages (gh-pages)               │    │
│  │                                                      │    │
│  │  • index.html (interactive interface)              │    │
│  │  • data/movies.json (generated data)               │    │
│  │  • JavaScript, CSS, assets                         │    │
│  └────────────────────────────────────────────────────┘    │
└───────────────────────────┬──────────────────────────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │   End Users   │
                    │ (Web Browser) │
                    └───────────────┘
```

### Data Pipeline

1. **Scrape** - Extracts episode titles from Maximum Fun website
2. **Clean** - Parses episode numbers, movie titles, and years
3. **Enrich** - Queries OMDB API for IMDb IDs and metadata
4. **Discover** - Queries Streaming Availability API for watch options
5. **Generate** - Creates JSON files for the web interface
6. **Deploy** - Commits to gh-pages branch for GitHub Pages hosting

## Project Structure

```
friendly_fire/
├── .github/workflows/
│   └── update-data.yml           # GitHub Actions workflow
├── src/
│   ├── scrapers/
│   │   ├── maximumfun_scraper.py # Podcast website scraper
│   │   └── data_cleaner.py       # Data cleaning utilities
│   ├── api/
│   │   ├── omdb_client.py        # OMDB API client
│   │   └── streaming_client.py   # Streaming Availability API client
│   ├── generators/
│   │   └── json_generator.py     # JSON output generator
│   └── main.py                    # Main orchestration script
├── docs/                          # GitHub Pages source
│   ├── index.html                 # Main web interface
│   ├── styles.css                 # Styling
│   ├── app.js                     # Frontend JavaScript
│   └── data/
│       ├── movies.json            # Generated movie data
│       └── metadata.json          # Update metadata
├── tests/                         # Unit tests
├── .env.example                   # Environment variables template
├── .gitignore                     # Git ignore rules
├── requirements.txt               # Python dependencies
├── main_legacy.py                 # Original implementation (archived)
└── README.md                      # This file
```

## Setup Instructions

### For Users (View the Site)

Just visit the live site! No setup required.

**Live URL:** `https://thwile.github.io/friendly_fire/`

### For Developers (Local Development)

#### Prerequisites

- Python 3.11+
- Git

#### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/thwile/friendly_fire.git
   cd friendly_fire
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up API keys**

   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your API keys:
   ```
   OMDB_API_KEY=your_omdb_key_here
   RAPIDAPI_KEY=your_rapidapi_key_here
   ```

   **Getting API Keys:**
   - **OMDB API**: Get a free key at [omdbapi.com/apikey.aspx](http://www.omdbapi.com/apikey.aspx) (1,000 requests/day free)
   - **RapidAPI**: Sign up at [rapidapi.com](https://rapidapi.com/) and subscribe to [Streaming Availability API](https://rapidapi.com/movie-of-the-night-movie-of-the-night-default/api/streaming-availability) (100 requests/day free)

5. **Run the pipeline**
   ```bash
   python src/main.py
   ```

   This will:
   - Scrape podcast episodes
   - Query APIs for data
   - Generate JSON files in `docs/data/`

6. **View locally**

   Start a local web server:
   ```bash
   cd docs
   python -m http.server 8000
   ```

   Open browser to: `http://localhost:8000`

### For Maintainers (GitHub Actions Setup)

1. **Configure GitHub Secrets**

   Go to: `Settings` → `Secrets and variables` → `Actions` → `New repository secret`

   Add two secrets:
   - `OMDB_API_KEY` - Your OMDB API key
   - `RAPIDAPI_KEY` - Your RapidAPI key

2. **Enable GitHub Pages**

   Go to: `Settings` → `Pages`
   - Source: Deploy from a branch
   - Branch: `gh-pages`, `/ (root)`
   - Save

3. **Trigger Workflow**

   - The workflow runs automatically every Monday at noon UTC
   - Manual trigger: Go to `Actions` → `Update Friendly Fire Data` → `Run workflow`

4. **Monitor**

   - Check workflow status in the Actions tab
   - View logs for any errors
   - See deployment at your GitHub Pages URL

## API Usage & Limits

### Free Tier Limits

| Service | Free Tier | Usage |
|---------|-----------|-------|
| GitHub Actions | 2,000 min/month | ~40 min/month |
| GitHub Pages | 100GB bandwidth | <1GB/month |
| OMDB API | 1,000 requests/day | ~100/week |
| Streaming API | 100 requests/day | ~100/week |

**Cost:** $0/month (completely free)

### Rate Limiting

- OMDB: 0.5 second delay between requests
- Streaming API: 1 second delay between requests
- Results are cached to minimize API calls

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

```bash
# Format code
black src/ tests/

# Lint code
flake8 src/ tests/
```

### Adding New Features

1. Create a new branch
2. Make changes
3. Add tests
4. Submit pull request

## Troubleshooting

### Workflow Fails

- Check Actions tab for error logs
- Verify API keys are set correctly in Secrets
- Check API quotas haven't been exceeded

### No Data on Site

- Ensure workflow has run at least once
- Check gh-pages branch exists and has data
- Verify GitHub Pages is enabled

### Local Development Issues

- Ensure `.env` file exists with valid API keys
- Check Python version (3.11+ required)
- Install all dependencies from requirements.txt

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Credits

- **Podcast:** [Friendly Fire](https://maximumfun.org/podcasts/friendly-fire/) by Maximum Fun
- **Data Sources:**
  - [OMDB API](http://www.omdbapi.com/) - Movie metadata
  - [Streaming Availability API](https://www.movieofthenight.com/about/api) - Streaming data
- **Hosting:** GitHub Pages

## License

This is an unofficial fan project. All movie data and metadata belong to their respective owners.

## Support

- **Issues:** [GitHub Issues](https://github.com/thwile/friendly_fire/issues)
- **Podcast:** Support [Friendly Fire on Maximum Fun](https://maximumfun.org/join/)

---

Made with ❤️ by fans of Friendly Fire

Listen to the podcast wherever you get your podcasts!
# Pipeline Usage Guide

The Friendly Fire Movie Tracker pipeline has flexible options to control which steps run. This is especially useful for conserving API quota and speeding up development.

## Basic Usage

### Run Full Pipeline (All API Calls)
```bash
python src/main.py
```
This runs all 5 steps:
1. Scrape Maximum Fun podcast episodes
2. Clean and parse episode data  
3. Query OMDB API for movie metadata
4. Query Streaming Availability API
5. Generate JSON output files

⚠️ **Uses API quota** for both OMDB and Streaming Availability

---

## Skip Options (Conserve API Quota)

### Skip All API Calls (UI Development)
```bash
python src/main.py --skip-apis
```
**Use this when:**
- Making UI changes (HTML/CSS/JS)
- Testing the website locally
- You don't want to use any API quota

**What it does:**
- Scrapes podcast for new episodes
- Uses cached OMDB data from last run
- Uses cached streaming data from last run
- Regenerates JSON files with existing data

✅ **No API calls made** - Perfect for frontend work!

---

### Skip Only Streaming API
```bash
python src/main.py --skip-streaming
```
**Use this when:**
- You want fresh OMDB data (ratings, posters, etc.)
- But want to conserve streaming API quota
- Streaming data doesn't change often

**What it does:**
- Scrapes podcast
- Queries OMDB API ✓
- Uses cached streaming data
- Regenerates JSON files

⚠️ **Uses OMDB API quota only**

---

### Skip Scraping (Speed Up Testing)
```bash
python src/main.py --skip-scraping
```
**Use this when:**
- Testing API changes
- Episode list hasn't changed
- Want to speed up the pipeline

**What it does:**
- Uses existing episode data
- Queries both APIs
- Regenerates JSON files

⚠️ **Uses both API quotas**

---

## Combining Flags

You can combine flags for maximum control:

```bash
# Skip scraping AND APIs (fastest, for pure JSON regeneration)
python src/main.py --skip-scraping --skip-apis
```

---

## When to Use Each Option

| Scenario | Command | APIs Used |
|----------|---------|-----------|
| 🎨 **UI/CSS changes only** | `--skip-apis` | None |
| 📊 **Update movie ratings** | `--skip-streaming` | OMDB only |
| 🎬 **Update streaming services** | (no flags) | Both |
| 🚀 **Quick test** | `--skip-scraping --skip-apis` | None |
| 🆕 **New podcast episodes** | (no flags) | Both |

---

## API Quota Limits

### OMDB API
- Free tier: 1,000 requests/day
- Each movie = 1 request
- 169 movies = 169 requests

### Streaming Availability API (RapidAPI)
- Basic (free): Limited monthly requests
- **Recommendation:** Use `--skip-streaming` most of the time
- Only run full pipeline when you need streaming updates

---

## Examples

```bash
# Making CSS changes to the website
python src/main.py --skip-apis

# New episode just released, need full update
python src/main.py

# Testing OMDB integration changes
python src/main.py --skip-streaming --skip-scraping

# Regenerate JSON without any external calls
python src/main.py --skip-scraping --skip-apis
```

---

## Tips

💡 **Best Practice:** Use `--skip-apis` for day-to-day work on the UI. Only run the full pipeline when you actually need fresh data.

💡 **Streaming Data Changes Rarely:** Most streaming services update monthly. You don't need to query this API often.

💡 **OMDB Data is Stable:** IMDb ratings change slowly. Running with `--skip-streaming` weekly is usually sufficient.

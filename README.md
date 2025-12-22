# Movie Showtimes Console Display (SerpAPI)

A console-based display board for movie showtimes using SerpAPI search results. Currently console only, it cycles through a list of theaters you provide and shows current movie showtimes.

## Features

- Uses SerpAPI search for showtimes at specific theaters
- Cycles through a list of theaters you specify in config
- Displays all movie showtimes returned for today's date
- Shows theater name, address (when provided), and showtimes
- Displays movie ratings and formats when present
- Auto-refresh cycles through movies; API calls occur at most once per day via a cache file

## Prerequisites

1. **Get a SerpAPI key**
  - Sign up at https://serpapi.com/
  - Copy your `api_key`

2. **Create a config file**
  ```json
  {
    "api_key": "YOUR_SERPAPI_KEY",
    "refresh": 10,
    "hl": "en",
    "gl": "us",
    "cache_file": "showtimes_cache.json",
    "theaters": [
      {"name": "AMC The Grove 14", "location": "Los Angeles, California, United States"},
      {"name": "Alamo Drafthouse Downtown", "location": "Los Angeles, California, United States"}
    ]
  }
  ```

3. **Install Dependencies**
  - Uses only Python stdlib (`urllib`, `json`), so nothing to install.

## Usage

### Basic Usage

```bash
python movie_showtimes_console.py --config ./showtimes_config.json
```

### With All Options

```bash
python movie_showtimes_console.py \
  --config ./showtimes_config.json \
  --refresh 15
```

### Command Line Arguments

- `--config` (required): Path to JSON config with `api_key` and `theaters`
- `--refresh` (optional): Seconds to display each theater (overrides config)
- `--cache-file` (optional): Path to cache JSON (overrides config `cache_file`, default `showtimes_cache.json`)

## How It Works

1. **Daily fetch**: On first run each day, fetch showtimes for all theaters, then write them to a cache file with the current date.
2. **Reuse cache**: If the cache date is today, reuse cached data (no API calls).
3. **Midnight roll-over**: While running, if the UTC date changes, the app automatically refreshes data, rewrites the cache, and rebuilds the movie list.
4. **Display**: Cycles through movies one-by-one; each `refresh` interval advances to the next movie.
5. **Loop**: Continues cycling through the cached movies using the configured refresh interval.

## Example Output

```
====================================================================================================
MOVIE SHOWTIMES @ 2025-12-22 14:30:15
====================================================================================================
Theater query: AMC The Grove 14
Location: Los Angeles, California, United States
====================================================================================================
MOVIE                                           RATING   TIMES
----------------------------------------------------------------------------------------------------
Wonka                                          PG-13   2:45pm
                                                       5:15pm (IMAX)
                                                       8:10pm
The Boy and the Heron                          PG      3:00pm
                                                       6:00pm
                                                       9:05pm
----------------------------------------------------------------------------------------------------
Total showtime entries: 8
====================================================================================================
```

## Troubleshooting

### HTTP 401 / 403
- Verify your SerpAPI `api_key`
- Make sure your plan has remaining credits

### HTTP 429 / Rate Limits
- Increase the `refresh` interval
- Reduce the number of theaters in the config

### Empty showtimes
- Confirm the theater name and location match Google results
- Try a more specific theater name
- Ensure `hl` and `gl` match your region

## Next Steps

Future enhancements:
- Add LED matrix display support (similar to LA Metro display)
- Filter movies by genre or rating
- Show movie runtime and synopsis
- Add booking links and QR codes
- Support for tomorrow's showtimes
- Add film poster images

## License

Same license as the parent LA Metro Display project.

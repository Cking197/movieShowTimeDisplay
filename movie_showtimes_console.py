import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python <3.9 fallback
    ZoneInfo = None

# Console script to fetch movie showtimes using SerpAPI search results
SERP_ENDPOINT = "https://serpapi.com/search.json"
DEFAULT_REFRESH = 10  # seconds per theater
DEFAULT_CACHE_FILE = "showtimes_cache.json"
DEFAULT_CONGIG_FILE = "showtimes_config.json"


def load_config(path: str =DEFAULT_CONGIG_FILE) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if "api_key" not in data:
        raise ValueError("Config missing 'api_key'")
    if "theaters" not in data or not isinstance(data["theaters"], list):
        raise ValueError("Config missing 'theaters' list")
    return data


def fetch_showtimes(api_key: str, theater: str, location: str, hl: str, gl: str) -> Dict[str, Any]:
    params = {
        "q": theater,
        "location": location,
        "hl": hl,
        "gl": gl,
        "api_key": api_key,
    }
    url = f"{SERP_ENDPOINT}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "MovieShowtimes-Console/1.1"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="ignore") if hasattr(e, "read") else ""
        raise RuntimeError(f"HTTP {e.code}: {detail}")


def normalize_showtimes(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    theaters = payload.get("showtimes") or []
    normalized: List[Dict[str, Any]] = []
    
    # Only take first theater entry (today's showtimes), ignore future days
    if theaters and len(theaters) > 0:
        theaters = [theaters[0]]
    
    for entry in theaters:
        theater_name = entry.get("theater_name") or entry.get("name") or "Unknown Theater"
        address = entry.get("address") or entry.get("address_line") or entry.get("full_address") or ""
        movies = entry.get("movies") or entry.get("showing") or []
        
        # Only process first entry (today's movies), skip future days
        if isinstance(movies, list) and len(movies) > 0 and isinstance(movies[0], list):
            movies = movies[0]

        movie_rows = []
        for movie in movies:
            title = movie.get("title") or movie.get("name") or movie.get("film_name") or "(title unknown)"

            time_blocks = movie.get("showtimes") or movie.get("times") or movie.get("showing") or []
            times: List[str] = []
            for tb in time_blocks:
                if isinstance(tb, dict):
                    t_val = tb.get("time") or tb.get("start_time") or tb.get("start") or ""
                    t_type = tb.get("type") or tb.get("format") or tb.get("ticket_type")
                    if t_val:
                        times.append(f"{t_val} ({t_type})" if t_type else t_val)
                elif isinstance(tb, str):
                    times.append(tb)

            movie_rows.append({
                "title": title,
                "times": times[:8],  # keep display manageable
            })

        normalized.append({
            "theater": theater_name,
            "address": address,
            "movies": movie_rows,
        })
    return normalized


def format_showtime_display(theater_label: str, location_label: str, showtimes: List[Dict[str, Any]], tz=None):
    # Clear screen (platform independent)
    print("\033[2J\033[H", end="")

    print("\n" + "=" * 100)
    now_time = now_in_tz(tz)
    print(f"MOVIE SHOWTIMES @ {now_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 100)
    print(f"Theater query: {theater_label}")
    print(f"Location: {location_label}")
    print("=" * 100)
    print(f"{'MOVIE':<60} TIMES")
    print("-" * 100)

    if not showtimes:
        print("No showtimes found")
        return

    total = 0
    for theater in showtimes:
        print(f"{theater['theater']}")
        if theater.get("address"):
            print(f"  {theater['address']}")
        for movie in theater.get("movies", []):
            title = movie["title"][:59]
            times = movie.get("times") or []
            if not times:
                print(f"{title:<60} (no times)")
                continue
            print(f"{title:<60} {times[0]}")
            for extra_time in times[1:]:
                print(f"{'':<60} {extra_time}")
            total += len(times)
        print("-" * 100)

    print(f"Total showtime entries: {total}")
    print("=" * 100)


def resolve_timezone(tz_name: Optional[str], tz_offset_hours: Optional[float]):
    if tz_name and ZoneInfo is not None:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    if tz_offset_hours is not None:
        try:
            return timezone(timedelta(hours=float(tz_offset_hours)))
        except Exception:
            pass
    return timezone.utc


def now_in_tz(tz) -> datetime:
    return datetime.now(tz) if tz else datetime.utcnow().replace(tzinfo=timezone.utc)


def flatten_movies(entries: List[Dict[str, Any]], now_str: str, tz=None) -> List[Dict[str, Any]]:
    movies: List[Dict[str, Any]] = []
    for entry in entries:
        theater_label = entry.get("theater_label", "")
        location_label = entry.get("location_label", "")
        for theater in entry.get("showtimes", []):
            # Always use the theater query as the theater display name
            theater_name = theater_label or "Unknown Theater"
            address = theater.get("address") or ""
            for movie in theater.get("movies", []):
                movies.append({
                    "theater_label": theater_label,
                    "location_label": location_label,
                    "theater_name": theater_name,
                    "address": address,
                    "title": movie.get("title") or "(title unknown)",
                    "times": movie.get("times") or [],
                    "now_str": now_str,
                    "tz": tz,
                })
    return movies


def format_single_movie_display(item: Dict[str, Any]):
    # Clear screen (platform independent)
    print("\033[2J\033[H", end="")

    print("\n" + "=" * 100)
    tz = item.get("tz")
    now_time = now_in_tz(tz)
    print(f"MOVIE SHOWTIMES @ {now_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 100)
    print(f"Location: {item.get('location_label', '')}")
    theater_display = item.get("theater_label") or item.get("theater_name") or ""
    print(f"Theater: {theater_display}")
    if item.get("address"):
        print(f"Address: {item.get('address')}")
    print("=" * 100)

    title = (item.get("title") or "(title unknown)")[:60]
    times = item.get("times") or []

    print(f"{title}")
    if times:
        print("Times:")
        for t in times:
            print(f"  - {t}")
    else:
        print("Times: (none listed)")

    print("=" * 100)


def load_cached(path: str) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None
    except Exception:
        return None


def save_cached(path: str, date_str: str, entries: List[Dict[str, Any]]) -> None:
    if not path:
        return
    payload = {"date": date_str, "entries": entries}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def fetch_all(api_key: str, hl: str, gl: str, theaters: List[Dict[str, Any]]):
    entries = []
    for entry in theaters:
        theater_name = entry.get("name") or entry.get("theater") or entry.get("query")
        location = entry.get("location") or ""
        if not theater_name or not location:
            print("Skipping malformed theater entry (needs 'name' and 'location')")
            continue

        raw = fetch_showtimes(api_key, theater_name, location, hl, gl)
        if raw.get("error"):
            raise RuntimeError(raw.get("error"))
        normalized = normalize_showtimes(raw)
        entries.append({
            "theater_label": theater_name,
            "location_label": location,
            "showtimes": normalized,
        })
    return entries


def run_display(config_path: str, refresh: Optional[int], cache_file: Optional[str]):
    config = load_config(config_path)
    api_key = config["api_key"]
    hl = config.get("hl", "en")
    gl = config.get("gl", "us")
    theaters = config["theaters"]
    cycle_delay = refresh or config.get("refresh") or DEFAULT_REFRESH
    cache_path = cache_file or config.get("cache_file") or DEFAULT_CACHE_FILE
    tz = resolve_timezone(config.get("timezone"), config.get("timezone_offset"))

    def load_entries_for_today() -> Tuple[List[Dict[str, Any]], str]:
        today_str = now_in_tz(tz).strftime("%Y-%m-%d")
        cached_local = load_cached(cache_path)
        if cached_local and cached_local.get("date") == today_str:
            return cached_local.get("entries") or [], cached_local.get("date", today_str)
        fresh = fetch_all(api_key, hl, gl, theaters)
        save_cached(cache_path, today_str, fresh)
        return fresh, today_str

    def group_movies_by_theater(entries: List[Dict[str, Any]], now_str: str) -> List[List[Dict[str, Any]]]:
        """Group movies by theater, maintaining theater order"""
        theater_groups = []
        for entry in entries:
            theater_label = entry.get("theater_label", "")
            location_label = entry.get("location_label", "")
            theater_movies = []
            for theater in entry.get("showtimes", []):
                theater_name = theater_label or "Unknown Theater"
                address = theater.get("address") or ""
                for movie in theater.get("movies", []):
                    theater_movies.append({
                        "theater_label": theater_label,
                        "location_label": location_label,
                        "theater_name": theater_name,
                        "address": address,
                        "title": movie.get("title") or "(title unknown)",
                        "times": movie.get("times") or [],
                        "now_str": now_str,
                        "tz": tz,
                    })
            if theater_movies:
                theater_groups.append(theater_movies)
        return theater_groups

    entries, cache_date = load_entries_for_today()
    theater_groups = group_movies_by_theater(entries, cache_date)
    if not theater_groups:
        print("No movies found to display. Check your config or cache.")
        return

    theater_idx = 0
    movie_idx = 0
    while True:
        # If the date rolls over while running, refresh data and movies
        current_date = now_in_tz(tz).strftime("%Y-%m-%d")
        cached = load_cached(cache_path)
        if not cached or cached.get("date") != current_date:
            try:
                entries, cache_date = load_entries_for_today()
                theater_groups = group_movies_by_theater(entries, cache_date)
                theater_idx = 0
                movie_idx = 0
            except Exception as e:
                print(f"\nError refreshing daily data: {e}")
                time.sleep(5)
                continue
            if not theater_groups:
                print("No movies found after refresh. Retrying in 5 seconds...")
                time.sleep(5)
                continue

        # Get current theater's movies
        theater_idx_normalized = theater_idx % len(theater_groups)
        current_theater = theater_groups[theater_idx_normalized]
        movie_idx_normalized = movie_idx % len(current_theater)
        item = current_theater[movie_idx_normalized]
        
        try:
            format_single_movie_display(item)
            time.sleep(cycle_delay)
            movie_idx += 1
            
            # Move to next theater when we've shown all movies in current theater
            if movie_idx >= len(current_theater):
                movie_idx = 0
                theater_idx += 1
        except Exception as e:
            print(f"\nError displaying movie: {e}")
            time.sleep(5)


def main():
    parser = argparse.ArgumentParser(
        description="Movie Showtimes Console Display via SerpAPI"
    )
    parser.add_argument(
        "--config",
        default="showtimes_config.json",
        help="Path to JSON config with api_key and theaters list (default: showtimes_config.json)",
    )
    parser.add_argument("--refresh", type=int, help="Seconds to display each theater (overrides config)")
    parser.add_argument("--cache-file", help="Path to cache JSON (defaults to showtimes_cache.json or config cache_file)")

    args = parser.parse_args()

    try:
        config_path = args.config or "showtimes_config.json"
        run_display(config_path, args.refresh, args.cache_file)
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    except Exception as e:
        print(f"\nFatal error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())

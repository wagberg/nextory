# Nextory Python API Client

Async Python client for the Nextory audiobook streaming service.

## Features

- **Authentication**: Two-tier auth (login token + profile token) with auto-refresh
- **Library**: Browse ongoing, want_to_read, completed, and custom lists
- **Streaming**: HLS audio package access for audiobook playback
- **Progress**: Read/update playback positions, bookmarks, usage reporting
- **Discovery**: Search, categories, recommendations, home entries
- **Profiles**: List and select user profiles

## Installation

```bash
pip install git+https://github.com/wagberg/nextory.git
```

Or for development:

```bash
git clone https://github.com/wagberg/nextory.git
cd nextory
uv sync
```

## Quick Start

### 1. Select and Save Profile

```bash
uv run nextory-select-profile
```

This authenticates and saves your profile to `~/.config/nextory/profile.yaml`.

### 2. Use the Client

```python
import asyncio
from nextory import NextoryClient
from nextory.config import ProfileConfig

async def main():
    config = ProfileConfig.load()

    async with NextoryClient(
        login_token=config.login_token,
        login_key=config.login_key,
        profile_token=config.profile_token,
        country="SE",
    ) as client:
        # Browse library
        libs = await client.get_libraries()
        books = await client.get_library("ongoing", libs.lists[0].id)

        for book in books.products:
            print(f"{book.title} by {', '.join(a.name for a in book.authors)}")

        # Search
        results = await client.search_books("Harry Potter", per=5)

        # Get audio package for streaming
        audio = await client.get_audio_package(format_id)

        # Reading position
        pos = await client.get_position(format_id)
        await client.patch_position(format_id, percentage=50.0, elapsed_time=3600)

asyncio.run(main())
```

## Key Methods

### Authentication
- `login(username, password)` → login_token
- `select_profile(login_key)` → profile_token
- `get_profiles()` → list of profiles

### Library
- `get_libraries()` → all lists (ongoing, want_to_read, completed, custom)
- `get_library(list_type, list_id, page, per)` → products in a list
- `add_to_library(product_id, list_id)` / `remove_from_library(product_id, list_id)`
- `mark_completed(product_id)` / `unmark_completed(product_id)`

### Discovery
- `search_books(phrase, page, per)` → search results
- `get_categories(content_type)` → browse categories
- `get_home_entries(page, per)` → personalized home screen
- `get_home_entry_products(entry_id, page, per)` → products for a home entry
- `get_recommendations(product_id)` → similar books
- `get_products_by_path(path, id, page, per)` → generic product browse

### Playback
- `get_audio_package(format_id)` → HLS audio files and metadata
- `get_position(format_id)` → current reading position
- `patch_position(format_id, percentage, elapsed_time)` → update position
- `get_bookmarks(format_id)` / `create_bookmark(...)` / `delete_bookmark(...)`
- `report_usage(profile_id, format_id, usage_blocks)` → analytics

### Account
- `get_account()` → account details including country
- `get_subscription()` → subscription info

## Development

```bash
uv sync                      # Install dependencies
uv run ruff check src/       # Lint
uv run ruff format src/      # Format
uv run pytest                # Run tests
```

### Project Structure

```
src/nextory/
├── __init__.py        # Package exports
├── client.py          # API client
├── config.py          # Profile configuration
├── exceptions.py      # Error types
├── helpers.py         # Utility functions
├── models.py          # Data models (Mashumaro)
└── cli/
    └── select_profile.py
```

## License

MIT

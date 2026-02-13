# Nextory Python API Client

Python API client for Nextory audiobook service with support for authentication, profile management, audiobook library access, audio streaming, and progress syncing.

## Features

- **Authentication**: Username/password authentication with two-tier auth (DeviceAuth + ProfileAuth)
- **Profile Management**: List, select, and save profile configurations
- **Library Access**: Fetch audiobooks from want_to_read, reading, and completed lists
- **Audio Streaming**: Direct URL access and chunk streaming for HLS audio files
- **Progress Syncing**: Read and update playback positions, report usage analytics
- **Async/Await**: Built with aiohttp for async operations
- **Music Assistant Ready**: Designed for future Music Assistant integration

## Installation

Using `uv` (recommended):

```bash
# Install uv if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install the package in development mode
uv pip install -e .
```

Using pip:

```bash
pip install -e .
```

## Quick Start

### 1. Select and Save Profile

First, run the profile selection tool to authenticate and save your profile configuration:

```bash
# Interactive mode
nextory-select-profile

# Or with command-line arguments
nextory-select-profile --username your@email.com --password yourpassword --profile-name "Main"
```

This saves your profile configuration to `~/.config/nextory/profile.json`.

### 2. Use the Client

```python
import asyncio
from nextory import NextoryClient, ProfileConfig

async def main():
    # Load saved profile
    config = ProfileConfig.load()
    
    # Create client
    async with NextoryClient() as client:
        # Authenticate
        await client.authenticate(username, password, config.login_key)
        
        # List audiobooks
        audiobooks = await client.get_library_audiobooks("want_to_read")
        
        # Get audio package
        audio_package = await client.get_audio_package(format_id)
        
        # Get audio URLs
        from nextory.streaming import get_audio_urls
        urls = get_audio_urls(audio_package)
        
        # Stream audio chunks
        from nextory.streaming import stream_audio_chunks
        async for chunk in stream_audio_chunks(client._get_session(), urls[0]):
            # Process audio chunk
            pass
        
        # Get reading position
        position = await client.get_reading_position(format_id)
        
        # Update reading position
        await client.update_reading_position(
            profile_id=config.profile_id,
            format_id=format_id,
            percentage=50.0,
            elapsed_time=3600
        )

asyncio.run(main())
```

## API Reference

### NextoryClient

Main client class for interacting with Nextory API.

**Methods:**
- `authenticate(username, password, login_key)` - Authenticate with credentials
- `get_library()` - Get user's library lists (product_lists and custom lists)
- `get_library_audiobooks(list_type, page, per)` - Get audiobooks from library
- `get_audiobook(product_id)` - Get single audiobook details
- `get_audio_package(format_id)` - Get audio files for audiobook
- `get_reading_position(format_id)` - Get current playback position
- `update_reading_position(profile_id, format_id, percentage, elapsed_time)` - Update position
- `report_usage(profile_id, format_id, usage_blocks)` - Report usage analytics

### ProfileConfig

Manage saved profile configurations.

**Methods:**
- `ProfileConfig.load()` - Load saved profile from `~/.config/nextory/profile.json`
- `config.save()` - Save profile configuration

### Streaming Helpers

**Functions:**
- `get_audio_urls(audio_package)` - Extract direct URLs from audio package
- `stream_audio_chunks(session, url, chunk_size)` - Async generator for audio streaming

## Development

### Setup

```bash
# Install with dev dependencies
uv sync

# Format code
uv run ruff format src/

# Check code
uv run ruff check src/

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=nextory --cov-report=term-missing
```

### Running Tests

The project includes comprehensive test coverage:

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_models.py

# Run specific test
uv run pytest tests/test_models.py::test_profile_serialization
```

### Running the Example

```bash
# Interactive mode (prompts for credentials)
uv run python example.py

# With command-line arguments
uv run python example.py --username your@email.com --password yourpassword

# Short form
uv run python example.py -u your@email.com -p yourpassword
```

### Project Structure

```
src/nextory/
├── __init__.py          # Package exports
├── client.py            # Main API client
├── config.py            # Configuration management
├── middlewares.py       # Middlewares for auth
├── models.py            # Data models (Mashumaro)
└── cli/
    └── select_profile.py  # Profile selection CLI
```

## License

MIT

## Contributing

Contributions welcome! This client is designed to be minimal and focused on core audiobook functionality.

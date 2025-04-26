# Whisper Subtitle Generator

A web application for generating, translating, and editing subtitles from videos/audio using Whisper, with video preview and multilingual support.

## Features

- Local Whisper model (v1.1.10) - no API key required
- Multilingual output support
- In-browser subtitle editor
- Video preview with subtitle overlay
- File sharing service with automatic endpoint adaptation

## Handling File Sharing API Changes

This application uses a robust file sharing service abstraction to handle API endpoint changes:

1. The `services/file_sharing.py` module provides a pluggable interface for file sharing services.
2. The `GofileService` class tries multiple endpoint variations when talking to the Gofile API.
3. If an endpoint fails, it automatically tries alternative endpoints that have been used in previous API versions.
4. Fallback mechanisms are in place for when API responses change format.

This design allows the application to continue working even when:
- API endpoints change paths (e.g., `/getServer` → `/servers`)
- API response formats change
- New authentication requirements are added

## Technical Details

- Built with Flask and Python 3.11
- Uses SQLAlchemy for database interactions
- Bootstrap CSS for styling
- Local Whisper model for speech recognition
- ffmpeg for audio extraction from video files

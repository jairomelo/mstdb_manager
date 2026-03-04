# V1 - DEPRECATED AND REMOVED

## Status: ❌ **REMOVED** (March 2026)

This directory contains the deprecated V1 API that has been removed from the application.

## Reason for Removal
- V1 was the original API version and has been superseded by V2
- Low performance and outdated design compared to V2
- Application moved from Elasticsearch to PostgreSQL, making V1's search endpoints obsolete

## Replacement
V1 functionality has been superseded by:
- **V2**: Performance-optimized API with new features and improved design

## Files in this directory
These files are kept for reference only and are not loaded by the application:
- `resolvers.py` - V1 resolvers (unused)
- `serializers.py` - V1 serializers (unused)
- `views.py` - V1 views (unused)

## Migration
Applications using V1 endpoints must migrate to V2.

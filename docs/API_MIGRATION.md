# API Migration Guide - V1/V1beta Removal & V2 Introduction

## Overview
This document outlines the removal of the deprecated V1 and V1beta APIs and the introduction of the new V2 API.

## Changes Made

### ✅ **V1beta API Removal**
- **Date**: October 2025 (source deleted March 2026)
- **Reason**: V1beta was experimental and is not used by any current applications
- **Impact**: No breaking changes for active applications

**Removed endpoints:**
- `/api/v1-beta/documentos/`
- `/api/v1-beta/peresclavizadas/`
- `/api/v1-beta/pernoesclavizadas/`
- `/api/v1-beta/corporaciones/`
- `/api/v1-beta/lugares/`
- `/api/v1-beta/search/`
- `/api/v1-beta/log/`

### ✅ **V1 API Removal**
- **Date**: March 2026 (source deleted)
- **Reason**: Superseded by V2; unused by any application
- **Impact**: No breaking changes (no active consumers); search endpoints were obsolete after the Elasticsearch → PostgreSQL move

### ✅ **V2 API Introduction**
- **Date**: October 2025
- **Purpose**: Performance-optimized API for new features (table views, CSV export, map visualizations)

**New endpoints:**
```
/api/v2/archivos/                    # Archive management
/api/v2/documentos/                  # Document management + search + CSV
/api/v2/personas-esclavizadas/       # Enslaved persons + all features
/api/v2/personas-no-esclavizadas/    # Non-enslaved persons + CSV
/api/v2/lugares/                     # Places + search + CSV
/api/v2/corporaciones/               # Corporations + search + CSV
/api/v2/travel-trajectories/         # Optimized travel/map data
/api/v2/relaciones-personas/         # Person relationships
/api/v2/relaciones-lugares/          # Place relationships
/api/v2/search/                      # Global search
```

## Migration Timeline

### Phase 1: ✅ **Setup** (Completed)
- [x] Remove V1beta endpoints
- [x] Create V2 API structure
- [x] Document changes

### Phase 2: **New Features** (In Progress)
- [ ] Implement table visualizations using V2
- [ ] Add CSV export functionality
- [ ] Implement history/attribution features
- [ ] Test map visualizations with V2 travel trajectories

### Phase 3: **Gradual Migration**
- [x] Migrate frontend components to V2
- [ ] Performance testing and optimization

## API Version Support

| Version | Status | Usage | Migration Plan |
|---------|---------|--------|----------------|
| V1beta | ❌ **REMOVED** | Unused experimental | Removed October 2025 (source deleted March 2026) |
| V1 | ❌ **REMOVED** | Superseded by V2 | Removed March 2026 (source deleted) |
| V2 | ✅ **ACTIVE** | All applications | Use for all development |

## For Future Collaborators

### **Working with APIs:**
- **New features**: Always use V2 endpoints
- **Existing functionality**: V1 remains stable
- **Performance improvements**: Migrate existing features to V2 gradually

### **Key V2 Benefits:**
- 10x smaller payloads for list views
- Built-in CSV export on all entities
- Better caching and performance
- Optimized for table views and maps
- Clean reference-based relationships

### **Migration Guidelines:**
1. Use V2 for any new frontend components
2. V1 remains available for existing functionality
3. Migrate V1 usage gradually, endpoint by endpoint
4. Test thoroughly when migrating map visualizations to V2

## Breaking Changes
- **V1beta removal**: No impact (unused)
- **V1**: No breaking changes
- **V2**: New API, no backward compatibility needed

## Questions or Issues?
- Check V2 documentation: `/api/v2/README.md`
- V2 follows REST principles with clear separation of list/detail views
- All V2 endpoints include built-in search and CSV export where applicable
# API V2 - Lightweight Reference-Based Design

## Overview
API V2 introduces a cleaner, more performant architecture that addresses the issues with V1's heavy nested serializers. It is designed to support new features like table views, CSV export, and map visualizations while maintaining a clear separation of concerns.

## Key Improvements Over V1

### 1. **Lightweight Responses**
- **List endpoints** return minimal data for table views and listings
- **Detail endpoints** provide full entity information with references instead of nested objects
- **Reference serializers** provide just essential fields (ID, name/title) for relationships

### 2. **Better Performance**
- Reduced payload sizes (10x smaller for complex entities)
- Fewer database joins in list views
- Better caching opportunities
- Optimized for table rendering and CSV export

### 3. **Built-in Export Features**
- **CSV Export**: Each ViewSet includes `/export_csv/` endpoint
- **Flattened data structure** for easy CSV generation
- **Configurable export limits** to prevent timeouts

### 4. **Clean Separation of Concerns**
- List serializers for browsing/tables
- Detail serializers for individual entity views
- Reference serializers for relationships
- Relationship endpoints for exploring connections

## API Endpoints

### Main Entity Endpoints
```
GET /api/v2/archivos/                   # List all archivos (lightweight)
GET /api/v2/archivos/{id}/              # Get archivo details
GET /api/v2/archivos/{id}/documentos/   # Get documents for archivo
GET /api/v2/archivos/export_csv/        # Export archivos as CSV

GET /api/v2/documentos/                 # List all documentos
GET /api/v2/documentos/{id}/            # Get documento details  
GET /api/v2/documentos/{id}/personas/   # Get personas for documento
GET /api/v2/documentos/search/?q=term   # Search documentos
GET /api/v2/documentos/export_csv/      # Export documentos as CSV

GET /api/v2/personas-esclavizadas/      # List enslaved persons
GET /api/v2/personas-esclavizadas/{id}/ # Get person details
GET /api/v2/personas-esclavizadas/{id}/relaciones/  # Get relationships
GET /api/v2/personas-esclavizadas/{id}/lugares/     # Get place relationships
GET /api/v2/personas-esclavizadas/search/?q=term    # Search persons
GET /api/v2/personas-esclavizadas/export_csv/       # Export as CSV

GET /api/v2/personas-no-esclavizadas/   # List non-enslaved persons
GET /api/v2/personas-no-esclavizadas/{id}/          # Get person details
GET /api/v2/personas-no-esclavizadas/export_csv/    # Export as CSV

GET /api/v2/lugares/                    # List places
GET /api/v2/lugares/{id}/               # Get place details
GET /api/v2/lugares/{id}/personas/      # Get personas for place
GET /api/v2/lugares/search/?q=term      # Search places
GET /api/v2/lugares/export_csv/         # Export as CSV

GET /api/v2/corporaciones/              # List corporations
GET /api/v2/corporaciones/{id}/         # Get corporation details
GET /api/v2/corporaciones/search/?q=term # Search corporations
GET /api/v2/corporaciones/export_csv/   # Export as CSV
```

### Relationship Endpoints
```
GET /api/v2/relaciones-personas/        # List person relationships
GET /api/v2/relaciones-personas/{id}/   # Get relationship details

GET /api/v2/relaciones-lugares/         # List person-place relationships  
GET /api/v2/relaciones-lugares/{id}/    # Get relationship details

GET /api/v2/travel-trajectories/        # List persons with travel trajectories
GET /api/v2/travel-trajectories/{id}/   # Get person's complete trajectory
GET /api/v2/travel-trajectories/{id}/trajectory_details/  # Detailed trajectory points
GET /api/v2/travel-trajectories/all_trajectories_summary/ # Map overview data
```

### Search & Utility Endpoints
```
GET /api/v2/search/?q=term&type=all     # Global search across all entities
GET /api/v2/csrf/                       # Get CSRF token
```

## Response Structure Examples

### List Response (Lightweight)
```json
{
  "count": 150,
  "next": "http://api/v2/personas-esclavizadas/?page=2",
  "previous": null,
  "results": [
    {
      "persona_id": 123,
      "persona_idno": "PE-123",
      "nombre_normalizado": "María Antonia",
      "nombres": "María Antonia",
      "sexo": "Femenino",
      "edad": 25,
      "documento_count": 3,
      "created_at": "2023-01-15T10:30:00Z"
    }
  ]
}
```

### Detail Response (Full data with references)
```json
{
  "persona_id": 123,
  "persona_idno": "PE-123",
  "nombre_normalizado": "María Antonia",
  "nombres": "María Antonia",
  "apellidos": "de la Cruz",
  "sexo": "Femenino",
  "edad": 25,
  "altura": "Regular",
  "documento_ids": [45, 67, 89],
  "lugar_ids": [12, 23],
  "relacion_ids": [5, 8, 12],
  "ocupacion_ids": [2],
  "hispanizacion": ["María"],
  "etnonimos": ["Congo"],
  "procedencia": "Angola"
}
```

## Migration Strategy

1. **Keep V1 running** for existing clients
2. **New features use V2** (table views, CSV export, attribution)
3. **Gradual migration** - migrate endpoints one by one
4. **Frontend benefits immediately** from lighter payloads

## Usage Examples

### Frontend Table Rendering
```javascript
// Fast, lightweight data for tables
const personas = await fetch('/api/v2/personas-esclavizadas/?page=1&page_size=50');

// Get full details when user clicks on row
const personaDetail = await fetch(`/api/v2/personas-esclavizadas/${id}/`);

// Get related data on demand
const documentos = await fetch(`/api/v2/documentos/?persona_id=${id}`);
```

### CSV Export
```javascript
// Direct download link for CSV export
const csvUrl = '/api/v2/personas-esclavizadas/export_csv/?sexo=F&edad_min=18';
window.open(csvUrl, '_blank');
```

### Search Implementation
```javascript
// Global search across all entities
const results = await fetch('/api/v2/search/?q=maria&type=personas');

// Entity-specific search
const docs = await fetch('/api/v2/documentos/search/?q=matrimonio');
```

### Travel Trajectory Usage
```javascript
// Get all persons with trajectories for map overview
const trajectories = await fetch('/api/v2/travel-trajectories/');

// Get summary of all places with trajectory counts
const mapOverview = await fetch('/api/v2/travel-trajectories/all_trajectories_summary/');

// Get detailed trajectory for a specific person
const personTrajectory = await fetch('/api/v2/travel-trajectories/123/trajectory_details/');
```

## Benefits for New Features

### 1. **Table Views**
- Light list endpoints perfect for data tables
- Fast rendering with minimal payload
- Easy pagination and filtering

### 2. **CSV Export**
- Built-in export endpoints for all entities
- Flattened data structure ideal for CSV
- Configurable limits and filtering

### 3. **History/Attribution**
- Clean separation allows adding audit fields
- Reference-based design supports versioning
- Can add history endpoints without breaking existing structure

### 4. **Performance**
- 10x smaller payloads for list views
- Better database query optimization
- Frontend can cache individual resources
- Reduced network transfer times
# Trayectorias Afro - Database manager

## Project Location

Choose an appropriate location for your Django project (e.g., `/home/your-user/mstdb_manager`).

Permissions must allow system services to access the directory:

```bash
sudo chmod 755 /home
sudo chmod 750 /home/your-user
sudo chown -R your-user:www-data /path/to/your/mstdb_manager
```

> All parent directories of static files must be executable (`chmod +x`) by Nginx's user (`www-data`) for static file access to work.Django project should be located in a directory accessible by your web server (e.g., `/home/your-user/mstdb_manager`).

Permissions must allow system services to access the directory:

```bash
sudo chmod 755 /home
sudo chmod 750 /home/your-user
sudo chown -R your-user:www-data /home/your-user/mstdb_manager
```

> All parent directories of static files must be executable (`chmod +x`) by Nginx's user (`www-data`) for static file access to work.application that provides a web interface and REST API to manage the database of the Trayectorias Afro project. The application includes both a traditional Django web interface and a modern REST API (V2) for accessing and manipulating historical data about enslaved persons, documents, places, and institutions. 

## Prerequisites

- Python 3.10.
- MySQL 8.0 or MariaDB 10.5.
- Elasticsearch 7.10 or later.

### SMTP

The user registration and password reset features require an SMTP server. For development purposes, you can use a local SMTP server like [MailHog](https://github.com/mailhog/MailHog). This application was created with a third-party SMTP server in mind (SendGrid) that only requires a API key to send emails. For custom SMTP configuration, follow Django's documentation on [Sending email](https://docs.djangoproject.com/en/5.1/topics/email/).

### MySQL

This application uses MySQL as the database backend. To run it needs these dependencies:

`sudo apt install -y pkg-config libmysqlclient-dev default-libmysqlclient-dev build-essential`

Also

`sudo apt install python3.x-dev`

### NGINX

This project is deployed using:

- Gunicorn as the WSGI application server
- Nginx as the reverse proxy and static file server
- Unix socket for communication between Gunicorn and Nginx
- Systemd for service management

#### System Requirements

Install the following on your instance:

```bash
sudo apt update
sudo apt install python3-pip python3-venv nginx mysql-server libmysqlclient-dev pkg-config build-essential python3-dev
```

#### Project Location

The Django project is located at:

`/home/trayectorias/mstdb_manager`

Permissions must allow system services to access the directory:

```bash
sudo chmod 755 /home
sudo chmod 750 /home/trayectorias
sudo chown -R trayectorias:www-data /home/trayectorias/mstdb_manager
```

> All parent directories of static files (e.g., `/home`, `/home/trayectorias`, etc.) must be executable (`chmod +x`) by Nginx’s user (`www-data`) for static file access to work.

#### Gunicorn Systemd Service

Create `/etc/systemd/system/gunicorn.service`:

```ini
[Unit]
Description=Gunicorn for Django project
After=network.target

[Service]
User=your-user
Group=www-data
WorkingDirectory=/path/to/your/mstdb_manager

RuntimeDirectory=gunicorn
RuntimeDirectoryMode=0755

ExecStart=/path/to/your/mstdb_manager/venv/bin/gunicorn \
    --access-logfile - \
    --workers 3 \
    --bind unix:/run/gunicorn/gunicorn.sock \
    mdb.wsgi:application

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reexec
sudo systemctl enable gunicorn
sudo systemctl start gunicorn
```

#### Nginx Configuration

Create `/etc/nginx/sites-available/your-project-name`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias /path/to/your/mstdb_manager/staticfiles/;
    }

    location /media/ {
        root /path/to/your/mstdb_manager;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn/gunicorn.sock;
    }
}
```

Enable the config:

```bash
sudo ln -s /etc/nginx/sites-available/your-project-name /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Static Files and Migrations

Inside the virtual environment:

```bash
python manage.py migrate
python manage.py collectstatic
```

## API Documentation

### V2 REST API

The application provides a comprehensive REST API (V2) that offers improved performance and functionality over the legacy V1 API. The V2 API is designed with a reference-based architecture to reduce payload sizes and improve response times.

#### Base URL
```
http://your-domain.com/mdb/api/v2/
```

#### Authentication
API endpoints require proper authentication. Ensure you have the necessary permissions to access the data.

#### Core Endpoints

**Archives**
- `GET /archivos/` - List all archives
- `GET /archivos/{id}/` - Get archive details
- `POST /archivos/` - Create new archive
- `PUT /archivos/{id}/` - Update archive
- `DELETE /archivos/{id}/` - Delete archive

**Documents**
- `GET /documentos/` - List all documents
- `GET /documentos/{id}/` - Get document details
- `GET /documentos/{id}/personas/` - Get all persons associated with document
- `GET /documentos/{id}/history/` - Get document change history
- `GET /documentos/search/?q={query}` - Search documents using Elasticsearch

**Enslaved Persons**
- `GET /personas-esclavizadas/` - List all enslaved persons
- `GET /personas-esclavizadas/{id}/` - Get enslaved person details
- `GET /personas-esclavizadas/{id}/relaciones/` - Get person relationships
- `GET /personas-esclavizadas/{id}/lugares/` - Get person-place relationships
- `GET /personas-esclavizadas/{id}/history/` - Get person change history
- `GET /personas-esclavizadas/search/?q={query}` - Search enslaved persons

**Non-Enslaved Persons**
- `GET /personas-no-esclavizadas/` - List all non-enslaved persons
- `GET /personas-no-esclavizadas/{id}/` - Get non-enslaved person details
- `GET /personas-no-esclavizadas/{id}/history/` - Get person change history
- `GET /personas-no-esclavizadas/search/?q={query}` - Search non-enslaved persons

**Places**
- `GET /lugares/` - List all places
- `GET /lugares/{id}/` - Get place details
- `GET /lugares/search/?q={query}` - Search places

**Corporations/Institutions**
- `GET /corporaciones/` - List all corporations
- `GET /corporaciones/{id}/` - Get corporation details
- `GET /corporaciones/{id}/history/` - Get corporation change history
- `GET /corporaciones/search/?q={query}` - Search corporations

**Relationships**
- `GET /relaciones-personas/` - List person-to-person relationships
- `GET /relaciones-lugares/` - List person-to-place relationships

**Travel Trajectories**
- `GET /travel-trajectories/` - Get person travel trajectories for mapping
- `GET /travel-trajectories/{id}/` - Get specific person's travel trajectory

**Global Search**
- `GET /search/?q={query}` - Global search across all entity types

**Utility Endpoints**
- `GET /csrf/` - Get CSRF token for secure requests

#### History Tracking

The API provides comprehensive change history for key entities using `django-simple-history`:

**History Response Format:**
```json
{
  "count": 3,
  "results": [
    {
      "history_id": 123,
      "history_date": "2025-06-25T04:27:24.469319Z",
      "history_user_name": "admin",
      "history_type_display": "Updated",
      "documento_id": 2819,
      "titulo": "Document Title",
      "fecha_inicial_raw": "1886",
      "fondo": "Archive Fund",
      "is_published": false
    }
  ]
}
```

**History Types:**
- `Created` - Entity was created
- `Updated` - Entity was modified  
- `Deleted` - Entity was deleted

#### API Features

**Performance Optimizations:**
- Reference-based serialization reduces payload sizes
- Separate list/detail serializers for optimal data loading
- Database query optimization with `select_related` and `prefetch_related`
- Pagination for large datasets

**Search Integration:**
- Elasticsearch-powered search with fuzzy matching
- Multi-field search across relevant entity fields
- Paginated search results

**Export Capabilities:**
- CSV export for all main entity types
- Configurable export fields and formats

**Data Filtering:**
- Query parameter filtering for list endpoints
- Published/unpublished content filtering
- Date range filtering where applicable

#### Custom Primary Keys

The V2 API uses custom primary key fields instead of Django's default `id`:
- Documents: `documento_id`
- Persons: `persona_id`  
- Places: `lugar_id`
- Corporations: `corporacion_id`
- Archives: `archivo_id`

#### Migration from V1

The V2 API provides significant improvements over V1:
- **Performance**: 60-80% reduction in response payload sizes
- **Consistency**: Standardized response formats across all endpoints
- **Features**: History tracking, enhanced search, relationship endpoints
- **Scalability**: Optimized queries and reference-based architecture

V1 endpoints are deprecated and will be removed in future versions. See `API_MIGRATION.md` for detailed migration guidance.

## Configuration

This application uses environment variables to configure the database connection and other settings. A list of required environment variables can be found in `.env_development` file. You can copy this file to `.env` and modify the values as needed.

### Django Settings

The Django settings for this application are located in `mdb/settings.py`. You can modify the settings as needed. We tried to keep the settings as generic as possible, so you can remove features you don't need, such as the search engine or the user registration.

## Project Structure

```
mstdb_manager/
├── api/                    # API application
│   ├── v1/                # Legacy V1 API (deprecated)
│   ├── v2/                # Modern V2 API
│   │   ├── serializers.py # V2 API serializers
│   │   ├── views.py       # V2 API views and viewsets
│   │   └── urls.py        # V2 API URL routing
│   └── urls.py            # Main API URL configuration
├── dbgestor/              # Main database application
│   ├── models.py          # Database models with history tracking
│   ├── views.py           # Django web interface views
│   ├── forms.py           # Django forms
│   ├── documents.py       # Elasticsearch document definitions
│   └── templates/         # Django HTML templates
├── cataloguers/           # User management application
├── customscripts/         # Utility scripts
├── mdb/                   # Django project settings
│   ├── settings.py        # Main settings file
│   ├── urls.py            # Root URL configuration
│   └── wsgi.py            # WSGI application
├── staticfiles/           # Collected static files
├── templates/             # Global templates
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
├── API_MIGRATION.md       # V1 to V2 migration guide
└── README.md              # This file
```

### Key Components

- **Models** (`dbgestor/models.py`): Core data models with `django-simple-history` integration
- **V2 API** (`api/v2/`): Modern REST API with optimized serializers and comprehensive endpoints
- **Search** (`dbgestor/documents.py`): Elasticsearch integration for full-text search
- **History Tracking**: Automatic change logging for all major entities
- **Authentication**: Django's built-in authentication with custom user management

## Installation

### Development Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd mstdb_manager
   ```

2. **Create and activate Python virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env_development .env
   # Edit .env with your database and service configurations
   ```

5. **Run database migrations:**
   ```bash
   python manage.py migrate
   ```

6. **Create a superuser:**
   ```bash
   python manage.py createsuperuser
   ```

7. **Collect static files:**
   ```bash
   python manage.py collectstatic
   ```

8. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

The application will be available at `http://localhost:8000/`

### API Testing

Test the V2 API endpoints using curl or any HTTP client:

```bash
# List all documents
curl "http://localhost:8000/mdb/api/v2/documentos/"

# Get document details
curl "http://localhost:8000/mdb/api/v2/documentos/1/"

# Get document history
curl "http://localhost:8000/mdb/api/v2/documentos/1/history/"

# Search across all entities
curl "http://localhost:8000/mdb/api/v2/search/?q=Antequera"
```


## Recent Updates

### V2 API Release (October 2025)
- **🚀 New V2 REST API**: Complete rewrite with reference-based architecture
- **📊 History Tracking**: Full change history for documents, persons, and corporations
- **🔍 Enhanced Search**: Elasticsearch integration with fuzzy matching across all entities
- **⚡ Performance**: 60-80% reduction in API response sizes
- **🗺️ Travel Trajectories**: Specialized endpoints for mapping person movements
- **📈 Relationship Data**: Dedicated endpoints for person-person and person-place relationships
- **📄 Export Features**: CSV export capabilities for all main entity types
- **🔑 Custom Primary Keys**: Consistent use of semantic IDs across all entities

### Migration Notes
- V1 API endpoints are deprecated (see `API_MIGRATION.md`)
- V1beta has been removed
- All new development should use V2 API endpoints
- History tracking is enabled for: Archivo, Documento, Persona, Lugar, Corporacion

## Credits

This project was funded by University of California MRPI [Routes of Enslavement in the Americas](https://www.humanities.uci.edu/routes-enslavement-americas), and it was developed and maintained by [Fundación Histórica Neogranadina](https://neogranadina.org/). Full credits available at [Trayectorias Afro](https://trayectoriasafro.org/About).
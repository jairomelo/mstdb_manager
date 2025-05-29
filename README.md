# Trayectorias Afro - Database manager

This is a Django application that provides a web interface to manage the database of the Trayectorias Afro project. 

## Prerequisites

- Python 3.10.
- MySQL 8.0 or MariaDB 10.5.
- Elasticsearch 7.10 or later.

### SMTP

The user registration and password reset features require an SMTP server. For development purposes, you can use a local SMTP server like [MailHog](https://github.com/mailhog/MailHog). This application was created with a third-party SMTP server in mind (SendGrid) that only requires a API key to send emails. For custom SMTP configuration, follow Django's documentation on [Sending email](https://docs.djangoproject.com/en/5.1/topics/email/).

### MySQL

This application uses MySQL as the database backend. To run it needs this dependencies:

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

Install the following on your Ubuntu-based Lightsail instance:

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

#### Gunicorn Systemd Service

Create `/etc/systemd/system/gunicorn.service`:

```ini
[Unit]
Description=Gunicorn for Django project
After=network.target

[Service]
User=trayectorias
Group=www-data
WorkingDirectory=/home/trayectorias/mstdb_manager

RuntimeDirectory=gunicorn
RuntimeDirectoryMode=0755

ExecStart=/home/trayectorias/mstdb_manager/.venv/bin/gunicorn \
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

Create `/etc/nginx/sites-available/mstdb_manager`:

```nginx
server {
    listen 80;
    server_name <your-ip-or-domain>;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        root /home/trayectorias/mstdb_manager;
    }

    location /media/ {
        root /home/trayectorias/mstdb_manager;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn/gunicorn.sock;
    }
}
```

Enable the config:

```bash
sudo ln -s /etc/nginx/sites-available/mstdb_manager /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Static Files and Migrations

Inside the virtual environment:

```bash
python manage.py migrate
python manage.py collectstatic
```

## Configuration

This application uses environment variables to configure the database connection and other settings. A list of required environment variables can be found in `.env_development` file. You can copy this file to `.env` and modify the values as needed.

### Django settings

The Django settings for this application are located in `mdb/settings.py`. You can modify the settings as needed. We tried to keep the settings as generic as possible, so you can remove features you don't need, such as the search engine or the user registration.

## Installation

1. Clone the repository.
2. Create a python virtual environment and activate it. 
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```


## Credits

This project was funded by University of California MRPI [Routes of Enslavement in the Americas](https://www.humanities.uci.edu/routes-enslavement-americas), and it was developed and maintained by [Fundación Histórica Neogranadina](https://neogranadina.org/). Full credits available at [Trayectorias Afro](https://trayectoriasafro.org/About).
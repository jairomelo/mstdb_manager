# 🛠️ Deployment Guide: TrayectoriasAfro Infrastructure

This document outlines the deployment process for the TrayectoriasAfro platform, consisting of:

* **Frontend** (SvelteKit) hosted at [https://trayectoriasafro.org](https://trayectoriasafro.org)
* **Backend** (Django REST API) hosted at [https://db.trayectoriasafro.org](https://db.trayectoriasafro.org)
* Hosted on a single AWS Lightsail instance
* Managed with NGINX, PM2, UFW, and Let's Encrypt via Certbot DNS challenge

---

## ⚙️ System Overview

| Component     | Tech Stack                     | Path/Domain                       |
| ------------- | ------------------------------ | --------------------------------- |
| Frontend      | SvelteKit + PM2                | `https://trayectoriasafro.org`    |
| Backend       | Django + Gunicorn              | `https://db.trayectoriasafro.org` |
| Reverse Proxy | NGINX                          | `/etc/nginx/sites-available/`     |
| SSL/TLS       | Let's Encrypt + Cloudflare DNS |                                   |
| Server        | AWS Lightsail (Ubuntu 22.04)   |                                   |
| Firewall      | UFW + Lightsail firewall rules |                                   |

---

## 📦 Directory Structure

```bash
/home/trayectorias/
├── mstdb_theme/           # SvelteKit frontend project
├── mstdb_manager/         # Django backend project
└── staticfiles/           # Collected static files (for Django)
```

---

## 🔐 HTTPS with Let's Encrypt (via Cloudflare DNS)

### DNS Setup

* DNS managed via [Cloudflare](https://dash.cloudflare.com)
* Proxies are **disabled during cert issuance**, and **optionally enabled** afterwards

### Certbot Configuration

* Credentials stored at `/root/.secrets/certbot/cloudflare.ini`
* Issued with:

```bash
sudo certbot certonly \
  --dns-cloudflare \
  --dns-cloudflare-credentials /root/.secrets/certbot/cloudflare.ini \
  --dns-cloudflare-propagation-seconds 60 \
  -d trayectoriasafro.org \
  -d www.trayectoriasafro.org \
  -d db.trayectoriasafro.org
```

### Auto-Renewal Hook

```bash
sudo crontab -e
```

```cron
0 3 * * * certbot renew --quiet --deploy-hook "systemctl reload nginx"
```

---

## 🌐 NGINX Configuration

### `/etc/nginx/sites-available/trayectoriasafro.org`

* Redirects HTTP to HTTPS
* Proxies to SvelteKit app served on port 3000 via PM2

```nginx
server {
    listen 80;
    server_name trayectoriasafro.org www.trayectoriasafro.org;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name trayectoriasafro.org www.trayectoriasafro.org;

    ssl_certificate /etc/letsencrypt/live/trayectoriasafro.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/trayectoriasafro.org/privkey.pem;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_cache_bypass $http_upgrade;
    }
}
```

### `/etc/nginx/sites-available/mstdb_manager` (Django backend)

```nginx
server {
    listen 80;
    server_name db.trayectoriasafro.org;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name db.trayectoriasafro.org;

    ssl_certificate /etc/letsencrypt/live/trayectoriasafro.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/trayectoriasafro.org/privkey.pem;

    location / {
        proxy_pass http://unix:/run/gunicorn/gunicorn.sock;
        include proxy_params;
        proxy_redirect off;
    }

    location /static/ {
        alias /home/trayectorias/mstdb_manager/staticfiles/;
    }

    location /media/ {
        root /home/trayectorias/mstdb_manager;
    }
}
```

---

## 🚀 Frontend Deployment with PM2

### Start SvelteKit App

```bash
cd /home/trayectorias/mstdb_theme
npm install
npm run build
pm2 start build/index.js --name trayectorias-frontend
```

### PM2 Persistence

```bash
pm2 save
pm2 startup
```

---

## 🔥 UFW + Lightsail Firewall Rules

### UFW (Inside the instance)

```bash
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8000  # optional for Django testing
```

### Lightsail Firewall (External)

Ensure these ports are open:

| Port | Protocol | Description |
| ---- | -------- | ----------- |
| 22   | TCP      | SSH access  |
| 80   | TCP      | HTTP        |
| 443  | TCP      | HTTPS       |

---

## 🗕️ Last verified: May 29, 2025

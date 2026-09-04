# 🚀 Production Deployment Guide: Zero API Exposure

This guide explains how to deploy the **NER Landslide Risk Monitoring & Early Warning System** to production live on the internet **without exposing your backend API, documentation, or server ports**.

---

## 🛡️ How "Zero API Exposure" Works

```
[Public Visitor / Mobile Citizen]
               │  (HTTPS Port 443 only)
               ▼
   ┌───────────────────────┐
   │ Cloudflare Proxy (WAF)│  <── Masks real server IP; blocks DDoS & scanners
   └───────────┬───────────┘
               │  (Port 443 SSL)
               ▼
   ┌───────────────────────┐
   │   Nginx Web Gateway   │  <── Rate limiting (15 req/s); security headers
   └─────┬───────────┬─────┘
         │           │
   (Static files) (Loopback proxy /api/ & /media/)
         │           │
         ▼           ▼
     frontend/   http://127.0.0.1:8000
       dist/     FastAPI Backend (PORT 8000 BLOCKED BY FIREWALL)
                 • Swagger UI (/docs) DISABLED
                 • ReDoc (/redoc) DISABLED
                 • OpenAPI Schema (/openapi.json) DISABLED
                 • S3 Keys & DB Secrets held strictly in server-side .env
```

---

## 📋 Method 1: Bare-Metal / Ubuntu VPS (Recommended)

Works on any Linux VPS (AWS EC2, DigitalOcean Droplet, Hetzner, Linode, Hostinger).

### 1. Initial VPS Setup & Firewall Hardening
Connect to your VPS via SSH and lock down the firewall:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx git curl ufw

# Set up strict firewall rules
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
# Explicitly block port 8000 from public internet access
sudo ufw deny 8000
sudo ufw enable
```

### 2. Clone Repository & Setup Backend
```bash
cd /var/www
sudo git clone <YOUR_GIT_REPO_URL> ner-landslide-monitoring
sudo chown -R $USER:$USER /var/www/ner-landslide-monitoring
cd /var/www/ner-landslide-monitoring/backend

# Create virtual environment and install packages
python3 -m venv venv
source venv/bin/activate
pip install -U pip setuptools wheel
pip install -r requirements.txt

# Create production .env
cp ../deployment/.env.production.example .env
nano .env
# Set ENVIRONMENT=production, your ALLOWED_ORIGINS, and real AUTH_SECRET_KEY
```

### 3. Configure Systemd Service (Runs Backend Automatically)
Create the service unit file:
```bash
sudo nano /etc/systemd/system/ner-backend.service
```
Paste the following:
```ini
[Unit]
Description=NER Landslide Monitoring FastAPI Service
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/var/www/ner-landslide-monitoring/backend
Environment="ENVIRONMENT=production"
EnvironmentFile=/var/www/ner-landslide-monitoring/backend/.env
ExecStart=/var/www/ner-landslide-monitoring/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now ner-backend
# Check status:
sudo systemctl status ner-backend
```

### 4. Build the Frontend
```bash
cd /var/www/ner-landslide-monitoring/frontend
# Install Node.js 20 if not already present
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

npm install
npm run build
# Assets will compile into /var/www/ner-landslide-monitoring/frontend/dist/
```

### 5. Configure Nginx Reverse Proxy
```bash
# Copy provided production nginx config
sudo cp /var/www/ner-landslide-monitoring/deployment/nginx.conf /etc/nginx/sites-available/ner-landslide.conf

# Edit domain name
sudo nano /etc/nginx/sites-available/ner-landslide.conf
# Replace YOUR_DOMAIN.COM with your actual domain

# Enable the site
sudo ln -s /etc/nginx/sites-available/ner-landslide.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 6. Install Free SSL Certificate (Certbot)
```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## 🐳 Method 2: 1-Command Docker Compose Deployment

If you prefer containerized deployment:

1. Install Docker and Docker Compose on your server:
   ```bash
   curl -fsSL https://get.docker.com | sh
   sudo usermod -aG docker $USER
   ```
2. In the project directory:
   ```bash
   cd deployment
   cp .env.production.example .env
   nano .env # Set your secrets
   docker compose -f docker-compose.prod.yml up -d --build
   ```
3. **Security Result:**
   * The `backend` container is attached to an internal bridge network with **NO host port binding**.
   * Only the `frontend` container listens on port 80/443.
   * Direct requests to `http://YOUR_SERVER_IP:8000` will be refused by the operating system.

---

## ☁️ Method 3: Cloudflare "Orange Cloud" (Complete Server IP Masking)

To guarantee that no one can find your server's true IP address or scan its open ports:

1. In Cloudflare, add your domain.
2. In the **DNS** settings:
   * Create an `A` record for `@` pointing to your server's IP address.
   * Set **Proxy status** to **Proxied (Orange Cloud)**.
3. In **SSL/TLS**:
   * Set encryption mode to **Full (Strict)**.
4. In **Security &rarr; WAF &rarr; Bots**:
   * Enable **Bot Fight Mode** to automatically block malicious scrapers and endpoint scanners.
5. **Verification:**
   Run `ping yourdomain.com` from any terminal. It will return Cloudflare's Anycast IPs (e.g., `104.21.x.x`), completely shielding your server.

---

## ✅ Production Security Verification Checklist

After deploying, verify these 5 tests:

| Test | How to Verify | Expected Result |
| :--- | :--- | :--- |
| **1. Swagger UI is Hidden** | Visit `https://yourdomain.com/docs` | Returns `404 Not Found` |
| **2. ReDoc is Hidden** | Visit `https://yourdomain.com/redoc` | Returns `404 Not Found` |
| **3. OpenAPI Schema Hidden** | Visit `https://yourdomain.com/openapi.json` | Returns `404 Not Found` |
| **4. Port 8000 Blocked** | Visit `http://your-server-ip:8000` | Connection refused / Timed out |
| **5. Application Works Seamlessly** | Open `https://yourdomain.com` | Map loads, advisories load, all 6 languages work, 2G SMS SOS works |

"""Deploy task handler."""
from __future__ import annotations

import io
import zipfile
from typing import Tuple

SYSTEMD_TEMPLATE = """[Unit]
Description=AIU Deploy Service
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/aiu
ExecStart=/usr/bin/python /opt/aiu/app.py
Restart=always

[Install]
WantedBy=multi-user.target
"""

NGINX_TEMPLATE = """server {
    listen 80;
    server_name example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
"""

SSL_SCRIPT = """#!/bin/bash
certbot certonly --nginx -d example.com --email dev@aiu-core.io --agree-tos --non-interactive
"""


async def generate_archive(order_id: str) -> Tuple[str, bytes]:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("aiu.service", SYSTEMD_TEMPLATE)
        archive.writestr("nginx.conf", NGINX_TEMPLATE)
        archive.writestr("ssl.sh", SSL_SCRIPT)
    buffer.seek(0)
    filename = f"deploy-kit-{order_id}.zip"
    return filename, buffer.getvalue()

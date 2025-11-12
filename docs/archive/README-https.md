## 1. *更新docker-compose.yml*
添加Certbot服务，并为Nginx和Certbot添加证书相关卷。

```yaml
   services:
  # GridBNB 交易机器人服务
  gridbnb-bot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: gridbnb-bot
    restart: always
    env_file:
      - .env
    # 内部端口，不直接暴露给外部
    expose:
      - "58181"
    volumes:
      - ./:/app
      - ./data:/app/data  # 持久化数据目录
    networks:
      - gridbnb-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:58181/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Nginx 反向代理服务
  nginx:
    image: nginx:alpine
    container_name: gridbnb-nginx
    restart: always
    ports:
      - "80:80"  # 外部访问端口，用于HTTP和Certbot验证
      - "443:443"  # HTTPS端口
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/logs:/var/log/nginx
      - ./certbot/conf:/etc/letsencrypt:ro  # 挂载SSL证书到Nginx（只读）
      - ./certbot/www:/var/www/certbot:rw  # Certbot webroot，用于验证
    depends_on:
      - gridbnb-bot
    networks:
      - gridbnb-network
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Certbot服务，用于获取和续期SSL证书
  certbot:
    image: certbot/certbot:latest
    container_name: gridbnb-certbot
    volumes:
      - ./certbot/conf:/etc/letsencrypt:rw  # 证书存储目录
      - ./certbot/www:/var/www/certbot:rw   # webroot目录，用于HTTP-01验证
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew; sleep 12h & wait $${!}; done;'"
    # 注意：entrypoint设置了自动续期循环，每12小时检查一次（Let's Encrypt推荐）

networks:
  gridbnb-network:
    driver: bridge
```


## 2. *更新nginx.conf*
初始Nginx配置只需处理HTTP（80端口），添加Certbot验证路径。

```text
# GridBNB Trading Bot - Nginx 反向代理配置
# 此配置将外部80端口的请求转发到内部的交易机器人Web服务

worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    # 基本设置
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 16M;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # 上游服务器定义
    upstream gridbnb_backend {
        # 在docker-compose网络中，使用服务名作为主机名
        server gridbnb-bot:58181;
        keepalive 32;
    }

    # 主服务器配置
    server {
        listen 80;
        server_name _;  # 接受所有域名，您可以改为具体域名

        # 日志文件
        access_log /var/log/nginx/access.log main;
        error_log /var/log/nginx/error.log;

        # 安全头
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "no-referrer-when-downgrade" always;
        add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

        # Certbot验证路径
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        # 主要代理配置
        location / {
            proxy_pass http://gridbnb_backend;
            proxy_http_version 1.1;
            
            # 代理头设置
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # 缓存设置
            proxy_cache_bypass $http_upgrade;
            
            # 超时设置
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # 静态文件缓存 (如果有)
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            proxy_pass http://gridbnb_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # API 路径优化
        location /api/ {
            proxy_pass http://gridbnb_backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            
            # API 请求不缓存
            add_header Cache-Control "no-cache, no-store, must-revalidate";
        }

        # 健康检查端点
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}

```

## 3. *启动/重启容器并申请证书*

### a. 运行docker compose down停止现有容器（如果已运行）

### b. 运行docker compose up -d启动所有服务（包括Certbot）

### c. 测试证书申请（dry-run模式，避免限额，使用--entrypoint标志）：

```sh
docker compose run --rm --entrypoint certbot certbot certonly --webroot --webroot-path /var/www/certbot --dry-run -d <your_domain.com>
```

预期行为：
它会模拟证书请求，使用Let's Encrypt的staging服务器（不会颁发真实证书）。
如果成功：您会看到关于挑战验证（例如通过webroot的HTTP-01）的输出，然后是“The dry run was successful.”。
过程中可能提示输入邮箱和同意条款（因为这是新证书）。

如果成功，移除--dry-run正式申请：
```sh
docker compose run --rm --entrypoint certbot certbot certonly --webroot --webroot-path /var/www/certbot -d <your_domain.com>
```

如果成功，您就会看到Successfully received certificate.类似的输出

## 4. *修改Nginx配置以启用HTTPS*

### a. 备份原始配置文件

在修改前，先备份当前nginx.conf，以防万一出错可以恢复。

```sh
cp cp ./nginx/nginx.conf ./nginx/nginx.conf.bak
```


### b. 编辑nginx.conf文件

使用文本编辑器（如vim、nano或VS Code）打开 ./nginx/nginx.conf 文件。基于您的原始配置，进行以下修改：

- 保留：worker_processes、events、http基本设置（mime.types、log_format、sendfile等）、upstream定义保持不变。

- 修改HTTP server块：将原来的HTTP server改为只处理Certbot验证和重定向到HTTPS。移除原有的代理配置（location /、/api/ 等），因为这些将移到HTTPS块中。

- 添加HTTPS server块：新建一个server块，监听443 ssl，使用证书路径。将原HTTP的代理配置（location /、/api/ 等）复制到这里。

- 注意：确保server_name为您的域名。如果有多个域名，可以添加更多。

完整的最终nginx.conf内容如下，请参考：

```yaml
# GridBNB Trading Bot - Nginx 反向代理配置
# 此配置将外部80端口的请求转发到内部的交易机器人Web服务

worker_processes auto;
error_log /var/log/nginx/error.log warn;
pid /var/run/nginx.pid;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for"';

    # 基本设置
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 16M;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;

    # 上游服务器定义
    upstream gridbnb_backend {
        # 在docker-compose网络中，使用服务名作为主机名
        server gridbnb-bot:58181;
        keepalive 32;
    }

    # HTTP服务器：重定向到HTTPS，并处理Certbot验证
    server {
        listen 80;
        server_name <your_domain.com>;  # ！！！此处替换为您的域名

        # Certbot验证路径（保留，用于续期）
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }

        # 重定向所有请求到HTTPS
        location / {
            return 301 https://$host$request_uri;
        }
    }

    # HTTPS服务器：启用SSL，反向代理到后端
    server {
        listen 443 ssl;
        server_name <your_domain.com>;  # ！！！此处替换为您的域名

        # SSL证书路径 
        ssl_certificate /etc/letsencrypt/live/<your_domain.com>/fullchain.pem; # ！！！ 此处需要替换您的域名
        ssl_certificate_key /etc/letsencrypt/live/<your_domain.com>/privkey.pem; # ！！！ 此处需要替换您的域名

        # 日志文件
        access_log /var/log/nginx/access.log main;
        error_log /var/log/nginx/error.log;

        # 安全头
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header Referrer-Policy "no-referrer-when-downgrade" always;
        add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;

        # 主要代理配置
        location / {
            proxy_pass http://gridbnb_backend;
            proxy_http_version 1.1;

            # 代理头设置
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # 缓存设置
            proxy_cache_bypass $http_upgrade;

            # 超时设置
            proxy_connect_timeout 60s;
            proxy_send_timeout 60s;
            proxy_read_timeout 60s;
        }

        # 静态文件缓存 (如果有)
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            proxy_pass http://gridbnb_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            expires 1y;
            add_header Cache-Control "public, immutable";
        }

        # API 路径优化
        location /api/ {
            proxy_pass http://gridbnb_backend;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            # API 请求不缓存
            add_header Cache-Control "no-cache, no-store, must-revalidate";
        }

        # 健康检查端点
        location /health {
            access_log off;
            return 200 "healthy\n";
            add_header Content-Type text/plain;
        }
    }
}
```

### c. 验证配置文件语法

保存文件后，检查Nginx配置是否语法正确：
```sh
docker compose exec nginx nginx -t
```

### d. 重启Nginx容器

```sh
docker compose restart nginx
```

### e. 测试https访问


## Docker

### 起動

```bash
docker compose -f docker-compose.dev.yml up --build
```

ブラウザで http://127.0.0.1:8000/ にアクセスします。

### 初回セットアップ（DB 作成）

別ターミナルで以下を実行します。

```bash
docker compose -f docker-compose.dev.yml run --rm web python manage.py migrate
```

### 本番起動（例）

```bash
# 例: 環境変数を用意して起動
cp .env.example .env
docker compose --env-file .env up -d --build
```

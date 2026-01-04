# Yarukoto

HTMX + Django で作ったシンプルな Todo アプリ。

## 開発環境

```bash
# Docker で起動
docker compose -f docker-compose.dev.yml up --build

# 初回のみ DB セットアップ
docker compose -f docker-compose.dev.yml run --rm web uv run manage.py migrate
```

http://127.0.0.1:8000/ にアクセス。

## 本番環境

```bash
cp .env.example .env  # 環境変数を設定
docker compose up -d --build
```

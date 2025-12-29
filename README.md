## Docker

### 起動

```bash
docker compose -f docker-compose.dev.yml up --build
```

ブラウザで http://127.0.0.1:8000/ にアクセスします。

### 初回セットアップ（DB 作成）

別ターミナルで以下を実行します。

```bash
docker compose -f docker-compose.dev.yml run --rm web uv run manage.py migrate
```

### 本番起動（例）

```bash
# 例: 環境変数を用意して起動
cp .env.example .env
docker compose --env-file .env up -d --build
```

`.env` の値に `$` が含まれる場合（Django の `SECRET_KEY` など）、Docker Compose が変数展開して警告や意図しない値になることがあります。
その場合は `.env` 内の `$` を `$$` に置換してください。

起動時に自動で DB マイグレーションを実行します（既定: `DJANGO_AUTO_MIGRATE=1`）。

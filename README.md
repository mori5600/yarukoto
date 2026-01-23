# Yarukoto

HTMX + Django で作ったシンプルな Todo アプリです。

## 主な機能

- ユーザー認証（ログイン/ログアウト/登録）
- Todo の追加/完了/削除
- HTMX による部分更新

## 技術スタック

- Django / HTMX
- Docker Compose
- uv（依存関係管理）

## 開発（Docker）

前提: Docker（`docker compose` が使える環境）

```bash
# 起動
docker compose -f compose.dev.yml up --build

# 初回のみ（またはモデル変更時）
docker compose -f compose.dev.yml run --rm web uv run ./manage.py migrate
```

ブラウザで `http://127.0.0.1:8000/` を開きます。

必要に応じて管理ユーザーを作成します:

```bash
docker compose -f compose.dev.yml run --rm web uv run ./manage.py createsuperuser
```

## 本番（Docker）

`compose.yml` は外部 Postgres を前提にしています（`DATABASE_URL` 必須）。

```bash
cp .env.example .env
# .env を編集（最低限: DJANGO_SECRET_KEY / DATABASE_URL / DJANGO_ALLOWED_HOSTS）
docker compose up -d --build
```

## 設定（環境変数）

- `DJANGO_SECRET_KEY`: 本番では必須
- `DJANGO_ALLOWED_HOSTS`: カンマ区切り（本番では必須）
- `DATABASE_URL`: 本番では必須（例: `postgresql://user:pass@host:5432/dbname?sslmode=require`）
- `SIGNUP_INVITATION_CODE`: 登録を招待コード方式で運用する場合に設定（デフォルトは招待コード方式）
  - オープン登録にする場合は `SIGNUP_VALIDATOR=accounts.validators.NoOpValidator` を設定

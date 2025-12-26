## Docker

### 起動

```bash
docker compose up --build
```

ブラウザで http://127.0.0.1:8000/ にアクセスします。

### 初回セットアップ（DB 作成）

別ターミナルで以下を実行します。

```bash
docker compose run --rm web python manage.py migrate
```

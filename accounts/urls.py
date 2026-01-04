"""accountsアプリケーションのURL設定。

ユーザー認証関連のエンドポイントをビューにマッピングする。

URLパターン:
    - 'signup/': ユーザー登録ページ
"""

from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("signup/", views.signup, name="signup"),
]

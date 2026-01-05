"""infoアプリケーションのURL設定。

Todo機能とは独立した、サイト共通の情報ページ（Docs/Help/Aboutなど）を提供する。

URLパターン:
    - 'docs/': アプリ説明ページ
"""

from django.urls import path

from . import views

app_name = "info"

urlpatterns = [
    path("docs/", views.docs, name="docs"),
]

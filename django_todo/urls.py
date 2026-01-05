"""django_todoプロジェクトのURL設定。

プロジェクトレベルのURLルーティングを定義する。

URLパターン:
    - 'admin/': Django管理サイト
    - 'accounts/': 認証（Django標準）
    - '': Todoアプリケーション
"""

import django.contrib.admin
import django.contrib.auth.views
import django.urls

from .auth_forms import BootstrapAuthenticationForm

urlpatterns = [
    django.urls.path("admin/", django.contrib.admin.site.urls),
    django.urls.path(
        "accounts/login/",
        django.contrib.auth.views.LoginView.as_view(
            template_name="account/login.html",
            authentication_form=BootstrapAuthenticationForm,
        ),
        name="account_login",
    ),
    django.urls.path(
        "accounts/logout/",
        django.contrib.auth.views.LogoutView.as_view(),
        name="account_logout",
    ),
    django.urls.path("accounts/", django.urls.include("accounts.urls")),
    django.urls.path("", django.urls.include("info.urls")),
    django.urls.path("", django.urls.include("todo.urls")),
]

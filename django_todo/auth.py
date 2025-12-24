"""Django認証の型安全な補助関数。

django-stubs では ``request.user`` が ``AbstractBaseUser | AnonymousUser`` になり得る。
このモジュールは @login_required 配下で安全にユーザー ID を扱うための関数を提供する。
"""

from typing import TypeGuard

from django.contrib.auth.models import AbstractBaseUser, AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest


def is_authenticated_user(
    user: AbstractBaseUser | AnonymousUser,
) -> TypeGuard[AbstractBaseUser]:
    """ユーザーが認証済みかつ主キーを持つかを実行時チェックする。

    Args:
        user: チェック対象のユーザー。

    Returns:
        認証済みで主キーが存在する場合True。
    """
    return user.is_authenticated and user.pk is not None


def get_authenticated_user_id(request: HttpRequest) -> int:
    """認証済みユーザーのIDを取得する。

    Args:
        request: HTTPリクエスト。

    Returns:
        認証済みユーザーの主キー。

    Raises:
        PermissionDenied: 未認証、またはユーザーIDが取得できない場合。
    """
    if not is_authenticated_user(request.user):
        raise PermissionDenied("User must be authenticated")

    user_pk = request.user.pk
    if user_pk is None:
        raise PermissionDenied("User must have a primary key")

    return int(user_pk)

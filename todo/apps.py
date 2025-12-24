"""Todoアプリケーションの設定。

Djangoアプリケーションの設定クラスを定義する。
"""

from django.apps import AppConfig


class TodoConfig(AppConfig):
    """Todoアプリケーションの設定クラス。

    Attributes:
        name: アプリケーション名。
    """

    name = "todo"

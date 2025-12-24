"""Todoアプリケーションの管理サイト設定。

Django管理サイトへのモデル登録を行う。
"""

from django.contrib import admin

from .models import TodoItem

admin.site.register(TodoItem)

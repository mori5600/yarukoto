"""TodoアプリケーションのURL設定。

Todoアプリケーションの各エンドポイントをビューにマッピングする。

URLパターン:
    - '': Todoリストのメインページ
    - 'items/': HTMX用のTodoリスト部分更新
    - 'create/': 新規Todoアイテム作成
    - 'update/<item_id>/': Todoアイテムの完了状態更新
    - 'delete/<item_id>/': Todoアイテム削除
"""

from django.urls import path

from . import views

app_name = "todo"

urlpatterns = [
    path("", views.todo_list, name="todo_list"),
    path("items/", views.todo_items, name="todo_items"),
    path("create/", views.create_todo_item, name="create_todo_item"),
    path(
        "update/<int:item_id>/",
        views.update_todo_item,
        name="update_todo_item",
    ),
    path(
        "item/<int:item_id>/",
        views.todo_item_partial,
        name="todo_item_partial",
    ),
    path("edit/<int:item_id>/", views.edit_todo_item, name="edit_todo_item"),
    path(
        "delete/<int:item_id>/",
        views.delete_todo_item,
        name="delete_todo_item",
    ),
    path(
        "delete-all/",
        views.delete_all_todo_items,
        name="delete_all_todo_items",
    ),
    path("docs/", views.docs, name="docs"),
]

"""Todoアプリケーションのビュー。

外部（urls.py / tests）からはこのパッケージを経由して参照する。
"""

from .docs import docs  # noqa: F401
from .todos import (  # noqa: F401
    DEFAULT_PAGE,
    PAGINATION_INFO_ID,
    TODO_FORM_ERRORS_ID,
    TODOS_PER_PAGE,
    create_todo_item,
    delete_all_todo_items,
    delete_todo_item,
    get_paginated_todos,
    parse_page_number,
    render_todo_list_with_pagination_oob,
    todo_items,
    todo_list,
    update_todo_item,
)

"""HTMX固有のレスポンス生成。

OOBスワップ、パーシャルHTML組み立てなど、HTMX専用の処理を提供する。
API化時には使用しない（捨てて良い）レイヤー。
"""

from http import HTTPStatus
from typing import Final

from django.core.paginator import Page
from django.http import HttpResponse
from django.template.loader import render_to_string

from .models import TodoItem
from .params import (
    DEFAULT_PAGE,
    DEFAULT_TODO_FILTER_STATUS,
    DEFAULT_TODO_SORT_KEY,
    TodoFilterStatus,
    TodoSortKey,
    build_todo_list_querystring,
)

# =============================================================================
# DOM ID 定数
# =============================================================================

TODO_LIST_ID: Final[str] = "todo-list"
PAGINATION_INFO_ID: Final[str] = "pagination-info"
TODO_COUNT_ID: Final[str] = "todo-count"
TODO_FORM_ERRORS_ID: Final[str] = "todo-form-errors"


# =============================================================================
# OOB ヘルパー
# =============================================================================


def _add_oob_attribute(html: str, element_id: str, oob_value: str = "true") -> str:
    """HTML断片にOOBスワップ属性を追加する。

    Args:
        html: 対象のHTML文字列。
        element_id: 対象要素のID。
        oob_value: hx-swap-oobの値。

    Returns:
        OOB属性が追加されたHTML。
    """
    return html.replace(
        f'id="{element_id}"',
        f'id="{element_id}" hx-swap-oob="{oob_value}"',
    )


# =============================================================================
# 一覧レスポンス
# =============================================================================


def render_todo_list_with_pagination_oob(
    page_obj: Page[TodoItem],
    *,
    form_error_message: str | None = None,
    query: str = "",
    status_filter: TodoFilterStatus = DEFAULT_TODO_FILTER_STATUS,
    sort_key: TodoSortKey = DEFAULT_TODO_SORT_KEY,
    include_main_list: bool = True,
    include_list_oob: bool = False,
    status: HTTPStatus = HTTPStatus.OK,
    today_completed_count: int = 0,
) -> HttpResponse:
    """TodoリストとページネーションをOOBスワップで返す。

    HTMXのOut-of-Band（OOB）スワップを使用して、Todoリストと
    ページネーション情報の両方を一度に更新できる形式でレンダリングする。

    Args:
        page_obj: ページオブジェクト。Todoアイテムとページネーション情報を含む。
        form_error_message: フォームエラーの表示メッセージ。
        query: 検索クエリ。
        status_filter: フィルタ状態。
        sort_key: 並び替えキー。
        include_main_list: メインレスポンスにリストを含めるか。
        include_list_oob: OOBでリストを更新するか。
        status: 返却するHTTPステータス。
        today_completed_count: 今日の完了件数。

    Returns:
        レンダリングされたHTMLを含むHttpResponse。
    """
    list_querystring = build_todo_list_querystring(
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )
    base_context: dict[str, object] = {
        "page_obj": page_obj,
        "current_page": getattr(page_obj, "number", DEFAULT_PAGE),
        "current_q": query,
        "current_status": status_filter.value,
        "current_sort": sort_key.value,
        "list_querystring": list_querystring,
        "today_completed_count": today_completed_count,
    }

    todo_list_html = ""
    if include_main_list or include_list_oob:
        todo_list_html = render_to_string("todo/_todo_list.html", base_context)

    todo_form_errors_html = render_to_string(
        "todo/_todo_form_errors.html",
        {"message": form_error_message},
    )
    todo_form_errors_with_oob = _add_oob_attribute(todo_form_errors_html, TODO_FORM_ERRORS_ID)

    pagination_info_html = render_to_string("todo/_pagination_info.html", base_context)
    pagination_info_with_oob = _add_oob_attribute(pagination_info_html, PAGINATION_INFO_ID)

    todo_count_html = render_to_string("todo/_todo_count.html", base_context)
    todo_count_with_oob = _add_oob_attribute(todo_count_html, TODO_COUNT_ID)

    parts: list[str] = []
    if include_main_list:
        parts.append(todo_list_html)
    if include_list_oob:
        parts.append(f'<div id="{TODO_LIST_ID}" hx-swap-oob="innerHTML">{todo_list_html}</div>')
    parts.append(todo_form_errors_with_oob)
    parts.append(todo_count_with_oob)
    parts.append(pagination_info_with_oob)

    return HttpResponse("".join(parts), status=status)


# =============================================================================
# 単一アイテムレスポンス
# =============================================================================


def render_todo_item_html(
    todo_item: TodoItem,
    *,
    current_page: int,
    query: str,
    status_filter: str,
    sort_key: str,
    list_querystring: str,
) -> str:
    """単一Todoアイテムの通常表示HTMLを生成する。

    Args:
        todo_item: 対象のTodoItem。
        current_page: 現在のページ番号。
        query: 検索クエリ。
        status_filter: フィルタ状態。
        sort_key: 並び替えキー。
        list_querystring: クエリ文字列。

    Returns:
        レンダリングされたHTML文字列。
    """
    return render_to_string(
        "todo/_todo_item.html",
        {
            "todo_item": todo_item,
            "current_page": current_page,
            "current_q": query,
            "current_status": status_filter,
            "current_sort": sort_key,
            "list_querystring": list_querystring,
        },
    )


def render_todo_item_with_oob(
    todo_item: TodoItem,
    *,
    current_page: int,
    query: str,
    status_filter: str,
    sort_key: str,
    list_querystring: str,
) -> str:
    """単一TodoアイテムのOOB更新用HTMLを生成する。

    Args:
        todo_item: 対象のTodoItem。
        current_page: 現在のページ番号。
        query: 検索クエリ。
        status_filter: フィルタ状態。
        sort_key: 並び替えキー。
        list_querystring: クエリ文字列。

    Returns:
        OOB属性付きのHTML文字列。
    """
    html = render_todo_item_html(
        todo_item,
        current_page=current_page,
        query=query,
        status_filter=status_filter,
        sort_key=sort_key,
        list_querystring=list_querystring,
    )
    return html.replace(
        f'id="todo-item-{todo_item.pk}"',
        f'id="todo-item-{todo_item.pk}" hx-swap-oob="outerHTML"',
    )


# =============================================================================
# フォーカスモードレスポンス
# =============================================================================


def render_focus_item_html(
    todo_item: TodoItem,
    *,
    current_page: int,
    list_querystring: str,
) -> str:
    """フォーカスモード用のTodoアイテムHTMLを生成する。

    Args:
        todo_item: 対象のTodoItem。
        current_page: 現在のページ番号。
        list_querystring: クエリ文字列。

    Returns:
        レンダリングされたHTML文字列。
    """
    return render_to_string(
        "todo/_todo_focus_item.html",
        {
            "todo_item": todo_item,
            "current_page": current_page,
            "list_querystring": list_querystring,
        },
    )


def render_todo_count_oob(
    page_obj: Page[TodoItem],
    *,
    today_completed_count: int,
) -> str:
    """Todo件数表示のOOB更新用HTMLを生成する。

    Args:
        page_obj: ページオブジェクト。
        today_completed_count: 今日の完了件数。

    Returns:
        OOB属性付きのHTML文字列。
    """
    html = render_to_string(
        "todo/_todo_count.html",
        {
            "page_obj": page_obj,
            "today_completed_count": today_completed_count,
        },
    )
    return _add_oob_attribute(html, TODO_COUNT_ID)


def render_focus_mode_delete_oob() -> str:
    """フォーカスモードを閉じるためのOOB HTMLを生成する。

    Returns:
        フォーカスモードを削除するOOB HTML。
    """
    return '<div id="todo-focus-mode" hx-swap-oob="delete"></div>'

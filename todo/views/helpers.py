"""Todoビュー用のヘルパー関数。

HTMXの部分更新やOOBスワップ用のレンダリングなど、ビュー本体から切り出した共通処理を提供する。
"""

import logging
from http import HTTPStatus
from typing import Final, Literal
from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.http import HttpResponse
from django.template.loader import render_to_string

from ..models import TodoItem

logger = logging.getLogger(__name__)

# 定数
DEFAULT_PAGE: Final[int] = 1
TODOS_PER_PAGE: Final[int] = 10
PAGINATION_INFO_ID: Final[str] = "pagination-info"
TODO_FORM_ERRORS_ID: Final[str] = "todo-form-errors"


TodoFilterStatus = Literal["all", "active", "completed"]


def parse_todo_filter_status(raw_status: str | None) -> TodoFilterStatus:
    """Todoのフィルタ状態を正規化する。

    Args:
        raw_status: クエリパラメータ等で受け取ったフィルタ状態。

    Returns:
        正規化されたフィルタ状態。未指定・不正値は "all"。
    """

    if raw_status is None:
        return "all"

    status = raw_status.strip().lower()
    if status in {"all", "active", "completed"}:
        return status  # type: ignore[return-value]
    return "all"


def parse_todo_search_query(raw_query: str | None) -> str:
    """Todo検索クエリを正規化する。

    Args:
        raw_query: クエリパラメータ等で受け取った検索文字列。

    Returns:
        前後空白を除去した検索文字列。未指定は空文字。
    """

    if raw_query is None:
        return ""
    return raw_query.strip()


def build_todo_filter_querystring(*, query: str, status: TodoFilterStatus) -> str:
    """検索/フィルタ用のクエリ文字列を生成する。

    Note:
        page は別途テンプレート側で付与する想定。

    Args:
        query: 検索文字列。
        status: フィルタ状態。

    Returns:
        URLエンコード済みのクエリ文字列。デフォルト状態（query="" かつ status="all"）は空文字。
    """

    params: dict[str, str] = {}

    if query:
        params["q"] = query
    if status != "all":
        params["status"] = status

    if not params:
        return ""
    return urlencode(params)


def parse_page_number(
    raw_page_number: str | int | None, *, default: int = DEFAULT_PAGE
) -> int:
    """ページ番号を安全にintへ正規化する。

    Args:
        raw_page_number: クエリパラメータ等で受け取ったページ番号。
        default: 変換に失敗した場合に使うデフォルト値。

    Returns:
        正規化されたページ番号。
    """
    if raw_page_number is None:
        return default

    try:
        page_number = int(raw_page_number)
    except (TypeError, ValueError):
        return default

    if page_number < 1:
        return default
    return page_number


def get_paginated_todos(
    *,
    user_id: int,
    page_number=DEFAULT_PAGE,
    per_page=TODOS_PER_PAGE,
    query: str = "",
    status: TodoFilterStatus = "all",
):
    """ページネーション済みのTodoリストを取得する。

    データベースからTodoアイテムを作成日時の降順で取得し、
    指定されたページサイズでページネーションを適用する。

    Args:
        user_id: Todoを取得する対象ユーザーID。
        page_number: 取得するページ番号。デフォルトは1。
        per_page: 1ページあたりのアイテム数。デフォルトは10。

    Returns:
        ページオブジェクト。指定されたページのTodoアイテムと
        ページネーション情報を含む。
    """

    todo_items_list = TodoItem.objects.filter(user_id=user_id)
    if status == "active":
        todo_items_list = todo_items_list.filter(completed=False)
    elif status == "completed":
        todo_items_list = todo_items_list.filter(completed=True)

    if query:
        todo_items_list = todo_items_list.filter(description__icontains=query)

    todo_items_list = todo_items_list.order_by("-created_at")
    paginator = Paginator(todo_items_list, per_page)
    return paginator.get_page(page_number)


def render_todo_list_with_pagination_oob(
    page_obj,
    *,
    form_error_message: str | None = None,
    query: str = "",
    status_filter: TodoFilterStatus = "all",
    status: HTTPStatus = HTTPStatus.OK,
) -> HttpResponse:
    """TodoリストとページネーションをOOBスワップで返す。

    HTMXのOut-of-Band（OOB）スワップを使用して、Todoリストと
    ページネーション情報の両方を一度に更新できる形式でレンダリングする。

    Args:
        page_obj: ページオブジェクト。Todoアイテムとページネーション情報を含む。
        form_error_message: フォームエラーの表示メッセージ。
        status: 返却するHTTPステータス。

    Returns:
        レンダリングされたHTMLを含むHttpResponse。
    """

    filter_querystring = build_todo_filter_querystring(
        query=query, status=status_filter
    )
    base_context: dict[str, object] = {
        "page_obj": page_obj,
        "current_page": getattr(page_obj, "number", DEFAULT_PAGE),
        "current_q": query,
        "current_status": status_filter,
        "filter_querystring": filter_querystring,
    }

    todo_list_html = render_to_string("todo/_todo_list.html", base_context)

    todo_form_errors_html = render_to_string(
        "todo/_todo_form_errors.html", {"message": form_error_message}
    )
    todo_form_errors_with_oob = todo_form_errors_html.replace(
        f'id="{TODO_FORM_ERRORS_ID}"',
        f'id="{TODO_FORM_ERRORS_ID}" hx-swap-oob="true"',
    )

    pagination_info_html = render_to_string("todo/_pagination_info.html", base_context)
    pagination_info_with_oob = pagination_info_html.replace(
        f'id="{PAGINATION_INFO_ID}"',
        f'id="{PAGINATION_INFO_ID}" hx-swap-oob="true"',
    )

    return HttpResponse(
        todo_list_html + todo_form_errors_with_oob + pagination_info_with_oob,
        status=status,
    )

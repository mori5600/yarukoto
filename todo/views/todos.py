"""Todo関連のビュー。

HTTPリクエスト処理（認可・バリデーション・DB操作）に加え、
Todo一覧のページング/検索/フィルタなど、一覧表示に必要なロジックを提供する。
"""

import logging
from http import HTTPStatus
from typing import Final, Literal
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string

from django_todo.auth import get_authenticated_user_id
from utils.enums import RequestMethod

from ..forms import TodoItemForm
from ..models import TodoItem

logger = logging.getLogger(__name__)

# 定数
DEFAULT_PAGE: Final[int] = 1
TODOS_PER_PAGE: Final[int] = 10
PAGINATION_INFO_ID: Final[str] = "pagination-info"
TODO_FORM_ERRORS_ID: Final[str] = "todo-form-errors"


type TodoFilterStatus = Literal["all", "active", "completed"]


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


@login_required
def todo_list(request: HttpRequest) -> HttpResponse:
    """Todoリストのメインページを表示する。

    ページネーション済みのTodoリストと新規追加用のフォームを表示する。

    Args:
        request: HTTPリクエストオブジェクト。

    Returns:
        レンダリングされたTodoリストページのHttpResponse。
    """
    user_id = get_authenticated_user_id(request)
    page_number = parse_page_number(request.GET.get("page"), default=DEFAULT_PAGE)
    query = parse_todo_search_query(request.GET.get("q"))
    status_filter = parse_todo_filter_status(request.GET.get("status"))
    page_obj = get_paginated_todos(
        user_id=user_id,
        page_number=page_number,
        query=query,
        status=status_filter,
    )
    form = TodoItemForm()

    filter_querystring = build_todo_filter_querystring(
        query=query, status=status_filter
    )

    return render(
        request,
        "todo/todo_list.html",
        {
            "page_obj": page_obj,
            "form": form,
            "current_page": page_obj.number,
            "current_q": query,
            "current_status": status_filter,
            "filter_querystring": filter_querystring,
        },
    )


@login_required
def todo_items(request: HttpRequest) -> HttpResponse:
    """HTMX用のTodoリスト部分テンプレートを返す。

    ページネーション済みのTodoリストのみを部分的に更新するために使用される。

    Args:
        request: HTTPリクエストオブジェクト。

    Returns:
        レンダリングされたTodoリスト部分テンプレートのHttpResponse。
    """
    user_id = get_authenticated_user_id(request)
    page_number = parse_page_number(request.GET.get("page"), default=DEFAULT_PAGE)
    query = parse_todo_search_query(request.GET.get("q"))
    status_filter = parse_todo_filter_status(request.GET.get("status"))
    page_obj = get_paginated_todos(
        user_id=user_id,
        page_number=page_number,
        query=query,
        status=status_filter,
    )
    filter_querystring = build_todo_filter_querystring(
        query=query, status=status_filter
    )
    return render(
        request,
        "todo/_todo_list.html",
        {
            "page_obj": page_obj,
            "current_page": page_obj.number,
            "current_q": query,
            "current_status": status_filter,
            "filter_querystring": filter_querystring,
        },
    )


@login_required
def create_todo_item(request: HttpRequest) -> HttpResponse:
    """新しいTodoアイテムを作成する。

    POSTリクエストで送信されたフォームデータからTodoアイテムを作成し、
    更新されたリストとページネーション情報を返す。

    Args:
        request: HTTPリクエストオブジェクト。

    Returns:
        作成成功時: 更新されたTodoリストとページネーション情報のHttpResponse。
        バリデーション失敗時: 400 Bad RequestのHttpResponse。
    """
    if request.method != RequestMethod.POST:
        return HttpResponse(status=HTTPStatus.BAD_REQUEST)

    user_id = get_authenticated_user_id(request)
    query = parse_todo_search_query(request.GET.get("q"))
    status_filter = parse_todo_filter_status(request.GET.get("status"))
    max_items = getattr(settings, "TODO_MAX_ITEMS_PER_USER", 1000)
    current_count = TodoItem.objects.filter(user_id=user_id).count()
    if current_count >= max_items:
        logger.info(
            "Todo上限に達しました: user_id=%s, count=%d, max=%d",
            user_id,
            current_count,
            max_items,
        )
        page_obj = get_paginated_todos(
            user_id=user_id,
            page_number=DEFAULT_PAGE,
            query=query,
            status=status_filter,
        )
        return render_todo_list_with_pagination_oob(
            page_obj,
            form_error_message=(
                f"Todoは1ユーザーあたり最大{max_items}件までです。不要なTodoを削除してください。"
            ),
            query=query,
            status_filter=status_filter,
            status=HTTPStatus.CONFLICT,
        )

    form = TodoItemForm(request.POST)
    if form.is_valid():
        todo_item = form.save(commit=False)
        todo_item.user_id = user_id
        todo_item.save()
        logger.info(
            "Todoアイテムを作成しました: user_id=%s, id=%d, description='%s'",
            user_id,
            todo_item.id,
            todo_item.description,
        )
        page_obj = get_paginated_todos(
            user_id=user_id,
            page_number=DEFAULT_PAGE,
            query=query,
            status=status_filter,
        )
        return render_todo_list_with_pagination_oob(
            page_obj,
            query=query,
            status_filter=status_filter,
        )

    logger.warning("Todoアイテムの作成に失敗しました: errors=%s", form.errors.as_json())
    page_obj = get_paginated_todos(
        user_id=user_id,
        page_number=DEFAULT_PAGE,
        query=query,
        status=status_filter,
    )
    message = (
        "Todoを入力してください。"
        if "description" in form.errors
        else "入力内容を確認してください。"
    )
    return render_todo_list_with_pagination_oob(
        page_obj,
        form_error_message=message,
        query=query,
        status_filter=status_filter,
        status=HTTPStatus.BAD_REQUEST,
    )


@login_required
def update_todo_item(request: HttpRequest, item_id: int) -> HttpResponse:
    """Todoアイテムの完了状態を更新する。

    指定されたIDのTodoアイテムの完了状態を反転させる。

    Args:
        request: HTTPリクエストオブジェクト。
        item_id: 更新するTodoアイテムのID。

    Returns:
        更新成功時: 更新されたTodoアイテムの行のHTMLを含むHttpResponse。
        メソッド不正時: 405 Method Not AllowedのHttpResponse。

    Raises:
        Http404: 指定されたIDのTodoアイテムが存在しない場合。
    """
    if request.method != RequestMethod.POST:
        return HttpResponse(status=HTTPStatus.METHOD_NOT_ALLOWED)

    user_id = get_authenticated_user_id(request)
    page_number = parse_page_number(request.GET.get("page"), default=DEFAULT_PAGE)
    query = parse_todo_search_query(request.GET.get("q"))
    status_filter = parse_todo_filter_status(request.GET.get("status"))
    filter_querystring = build_todo_filter_querystring(
        query=query, status=status_filter
    )

    todo_item = get_object_or_404(TodoItem, id=item_id, user_id=user_id)
    old_status = todo_item.completed
    todo_item.completed = not todo_item.completed
    todo_item.save()
    logger.info(
        "Todoアイテムの完了状態を更新しました: user_id=%s, id=%d, completed=%s -> %s",
        getattr(request.user, "id", None),
        item_id,
        old_status,
        todo_item.completed,
    )
    return render(
        request,
        "todo/_todo_item.html",
        {
            "todo_item": todo_item,
            "current_page": page_number,
            "current_q": query,
            "current_status": status_filter,
            "filter_querystring": filter_querystring,
        },
    )


@login_required
def delete_todo_item(request: HttpRequest, item_id: int) -> HttpResponse:
    """Todoアイテムを削除する。

    指定されたIDのTodoアイテムを削除し、更新されたリストと
    ページネーション情報を返す。

    Args:
        request: HTTPリクエストオブジェクト。
        item_id: 削除するTodoアイテムのID。

    Returns:
        削除成功時: 更新されたTodoリストとページネーション情報のHttpResponse。
        メソッド不正時: 405 Method Not AllowedのHttpResponse。

    Raises:
        Http404: 指定されたIDのTodoアイテムが存在しない場合。
    """
    if request.method != RequestMethod.DELETE:
        return HttpResponse(status=HTTPStatus.METHOD_NOT_ALLOWED)

    user_id = get_authenticated_user_id(request)
    todo_item = get_object_or_404(TodoItem, id=item_id, user_id=user_id)
    page_number = parse_page_number(request.GET.get("page"), default=DEFAULT_PAGE)
    query = parse_todo_search_query(request.GET.get("q"))
    status_filter = parse_todo_filter_status(request.GET.get("status"))
    description = todo_item.description
    todo_item.delete()
    logger.info(
        "Todoアイテムを削除しました: user_id=%s, id=%d, description='%s'",
        user_id,
        item_id,
        description,
    )
    page_obj = get_paginated_todos(
        user_id=user_id,
        page_number=page_number,
        query=query,
        status=status_filter,
    )
    return render_todo_list_with_pagination_oob(
        page_obj,
        query=query,
        status_filter=status_filter,
    )


@login_required
def delete_all_todo_items(request: HttpRequest) -> HttpResponse:
    """全てのTodoアイテムを一括削除する。

    データベース内の全てのTodoアイテムを削除し、
    空のリストとページネーション情報を返す。

    Args:
        request: HTTPリクエストオブジェクト。

    Returns:
        削除成功時: 空のTodoリストとページネーション情報のHttpResponse。
        メソッド不正時: 405 Method Not AllowedのHttpResponse。
    """
    if request.method != RequestMethod.DELETE:
        return HttpResponse(status=HTTPStatus.METHOD_NOT_ALLOWED)

    user_id = get_authenticated_user_id(request)
    query = parse_todo_search_query(request.GET.get("q"))
    status_filter = parse_todo_filter_status(request.GET.get("status"))
    queryset = TodoItem.objects.filter(user_id=user_id)
    count = queryset.count()
    queryset.delete()
    logger.info(
        "全てのTodoアイテムを一括削除しました: user_id=%s, 削除件数=%d",
        user_id,
        count,
    )
    page_obj = get_paginated_todos(
        user_id=user_id,
        page_number=DEFAULT_PAGE,
        query=query,
        status=status_filter,
    )
    return render_todo_list_with_pagination_oob(
        page_obj,
        query=query,
        status_filter=status_filter,
    )

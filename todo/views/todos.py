"""Todo関連のビュー。

HTTPリクエスト処理（認可・バリデーション・DB操作）に加え、
Todo一覧のページング/検索/フィルタなど、一覧表示に必要なロジックを提供する。
"""

import logging
from enum import StrEnum
from http import HTTPStatus
from typing import Final
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
DESCRIPTION_MAX_LENGTH: Final[int] = 255
TODO_LIST_ID: Final[str] = "todo-list"
PAGINATION_INFO_ID: Final[str] = "pagination-info"
TODO_COUNT_ID: Final[str] = "todo-count"
TODO_FORM_ERRORS_ID: Final[str] = "todo-form-errors"


class TodoFilterStatus(StrEnum):
    ALL = "all"
    ACTIVE = "active"
    COMPLETED = "completed"


DEFAULT_TODO_FILTER_STATUS: Final[TodoFilterStatus] = TodoFilterStatus.ALL


class TodoSortKey(StrEnum):
    CREATED = "created"
    UPDATED = "updated"
    ACTIVE_FIRST = "active_first"


DEFAULT_TODO_SORT_KEY: Final[TodoSortKey] = TodoSortKey.CREATED


def normalize_todo_sort_key(raw_sort: str | TodoSortKey | None) -> TodoSortKey:
    """Todo一覧の並び替えキーを正規化する。

    Args:
        raw_sort: クエリパラメータ等で受け取った並び替えキー。

    Returns:
        正規化された並び替えキー。未指定・不正値は created。
    """
    if raw_sort is None:
        return DEFAULT_TODO_SORT_KEY
    if isinstance(raw_sort, TodoSortKey):
        return raw_sort

    sort_key = str(raw_sort).strip().lower()
    if not sort_key:
        return DEFAULT_TODO_SORT_KEY

    try:
        return TodoSortKey(sort_key)
    except ValueError:
        return DEFAULT_TODO_SORT_KEY


def parse_todo_sort_key(raw_sort: str | None) -> TodoSortKey:
    """Todo一覧の並び替えキーを正規化する（クエリ文字列専用）。"""
    return normalize_todo_sort_key(raw_sort)


def normalize_todo_filter_status(raw_status: str | TodoFilterStatus | None) -> TodoFilterStatus:
    """Todoのフィルタ状態を正規化する。

    Args:
        raw_status: クエリパラメータ等で受け取ったフィルタ状態。

    Returns:
        正規化されたフィルタ状態。未指定・不正値は all。
    """
    if raw_status is None:
        return DEFAULT_TODO_FILTER_STATUS
    if isinstance(raw_status, TodoFilterStatus):
        return raw_status

    status = str(raw_status).strip().lower()
    if not status:
        return DEFAULT_TODO_FILTER_STATUS

    try:
        return TodoFilterStatus(status)
    except ValueError:
        return DEFAULT_TODO_FILTER_STATUS


def parse_todo_filter_status(raw_status: str | None) -> TodoFilterStatus:
    """Todoのフィルタ状態を正規化する。

    Args:
        raw_status: クエリパラメータ等で受け取ったフィルタ状態。

    Returns:
        正規化されたフィルタ状態。未指定・不正値は "all"。
    """
    return normalize_todo_filter_status(raw_status)


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


def build_todo_list_querystring(
    *,
    query: str,
    status: TodoFilterStatus,
    sort_key: TodoSortKey,
) -> str:
    """Todo一覧（検索/フィルタ/並び替え）用のクエリ文字列を生成する。

    Note:
        page は別途テンプレート側で付与する想定。

    Args:
        query: 検索文字列。
        status: フィルタ状態。

    Returns:
        URLエンコード済みのクエリ文字列。
        デフォルト状態（query="" かつ status="all" かつ sort_key="created"）は空文字。
    """
    params: dict[str, str] = {}

    if query:
        params["q"] = query
    if status != DEFAULT_TODO_FILTER_STATUS:
        params["status"] = status.value
    if sort_key != DEFAULT_TODO_SORT_KEY:
        params["sort"] = sort_key.value

    if not params:
        return ""
    return urlencode(params)


def parse_page_number(raw_page_number: str | int | None, *, default: int = DEFAULT_PAGE) -> int:
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


def is_todo_limit_reached(*, user_id: int, max_items: int) -> bool:
    """指定ユーザーのTodoが上限に達しているかを軽く判定する。

    Note:
        「件数そのもの」ではなく「max_items 件目が存在するか」を見ることで、
        毎回の COUNT(*) を避ける（通常ルートを軽くする）。
        上限到達時のログ等で件数が必要なら、その時だけ count() する。

    Args:
        user_id: 対象ユーザーID。
        max_items: 上限件数。

    Returns:
        上限に達していれば True。
    """
    if max_items <= 0:
        return True

    # OFFSET/LIMIT で 1 行だけ取る（存在すれば max_items 以上ある）
    return TodoItem.objects.filter(user_id=user_id).values("id").order_by("id")[max_items - 1 : max_items].exists()


def get_paginated_todos(
    *,
    user_id: int,
    page_number=DEFAULT_PAGE,
    per_page=TODOS_PER_PAGE,
    query: str = "",
    status: TodoFilterStatus | str = DEFAULT_TODO_FILTER_STATUS,
    sort_key: TodoSortKey | str = DEFAULT_TODO_SORT_KEY,
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
    normalized_status = normalize_todo_filter_status(status)
    normalized_sort_key = normalize_todo_sort_key(sort_key)

    todo_items_list = TodoItem.objects.filter(user_id=user_id)

    if normalized_status == TodoFilterStatus.ACTIVE:
        todo_items_list = todo_items_list.filter(completed=False)
    elif normalized_status == TodoFilterStatus.COMPLETED:
        todo_items_list = todo_items_list.filter(completed=True)

    if query:
        todo_items_list = todo_items_list.filter(description__icontains=query)

    if normalized_sort_key == TodoSortKey.UPDATED:
        todo_items_list = todo_items_list.order_by("-updated_at", "-created_at")
    elif normalized_sort_key == TodoSortKey.ACTIVE_FIRST:
        todo_items_list = todo_items_list.order_by("completed", "-created_at")
    else:
        todo_items_list = todo_items_list.order_by("-created_at")

    paginator = Paginator(todo_items_list, per_page)
    return paginator.get_page(page_number)


def render_todo_list_with_pagination_oob(
    page_obj,
    *,
    form_error_message: str | None = None,
    query: str = "",
    status_filter: TodoFilterStatus = DEFAULT_TODO_FILTER_STATUS,
    sort_key: TodoSortKey = DEFAULT_TODO_SORT_KEY,
    include_main_list: bool = True,
    include_list_oob: bool = False,
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
    }

    todo_list_html = ""
    if include_main_list or include_list_oob:
        todo_list_html = render_to_string("todo/_todo_list.html", base_context)

    todo_form_errors_html = render_to_string("todo/_todo_form_errors.html", {"message": form_error_message})
    todo_form_errors_with_oob = todo_form_errors_html.replace(
        f'id="{TODO_FORM_ERRORS_ID}"',
        f'id="{TODO_FORM_ERRORS_ID}" hx-swap-oob="true"',
    )

    pagination_info_html = render_to_string("todo/_pagination_info.html", base_context)
    pagination_info_with_oob = pagination_info_html.replace(
        f'id="{PAGINATION_INFO_ID}"',
        f'id="{PAGINATION_INFO_ID}" hx-swap-oob="true"',
    )

    todo_count_html = render_to_string("todo/_todo_count.html", base_context)
    todo_count_with_oob = todo_count_html.replace(
        f'id="{TODO_COUNT_ID}"',
        f'id="{TODO_COUNT_ID}" hx-swap-oob="true"',
    )

    parts: list[str] = []
    if include_main_list:
        parts.append(todo_list_html)
    if include_list_oob:
        parts.append(f'<div id="{TODO_LIST_ID}" hx-swap-oob="innerHTML">{todo_list_html}</div>')
    parts.append(todo_form_errors_with_oob)
    parts.append(todo_count_with_oob)
    parts.append(pagination_info_with_oob)

    return HttpResponse("".join(parts), status=status)


@login_required
def todo_item_partial(request: HttpRequest, item_id: int) -> HttpResponse:
    """Todoアイテム単体のパーシャルを返す。

    インライン編集のキャンセル等で、Todoアイテムの表示行へ戻す用途。

    Args:
        request: HTTPリクエストオブジェクト。
        item_id: 対象のTodoアイテムID。

    Returns:
        レンダリングされたTodoアイテムHTMLを含むHttpResponse。
        メソッド不正時: 405 Method Not AllowedのHttpResponse。
    """
    if request.method != RequestMethod.GET:
        return HttpResponse(status=HTTPStatus.METHOD_NOT_ALLOWED)

    user_id = get_authenticated_user_id(request)
    page_number = parse_page_number(request.GET.get("page"), default=DEFAULT_PAGE)
    query = parse_todo_search_query(request.GET.get("q"))
    status_filter = parse_todo_filter_status(request.GET.get("status"))
    sort_key = parse_todo_sort_key(request.GET.get("sort"))
    list_querystring = build_todo_list_querystring(
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )

    todo_item = get_object_or_404(TodoItem, id=item_id, user_id=user_id)
    return render(
        request,
        "todo/_todo_item.html",
        {
            "todo_item": todo_item,
            "current_page": page_number,
            "current_q": query,
            "current_status": status_filter.value,
            "current_sort": sort_key.value,
            "list_querystring": list_querystring,
        },
    )


@login_required
def edit_todo_item(request: HttpRequest, item_id: int) -> HttpResponse:
    """Todoアイテムの説明文をインライン編集する。

    GET: 編集フォーム行（パーシャル）を返す。
    POST: 説明文を更新し、
        - 対象行は通常表示へ戻す（メインスワップ）
        - 必要な場合のみ Todo一覧とページネーション情報をOOBで再描画する（速度優先）

    Args:
        request: HTTPリクエストオブジェクト。
        item_id: 編集するTodoアイテムのID。

    Returns:
        GET: 編集フォームのHTMLを含むHttpResponse。
        POST成功: 対象行 +（必要に応じて）OOB更新を含むHttpResponse。
        バリデーション失敗: 編集フォームのHTMLを含む 400 Bad Request。
        メソッド不正時: 405 Method Not AllowedのHttpResponse。
    """
    if request.method not in {RequestMethod.GET, RequestMethod.POST}:
        return HttpResponse(status=HTTPStatus.METHOD_NOT_ALLOWED)

    user_id = get_authenticated_user_id(request)
    page_number = parse_page_number(request.GET.get("page"), default=DEFAULT_PAGE)
    query = parse_todo_search_query(request.GET.get("q"))
    status_filter = parse_todo_filter_status(request.GET.get("status"))
    sort_key = parse_todo_sort_key(request.GET.get("sort"))
    list_querystring = build_todo_list_querystring(
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )

    todo_item = get_object_or_404(TodoItem, id=item_id, user_id=user_id)

    if request.method == RequestMethod.GET:
        return render(
            request,
            "todo/_todo_item_edit.html",
            {
                "todo_item": todo_item,
                "current_page": page_number,
                "current_q": query,
                "current_status": status_filter.value,
                "current_sort": sort_key.value,
                "list_querystring": list_querystring,
            },
        )

    raw_description = request.POST.get("description", "")
    new_description = raw_description.strip()
    description_field = TodoItem._meta.get_field("description")
    field_max_length = getattr(description_field, "max_length", None)
    max_length = field_max_length if isinstance(field_max_length, int) else DESCRIPTION_MAX_LENGTH

    if not new_description:
        return render(
            request,
            "todo/_todo_item_edit.html",
            {
                "todo_item": todo_item,
                "draft_description": raw_description,
                "error_message": "Todoを入力してください。",
                "current_page": page_number,
                "current_q": query,
                "current_status": status_filter.value,
                "current_sort": sort_key.value,
                "list_querystring": list_querystring,
            },
            status=HTTPStatus.BAD_REQUEST,
        )

    if len(new_description) > max_length:
        return render(
            request,
            "todo/_todo_item_edit.html",
            {
                "todo_item": todo_item,
                "draft_description": raw_description,
                "error_message": f"Todoは最大{max_length}文字までです。",
                "current_page": page_number,
                "current_q": query,
                "current_status": status_filter.value,
                "current_sort": sort_key.value,
                "list_querystring": list_querystring,
            },
            status=HTTPStatus.BAD_REQUEST,
        )

    old_description = todo_item.description
    changed = False
    if new_description != old_description:
        todo_item.description = new_description
        todo_item.save(update_fields=["description", "updated_at"])
        changed = True
        logger.info(
            "Todoアイテムを編集しました: user_id=%s, id=%d, description='%s' -> '%s'",
            getattr(request.user, "id", None),
            item_id,
            old_description,
            new_description,
        )

    item_html = render_to_string(
        "todo/_todo_item.html",
        {
            "todo_item": todo_item,
            "current_page": page_number,
            "current_q": query,
            "current_status": status_filter.value,
            "current_sort": sort_key.value,
            "list_querystring": list_querystring,
        },
    )

    # 速度優先:
    # - 検索中(qあり)は、編集により検索結果から外れる/入る可能性があるので一覧更新する
    # - sort=updated は updated_at で順序が動くので一覧更新する
    # - 変更がなければ何も動かないので一覧更新しない
    needs_list_refresh = changed and (bool(query) or sort_key == TodoSortKey.UPDATED)
    if not needs_list_refresh:
        return HttpResponse(item_html)

    page_obj = get_paginated_todos(
        user_id=user_id,
        page_number=page_number,
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )
    oob_response = render_todo_list_with_pagination_oob(
        page_obj,
        query=query,
        status_filter=status_filter,
        sort_key=sort_key,
        include_main_list=False,
        include_list_oob=True,
    )
    return HttpResponse(
        item_html + oob_response.content.decode("utf-8"),
        status=oob_response.status_code,
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
    sort_key = parse_todo_sort_key(request.GET.get("sort"))
    page_obj = get_paginated_todos(
        user_id=user_id,
        page_number=page_number,
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )
    form = TodoItemForm()

    list_querystring = build_todo_list_querystring(
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )

    return render(
        request,
        "todo/todo_list.html",
        {
            "page_obj": page_obj,
            "form": form,
            "current_page": page_obj.number,
            "current_q": query,
            "current_status": status_filter.value,
            "current_sort": sort_key.value,
            "list_querystring": list_querystring,
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
    sort_key = parse_todo_sort_key(request.GET.get("sort"))
    page_obj = get_paginated_todos(
        user_id=user_id,
        page_number=page_number,
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )

    list_querystring = build_todo_list_querystring(
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )
    return render(
        request,
        "todo/_todo_list.html",
        {
            "page_obj": page_obj,
            "current_page": page_obj.number,
            "current_q": query,
            "current_status": status_filter.value,
            "current_sort": sort_key.value,
            "list_querystring": list_querystring,
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
    sort_key = parse_todo_sort_key(request.GET.get("sort"))
    max_items = getattr(settings, "TODO_MAX_ITEMS_PER_USER", 1000)

    # 速度優先: 通常ルートは count() を避ける
    if is_todo_limit_reached(user_id=user_id, max_items=max_items):
        # 上限到達は稀なので、ログ用にここでだけ count()（必要なら）
        current_count = TodoItem.objects.filter(user_id=user_id).count()
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
            sort_key=sort_key,
        )
        return render_todo_list_with_pagination_oob(
            page_obj,
            form_error_message=(f"Todoは1ユーザーあたり最大{max_items}件までです。不要なTodoを削除してください。"),
            query=query,
            status_filter=status_filter,
            sort_key=sort_key,
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
            sort_key=sort_key,
        )
        return render_todo_list_with_pagination_oob(
            page_obj,
            query=query,
            status_filter=status_filter,
            sort_key=sort_key,
        )

    logger.warning("Todoアイテムの作成に失敗しました: errors=%s", form.errors.as_json())
    page_obj = get_paginated_todos(
        user_id=user_id,
        page_number=DEFAULT_PAGE,
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )
    message = "Todoを入力してください。" if "description" in form.errors else "入力内容を確認してください。"
    return render_todo_list_with_pagination_oob(
        page_obj,
        form_error_message=message,
        query=query,
        status_filter=status_filter,
        sort_key=sort_key,
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
    sort_key = parse_todo_sort_key(request.GET.get("sort"))
    list_querystring = build_todo_list_querystring(
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )

    todo_item = get_object_or_404(TodoItem, id=item_id, user_id=user_id)
    old_status = todo_item.completed
    todo_item.completed = not todo_item.completed
    todo_item.save(update_fields=["completed", "updated_at"])
    logger.info(
        "Todoアイテムの完了状態を更新しました: user_id=%s, id=%d, completed=%s -> %s",
        getattr(request.user, "id", None),
        item_id,
        old_status,
        todo_item.completed,
    )

    # 通常は「行だけ」返して最速にする。
    item_html = render_to_string(
        "todo/_todo_item.html",
        {
            "todo_item": todo_item,
            "current_page": page_number,
            "current_q": query,
            "current_status": status_filter.value,
            "current_sort": sort_key.value,
            "list_querystring": list_querystring,
        },
    )

    # ただし次のケースでは一覧の内容/順序が変わり得るので OOB で一覧も更新する。
    # - status != all: トグルで一覧から消える/出る可能性
    # - sort=active_first: completed が変わると順序が変わる
    # - sort=updated: updated_at が更新され、順序が変わる
    needs_list_refresh = (status_filter != TodoFilterStatus.ALL) or (
        sort_key in {TodoSortKey.ACTIVE_FIRST, TodoSortKey.UPDATED}
    )
    if not needs_list_refresh:
        return HttpResponse(item_html)

    page_obj = get_paginated_todos(
        user_id=user_id,
        page_number=page_number,
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )
    oob_response = render_todo_list_with_pagination_oob(
        page_obj,
        query=query,
        status_filter=status_filter,
        sort_key=sort_key,
        include_main_list=False,
        include_list_oob=True,
    )
    return HttpResponse(
        item_html + oob_response.content.decode("utf-8"),
        status=oob_response.status_code,
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
    sort_key = parse_todo_sort_key(request.GET.get("sort"))
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
        sort_key=sort_key,
    )
    return render_todo_list_with_pagination_oob(
        page_obj,
        query=query,
        status_filter=status_filter,
        sort_key=sort_key,
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
    sort_key = parse_todo_sort_key(request.GET.get("sort"))

    queryset = TodoItem.objects.filter(user_id=user_id)
    deleted_count, _ = queryset.delete()
    logger.info(
        "全てのTodoアイテムを一括削除しました: user_id=%s, 削除件数=%d",
        user_id,
        deleted_count,
    )

    page_obj = get_paginated_todos(
        user_id=user_id,
        page_number=DEFAULT_PAGE,
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )
    return render_todo_list_with_pagination_oob(
        page_obj,
        query=query,
        status_filter=status_filter,
        sort_key=sort_key,
    )

"""Todo関連のビュー（HTTP層）。

HTTPリクエストの受付、パラメータ解析、認証確認を行い、
services/queries を呼び出して htmx_responses でレスポンスを生成する。
ビジネスロジックは含まない。
"""

import logging
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from django_todo.auth import get_authenticated_user_id
from shared.enums import RequestMethod

from . import htmx_responses, queries, services
from .forms import TodoItemForm
from .models import TodoItem
from .params import (
    DEFAULT_PAGE,
    TodoFilterStatus,
    TodoSortKey,
    build_todo_list_querystring,
    parse_page_number,
    parse_todo_filter_status,
    parse_todo_search_query,
    parse_todo_sort_key,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 一覧表示
# =============================================================================


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

    page_obj = queries.get_paginated_todos(
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
    today_completed_count = queries.get_today_completed_count(user_id)

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
            "today_completed_count": today_completed_count,
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

    page_obj = queries.get_paginated_todos(
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


# =============================================================================
# 単一アイテム表示
# =============================================================================


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
    is_focus_mode = request.GET.get("focus") == "1"
    list_querystring = build_todo_list_querystring(
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )

    todo_item = get_object_or_404(TodoItem, id=item_id, user_id=user_id)

    if is_focus_mode:
        return render(
            request,
            "todo/_todo_focus_item.html",
            {
                "todo_item": todo_item,
                "current_page": page_number,
                "list_querystring": list_querystring,
            },
        )

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


# =============================================================================
# 作成
# =============================================================================


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
    max_items: int = getattr(settings, "TODO_MAX_ITEMS_PER_USER", 1000)

    # フォームバリデーション
    form = TodoItemForm(request.POST)
    if not form.is_valid():
        logger.warning("Todoアイテムの作成に失敗しました: errors=%s", form.errors.as_json())
        page_obj = queries.get_paginated_todos(
            user_id=user_id,
            page_number=DEFAULT_PAGE,
            query=query,
            status=status_filter,
            sort_key=sort_key,
        )
        message = "Todoを入力してください。" if "description" in form.errors else "入力内容を確認してください。"
        return htmx_responses.render_todo_list_with_pagination_oob(
            page_obj,
            form_error_message=message,
            query=query,
            status_filter=status_filter,
            sort_key=sort_key,
            status=HTTPStatus.BAD_REQUEST,
            today_completed_count=queries.get_today_completed_count(user_id),
        )

    # 作成実行
    result = services.create_todo(
        user_id=user_id,
        description=form.cleaned_data["description"],
        max_items=max_items,
    )

    if not result.success:
        logger.info(
            "Todo上限に達しました: user_id=%s, count=%d, max=%d",
            user_id,
            queries.get_user_todo_count(user_id),
            max_items,
        )
        page_obj = queries.get_paginated_todos(
            user_id=user_id,
            page_number=DEFAULT_PAGE,
            query=query,
            status=status_filter,
            sort_key=sort_key,
        )
        return htmx_responses.render_todo_list_with_pagination_oob(
            page_obj,
            form_error_message=result.error,
            query=query,
            status_filter=status_filter,
            sort_key=sort_key,
            status=HTTPStatus.CONFLICT,
            today_completed_count=queries.get_today_completed_count(user_id),
        )

    logger.info(
        "Todoアイテムを作成しました: user_id=%s, id=%d, description='%s'",
        user_id,
        result.todo_item.pk if result.todo_item else None,
        result.todo_item.description if result.todo_item else None,
    )
    page_obj = queries.get_paginated_todos(
        user_id=user_id,
        page_number=DEFAULT_PAGE,
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )
    return htmx_responses.render_todo_list_with_pagination_oob(
        page_obj,
        query=query,
        status_filter=status_filter,
        sort_key=sort_key,
        today_completed_count=queries.get_today_completed_count(user_id),
    )


# =============================================================================
# 更新（完了トグル）
# =============================================================================


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
    is_focus_mode = request.GET.get("focus") == "1"
    list_querystring = build_todo_list_querystring(
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )

    todo_item = get_object_or_404(TodoItem, id=item_id, user_id=user_id)
    result = services.toggle_todo_completion(todo_item)

    if result.todo_item is None:
        logger.error(
            "Todoアイテムの完了状態更新に失敗しました（todo_itemがNone）: user_id=%s, id=%d",
            user_id,
            item_id,
        )
        return HttpResponse(status=HTTPStatus.INTERNAL_SERVER_ERROR)

    updated_todo_item = result.todo_item

    logger.info(
        "Todoアイテムの完了状態を更新しました: user_id=%s, id=%d, completed=%s -> %s",
        user_id,
        item_id,
        result.old_status,
        updated_todo_item.completed,
    )

    needs_refresh = services.needs_list_refresh_on_toggle(
        status_filter=status_filter.value,
        sort_key=sort_key.value,
    )

    # フォーカスモード内の更新
    if is_focus_mode:
        return _render_focus_mode_toggle_response(
            todo_item=updated_todo_item,
            user_id=user_id,
            page_number=page_number,
            query=query,
            status_filter=status_filter,
            sort_key=sort_key,
            list_querystring=list_querystring,
            needs_refresh=needs_refresh,
        )

    # 通常モードの更新
    return _render_normal_toggle_response(
        todo_item=updated_todo_item,
        user_id=user_id,
        page_number=page_number,
        query=query,
        status_filter=status_filter,
        sort_key=sort_key,
        list_querystring=list_querystring,
        needs_refresh=needs_refresh,
    )


def _render_focus_mode_toggle_response(
    *,
    todo_item: TodoItem,
    user_id: int,
    page_number: int,
    query: str,
    status_filter: TodoFilterStatus,
    sort_key: TodoSortKey,
    list_querystring: str,
    needs_refresh: bool,
) -> HttpResponse:
    """フォーカスモード内での完了トグル後のレスポンスを生成する。"""
    focus_item_html = htmx_responses.render_focus_item_html(
        todo_item,
        current_page=page_number,
        list_querystring=list_querystring,
    )

    if needs_refresh:
        page_obj = queries.get_paginated_todos(
            user_id=user_id,
            page_number=page_number,
            query=query,
            status=status_filter,
            sort_key=sort_key,
        )
        oob_response = htmx_responses.render_todo_list_with_pagination_oob(
            page_obj,
            query=query,
            status_filter=status_filter,
            sort_key=sort_key,
            include_main_list=False,
            include_list_oob=True,
            today_completed_count=queries.get_today_completed_count(user_id),
        )
        return HttpResponse(focus_item_html + oob_response.content.decode("utf-8"))

    # 一覧更新不要でも、背景の行と件数は更新
    list_item_oob = htmx_responses.render_todo_item_with_oob(
        todo_item,
        current_page=page_number,
        query=query,
        status_filter=status_filter.value,
        sort_key=sort_key.value,
        list_querystring=list_querystring,
    )
    page_obj = queries.get_paginated_todos(
        user_id=user_id,
        page_number=page_number,
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )
    todo_count_oob = htmx_responses.render_todo_count_oob(
        page_obj,
        today_completed_count=queries.get_today_completed_count(user_id),
    )
    return HttpResponse(focus_item_html + list_item_oob + todo_count_oob)


def _render_normal_toggle_response(
    *,
    todo_item: TodoItem,
    user_id: int,
    page_number: int,
    query: str,
    status_filter: TodoFilterStatus,
    sort_key: TodoSortKey,
    list_querystring: str,
    needs_refresh: bool,
) -> HttpResponse:
    """通常モードでの完了トグル後のレスポンスを生成する。"""
    item_html = htmx_responses.render_todo_item_html(
        todo_item,
        current_page=page_number,
        query=query,
        status_filter=status_filter.value,
        sort_key=sort_key.value,
        list_querystring=list_querystring,
    )

    if not needs_refresh:
        # 一覧更新不要でも、今日の進捗バッジはOOBで更新
        page_obj = queries.get_paginated_todos(
            user_id=user_id,
            page_number=page_number,
            query=query,
            status=status_filter,
            sort_key=sort_key,
        )
        todo_count_oob = htmx_responses.render_todo_count_oob(
            page_obj,
            today_completed_count=queries.get_today_completed_count(user_id),
        )
        return HttpResponse(item_html + todo_count_oob)

    page_obj = queries.get_paginated_todos(
        user_id=user_id,
        page_number=page_number,
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )
    oob_response = htmx_responses.render_todo_list_with_pagination_oob(
        page_obj,
        query=query,
        status_filter=status_filter,
        sort_key=sort_key,
        include_main_list=False,
        include_list_oob=True,
        today_completed_count=queries.get_today_completed_count(user_id),
    )
    return HttpResponse(item_html + oob_response.content.decode("utf-8"))


# =============================================================================
# 更新（説明文編集）
# =============================================================================


@login_required
def edit_todo_item(request: HttpRequest, item_id: int) -> HttpResponse:
    """Todoアイテムの説明文をインライン編集する。

    GET: 編集フォーム行（パーシャル）を返す。
    POST: 説明文を更新し、対象行を返す（必要に応じてOOBで一覧も更新）。

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
    is_focus_mode = request.GET.get("focus") == "1"
    list_querystring = build_todo_list_querystring(
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )

    todo_item = get_object_or_404(TodoItem, id=item_id, user_id=user_id)

    # GET: 編集フォームを表示
    if request.method == RequestMethod.GET:
        template = "todo/_todo_focus_item_edit.html" if is_focus_mode else "todo/_todo_item_edit.html"
        return render(
            request,
            template,
            {
                "todo_item": todo_item,
                "current_page": page_number,
                "current_q": query,
                "current_status": status_filter.value,
                "current_sort": sort_key.value,
                "list_querystring": list_querystring,
            },
        )

    # POST: 説明文を更新
    raw_description = request.POST.get("description", "")
    new_description = raw_description.strip()
    result = services.update_todo_description(todo_item, new_description)

    if not result.success:
        template = "todo/_todo_focus_item_edit.html" if is_focus_mode else "todo/_todo_item_edit.html"
        return render(
            request,
            template,
            {
                "todo_item": todo_item,
                "draft_description": raw_description,
                "error_message": result.error,
                "current_page": page_number,
                "current_q": query,
                "current_status": status_filter.value,
                "current_sort": sort_key.value,
                "list_querystring": list_querystring,
            },
            status=HTTPStatus.BAD_REQUEST,
        )

    if result.changed:
        logger.info(
            "Todoアイテムを編集しました: user_id=%s, id=%d",
            user_id,
            item_id,
        )

    updated_todo_item = result.todo_item
    if updated_todo_item is None:
        logger.error(
            "Todoアイテムの編集に失敗しました（todo_itemがNone）: user_id=%s, id=%d",
            user_id,
            item_id,
        )
        return HttpResponse(status=HTTPStatus.INTERNAL_SERVER_ERROR)

    needs_refresh = services.needs_list_refresh_on_edit(
        changed=result.changed,
        query=query,
        sort_key=sort_key.value,
    )

    # フォーカスモード内の編集
    if is_focus_mode:
        return _render_focus_mode_edit_response(
            todo_item=updated_todo_item,
            user_id=user_id,
            page_number=page_number,
            query=query,
            status_filter=status_filter,
            sort_key=sort_key,
            list_querystring=list_querystring,
            needs_refresh=needs_refresh,
        )

    # 通常モードの編集
    return _render_normal_edit_response(
        todo_item=updated_todo_item,
        user_id=user_id,
        page_number=page_number,
        query=query,
        status_filter=status_filter,
        sort_key=sort_key,
        list_querystring=list_querystring,
        needs_refresh=needs_refresh,
    )


def _render_focus_mode_edit_response(
    *,
    todo_item: TodoItem,
    user_id: int,
    page_number: int,
    query: str,
    status_filter: TodoFilterStatus,
    sort_key: TodoSortKey,
    list_querystring: str,
    needs_refresh: bool,
) -> HttpResponse:
    """フォーカスモード内での編集後のレスポンスを生成する。"""
    focus_item_html = htmx_responses.render_focus_item_html(
        todo_item,
        current_page=page_number,
        list_querystring=list_querystring,
    )

    if needs_refresh:
        page_obj = queries.get_paginated_todos(
            user_id=user_id,
            page_number=page_number,
            query=query,
            status=status_filter,
            sort_key=sort_key,
        )
        oob_response = htmx_responses.render_todo_list_with_pagination_oob(
            page_obj,
            query=query,
            status_filter=status_filter,
            sort_key=sort_key,
            include_main_list=False,
            include_list_oob=True,
            today_completed_count=queries.get_today_completed_count(user_id),
        )
        return HttpResponse(focus_item_html + oob_response.content.decode("utf-8"))

    # 背景の一覧アイテムも更新
    list_item_oob = htmx_responses.render_todo_item_with_oob(
        todo_item,
        current_page=page_number,
        query=query,
        status_filter=status_filter.value,
        sort_key=sort_key.value,
        list_querystring=list_querystring,
    )
    return HttpResponse(focus_item_html + list_item_oob)


def _render_normal_edit_response(
    *,
    todo_item: TodoItem,
    user_id: int,
    page_number: int,
    query: str,
    status_filter: TodoFilterStatus,
    sort_key: TodoSortKey,
    list_querystring: str,
    needs_refresh: bool,
) -> HttpResponse:
    """通常モードでの編集後のレスポンスを生成する。"""
    item_html = htmx_responses.render_todo_item_html(
        todo_item,
        current_page=page_number,
        query=query,
        status_filter=status_filter.value,
        sort_key=sort_key.value,
        list_querystring=list_querystring,
    )

    if not needs_refresh:
        return HttpResponse(item_html)

    page_obj = queries.get_paginated_todos(
        user_id=user_id,
        page_number=page_number,
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )
    oob_response = htmx_responses.render_todo_list_with_pagination_oob(
        page_obj,
        query=query,
        status_filter=status_filter,
        sort_key=sort_key,
        include_main_list=False,
        include_list_oob=True,
        today_completed_count=queries.get_today_completed_count(user_id),
    )
    return HttpResponse(item_html + oob_response.content.decode("utf-8"))


# =============================================================================
# 削除
# =============================================================================


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
    page_number = parse_page_number(request.GET.get("page"), default=DEFAULT_PAGE)
    query = parse_todo_search_query(request.GET.get("q"))
    status_filter = parse_todo_filter_status(request.GET.get("status"))
    sort_key = parse_todo_sort_key(request.GET.get("sort"))
    is_focus_mode = request.GET.get("focus") == "1"

    todo_item = get_object_or_404(TodoItem, id=item_id, user_id=user_id)
    result = services.delete_todo(todo_item)

    logger.info(
        "Todoアイテムを削除しました: user_id=%s, id=%d, description='%s'",
        user_id,
        item_id,
        result.description,
    )

    page_obj = queries.get_paginated_todos(
        user_id=user_id,
        page_number=page_number,
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )

    # フォーカスモードから削除した場合は、フォーカスモード自体を終了
    if is_focus_mode:
        oob_response = htmx_responses.render_todo_list_with_pagination_oob(
            page_obj,
            query=query,
            status_filter=status_filter,
            sort_key=sort_key,
            today_completed_count=queries.get_today_completed_count(user_id),
            include_main_list=False,
            include_list_oob=True,
        )
        focus_mode_oob = htmx_responses.render_focus_mode_delete_oob()
        return HttpResponse(focus_mode_oob + oob_response.content.decode("utf-8"))

    return htmx_responses.render_todo_list_with_pagination_oob(
        page_obj,
        query=query,
        status_filter=status_filter,
        sort_key=sort_key,
        today_completed_count=queries.get_today_completed_count(user_id),
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

    result = services.delete_all_todos(user_id)

    logger.info(
        "全てのTodoアイテムを一括削除しました: user_id=%s, 削除件数=%d",
        user_id,
        result.deleted_count,
    )

    page_obj = queries.get_paginated_todos(
        user_id=user_id,
        page_number=DEFAULT_PAGE,
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )
    return htmx_responses.render_todo_list_with_pagination_oob(
        page_obj,
        query=query,
        status_filter=status_filter,
        sort_key=sort_key,
        today_completed_count=queries.get_today_completed_count(user_id),
    )


@login_required
def delete_completed_todo_items(request: HttpRequest) -> HttpResponse:
    """完了済みTodoアイテムを一括削除する。

    検索条件やフィルタ状態に依存せず、「完了済み（completed=True）」のTodoのみを削除する。
    削除後は、現在の検索/フィルタ/並び替え条件でページ1を再描画して返す。

    Args:
        request: HTTPリクエストオブジェクト。

    Returns:
        削除成功時: 更新されたTodoリストとページネーション情報のHttpResponse。
        メソッド不正時: 405 Method Not AllowedのHttpResponse。
    """
    if request.method != RequestMethod.DELETE:
        return HttpResponse(status=HTTPStatus.METHOD_NOT_ALLOWED)

    user_id = get_authenticated_user_id(request)
    query = parse_todo_search_query(request.GET.get("q"))
    status_filter = parse_todo_filter_status(request.GET.get("status"))
    sort_key = parse_todo_sort_key(request.GET.get("sort"))

    result = services.delete_completed_todos(user_id)

    logger.info(
        "完了済みTodoアイテムを一括削除しました: user_id=%s, 削除件数=%d",
        user_id,
        result.deleted_count,
    )

    page_obj = queries.get_paginated_todos(
        user_id=user_id,
        page_number=DEFAULT_PAGE,
        query=query,
        status=status_filter,
        sort_key=sort_key,
    )
    return htmx_responses.render_todo_list_with_pagination_oob(
        page_obj,
        query=query,
        status_filter=status_filter,
        sort_key=sort_key,
        today_completed_count=queries.get_today_completed_count(user_id),
    )


# =============================================================================
# フォーカスモード
# =============================================================================


@login_required
def enter_focus_mode(request: HttpRequest, item_id: int) -> HttpResponse:
    """フォーカスモードに入る（単一Todoをフルスクリーン表示）。

    Args:
        request: HTTPリクエストオブジェクト。
        item_id: フォーカスするTodoアイテムID。

    Returns:
        フォーカスモード用のオーバーレイHTMLを含むHttpResponse。
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
        "todo/_todo_focus_mode.html",
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
def exit_focus_mode(request: HttpRequest) -> HttpResponse:
    """フォーカスモードを終了する。

    空のレスポンスを返してオーバーレイをDOMから削除する。

    Args:
        request: HTTPリクエストオブジェクト。

    Returns:
        空のHttpResponse（hx-swap="outerHTML"でオーバーレイが消える）。
        メソッド不正時: 405 Method Not AllowedのHttpResponse。
    """
    if request.method != RequestMethod.GET:
        return HttpResponse(status=HTTPStatus.METHOD_NOT_ALLOWED)

    return HttpResponse("")

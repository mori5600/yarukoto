import logging
from http import HTTPStatus

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404

from django_todo.auth import get_authenticated_user_id
from shared.enums import RequestMethod

from .. import htmx_responses, queries, services
from ..models import TodoItem
from ..params import (
    DEFAULT_PAGE,
    parse_page_number,
    parse_todo_filter_status,
    parse_todo_search_query,
    parse_todo_sort_key,
)

logger = logging.getLogger(__name__)


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

import logging
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse

from django_todo.auth import get_authenticated_user_id
from shared.enums import RequestMethod

from .. import htmx_responses, queries, services
from ..forms import TodoItemForm
from ..params import (
    DEFAULT_PAGE,
    parse_todo_filter_status,
    parse_todo_search_query,
    parse_todo_sort_key,
)

logger = logging.getLogger(__name__)


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

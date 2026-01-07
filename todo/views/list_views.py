import logging
from http import HTTPStatus

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from django_todo.auth import get_authenticated_user_id
from shared.enums import RequestMethod

from .. import queries
from ..forms import TodoItemForm
from ..models import TodoItem
from ..params import (
    DEFAULT_PAGE,
    build_todo_list_querystring,
    parse_page_number,
    parse_todo_filter_status,
    parse_todo_search_query,
    parse_todo_sort_key,
)

logger = logging.getLogger(__name__)


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

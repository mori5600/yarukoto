import logging
from http import HTTPStatus

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from django_todo.auth import get_authenticated_user_id
from shared.enums import RequestMethod

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

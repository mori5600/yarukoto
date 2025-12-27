"""Todo関連のビュー。

HTTPリクエスト処理（認可・バリデーション・DB操作）を担当する。
"""

import logging
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from django_todo.auth import get_authenticated_user_id

from ..forms import TodoItemForm
from ..models import TodoItem
from .helpers import (
    DEFAULT_PAGE,
    get_paginated_todos,
    parse_page_number,
    render_todo_list_with_pagination_oob,
)
from utils.enums import RequestMethod

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
    page_obj = get_paginated_todos(user_id=user_id, page_number=page_number)
    form = TodoItemForm()

    return render(
        request,
        "todo/todo_list.html",
        {
            "page_obj": page_obj,
            "form": form,
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
    page_obj = get_paginated_todos(user_id=user_id, page_number=page_number)
    return render(request, "todo/_todo_list.html", {"page_obj": page_obj})


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
    max_items = getattr(settings, "TODO_MAX_ITEMS_PER_USER", 1000)
    current_count = TodoItem.objects.filter(user_id=user_id).count()
    if current_count >= max_items:
        logger.info(
            "Todo上限に達しました: user_id=%s, count=%d, max=%d",
            user_id,
            current_count,
            max_items,
        )
        page_obj = get_paginated_todos(user_id=user_id, page_number=DEFAULT_PAGE)
        return render_todo_list_with_pagination_oob(
            page_obj,
            form_error_message=(
                f"Todoは1ユーザーあたり最大{max_items}件までです。不要なTodoを削除してください。"
            ),
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
        page_obj = get_paginated_todos(user_id=user_id, page_number=DEFAULT_PAGE)
        return render_todo_list_with_pagination_oob(page_obj)

    logger.warning("Todoアイテムの作成に失敗しました: errors=%s", form.errors.as_json())
    page_obj = get_paginated_todos(user_id=user_id, page_number=DEFAULT_PAGE)
    message = (
        "Todoを入力してください。"
        if "description" in form.errors
        else "入力内容を確認してください。"
    )
    return render_todo_list_with_pagination_oob(
        page_obj,
        form_error_message=message,
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
    return render(request, "todo/_todo_item.html", {"todo_item": todo_item})


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
    description = todo_item.description
    todo_item.delete()
    logger.info(
        "Todoアイテムを削除しました: user_id=%s, id=%d, description='%s'",
        user_id,
        item_id,
        description,
    )
    page_obj = get_paginated_todos(user_id=user_id, page_number=page_number)
    return render_todo_list_with_pagination_oob(page_obj)


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
    queryset = TodoItem.objects.filter(user_id=user_id)
    count = queryset.count()
    queryset.delete()
    logger.info(
        "全てのTodoアイテムを一括削除しました: user_id=%s, 削除件数=%d",
        user_id,
        count,
    )
    page_obj = get_paginated_todos(user_id=user_id, page_number=DEFAULT_PAGE)
    return render_todo_list_with_pagination_oob(page_obj)

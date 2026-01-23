import logging
from http import HTTPStatus

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from django_todo.auth import get_authenticated_user_id
from shared.enums import RequestMethod

from .. import htmx_responses, queries, services
from ..models import TodoItem
from ..params import (
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
    raw_notes = request.POST.get("notes") if "notes" in request.POST else None
    notes_in_request = raw_notes is not None
    new_notes = raw_notes.strip() if notes_in_request else ""
    result = services.update_todo_content(
        todo_item,
        new_description,
        new_notes=new_notes,
        notes_in_request=notes_in_request,
    )

    if not result.success:
        template = "todo/_todo_focus_item_edit.html" if is_focus_mode else "todo/_todo_item_edit.html"
        context = {
            "todo_item": todo_item,
            "draft_description": raw_description,
            "error_message": result.error,
            "current_page": page_number,
            "current_q": query,
            "current_status": status_filter.value,
            "current_sort": sort_key.value,
            "list_querystring": list_querystring,
        }
        if notes_in_request:
            context["draft_notes"] = raw_notes

        return render(
            request,
            template,
            context,
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

"""Todo一覧の読み取りクエリ。

データベースからTodoを取得するQuery Objectパターン。
Django ORMに依存するが、ビジネスロジックは含まない。
API化時にも再利用可能。
"""

from django.core.paginator import Page, Paginator
from django.utils import timezone

from .models import TodoItem
from .params import (
    DEFAULT_PAGE,
    DEFAULT_TODO_FILTER_STATUS,
    DEFAULT_TODO_SORT_KEY,
    TODOS_PER_PAGE,
    TodoFilterStatus,
    TodoSortKey,
    normalize_todo_filter_status,
    normalize_todo_sort_key,
)


def get_paginated_todos(
    *,
    user_id: int,
    page_number: int = DEFAULT_PAGE,
    per_page: int = TODOS_PER_PAGE,
    query: str = "",
    status: TodoFilterStatus | str = DEFAULT_TODO_FILTER_STATUS,
    sort_key: TodoSortKey | str = DEFAULT_TODO_SORT_KEY,
) -> Page[TodoItem]:
    """ページネーション済みのTodoリストを取得する。

    データベースからTodoアイテムを取得し、フィルタ・検索・並び替えを適用して
    指定されたページサイズでページネーションを適用する。

    Args:
        user_id: Todoを取得する対象ユーザーID。
        page_number: 取得するページ番号。デフォルトは1。
        per_page: 1ページあたりのアイテム数。デフォルトは10。
        query: 検索文字列（description に部分一致）。
        status: フィルタ状態（all/active/completed）。
        sort_key: 並び替えキー（created/updated/active_first）。

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


def get_today_completed_count(user_id: int) -> int:
    """今日完了したTodoの件数を取得する。

    Args:
        user_id: 対象ユーザーID。

    Returns:
        今日（ローカル日付）に完了状態になったTodoの件数。
    """
    today = timezone.localdate()
    return TodoItem.objects.filter(
        user_id=user_id,
        completed=True,
        updated_at__date=today,
    ).count()


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


def get_todo_by_id(*, item_id: int, user_id: int) -> TodoItem | None:
    """指定IDのTodoを取得する。

    Args:
        item_id: TodoアイテムID。
        user_id: 所有ユーザーID。

    Returns:
        TodoItemインスタンス。存在しなければNone。
    """
    return TodoItem.objects.filter(id=item_id, user_id=user_id).first()


def get_user_todo_count(user_id: int) -> int:
    """指定ユーザーのTodo総数を取得する。

    Args:
        user_id: 対象ユーザーID。

    Returns:
        Todo件数。
    """
    return TodoItem.objects.filter(user_id=user_id).count()

"""Todo一覧のパラメータ解析・正規化。

HTTPリクエストのクエリパラメータを型安全な値に変換する。
Django非依存（標準ライブラリのみ）で、API化時にも再利用可能。
"""

from enum import StrEnum
from typing import Final
from urllib.parse import urlencode

# =============================================================================
# 定数
# =============================================================================

DEFAULT_PAGE: Final[int] = 1
TODOS_PER_PAGE: Final[int] = 10
DESCRIPTION_MAX_LENGTH: Final[int] = 255


# =============================================================================
# Enum
# =============================================================================


class TodoFilterStatus(StrEnum):
    """Todoのフィルタ状態。"""

    ALL = "all"
    ACTIVE = "active"
    COMPLETED = "completed"


DEFAULT_TODO_FILTER_STATUS: Final[TodoFilterStatus] = TodoFilterStatus.ALL


class TodoSortKey(StrEnum):
    """Todo一覧の並び替えキー。"""

    CREATED = "created"
    UPDATED = "updated"
    ACTIVE_FIRST = "active_first"


DEFAULT_TODO_SORT_KEY: Final[TodoSortKey] = TodoSortKey.CREATED


# =============================================================================
# パラメータ正規化
# =============================================================================


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
    """Todoのフィルタ状態を正規化する（クエリ文字列専用）。

    Args:
        raw_status: クエリパラメータ等で受け取ったフィルタ状態。

    Returns:
        正規化されたフィルタ状態。未指定・不正値は "all"。
    """
    return normalize_todo_filter_status(raw_status)


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
    """Todo一覧の並び替えキーを正規化する（クエリ文字列専用）。

    Args:
        raw_sort: クエリパラメータ等で受け取った並び替えキー。

    Returns:
        正規化された並び替えキー。未指定・不正値は created。
    """
    return normalize_todo_sort_key(raw_sort)


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
        sort_key: 並び替えキー。

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

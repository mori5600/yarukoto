"""Todo操作のビジネスロジック（サービス層）。

書き込み操作（create/update/delete）とビジネスルールを提供する。
Result型で成功/失敗を表現し、API化時にも再利用可能。
"""

from dataclasses import dataclass

from .models import TodoItem
from .params import DESCRIPTION_MAX_LENGTH, NOTES_MAX_LENGTH
from .queries import is_todo_limit_reached

# =============================================================================
# Result 型
# =============================================================================


@dataclass(frozen=True)
class CreateTodoResult:
    """Todo作成の結果。"""

    success: bool
    todo_item: TodoItem | None = None
    error: str | None = None


@dataclass(frozen=True)
class UpdateTodoResult:
    """Todo更新の結果。"""

    success: bool
    todo_item: TodoItem | None = None
    changed: bool = False
    error: str | None = None


@dataclass(frozen=True)
class ToggleCompletionResult:
    """Todo完了状態トグルの結果。"""

    success: bool
    todo_item: TodoItem | None = None
    old_status: bool = False


@dataclass(frozen=True)
class DeleteResult:
    """Todo削除の結果。"""

    success: bool
    deleted_count: int = 0
    description: str | None = None  # 単一削除時のログ用


# =============================================================================
# 作成
# =============================================================================


def create_todo(
    *,
    user_id: int,
    description: str,
    max_items: int,
) -> CreateTodoResult:
    """Todoを作成する。

    上限チェックを行い、問題なければ新規Todoを作成する。

    Args:
        user_id: 所有ユーザーID。
        description: Todo説明文。
        max_items: ユーザーごとのTodo上限件数。

    Returns:
        CreateTodoResult。成功時はtodo_itemにインスタンス、
        失敗時はerrorにメッセージ。
    """
    if is_todo_limit_reached(user_id=user_id, max_items=max_items):
        return CreateTodoResult(
            success=False,
            error=f"Todoは1ユーザーあたり最大{max_items}件までです。不要なTodoを削除してください。",
        )

    todo_item = TodoItem.objects.create(user_id=user_id, description=description)
    return CreateTodoResult(success=True, todo_item=todo_item)


# =============================================================================
# 更新
# =============================================================================


def toggle_todo_completion(todo_item: TodoItem) -> ToggleCompletionResult:
    """完了状態をトグルする。

    Args:
        todo_item: 対象のTodoItem。

    Returns:
        ToggleCompletionResult。old_statusに変更前の状態。
    """
    old_status = todo_item.completed
    todo_item.completed = not todo_item.completed
    todo_item.save(update_fields=["completed", "updated_at"])
    return ToggleCompletionResult(
        success=True,
        todo_item=todo_item,
        old_status=old_status,
    )


def update_todo_content(
    todo_item: TodoItem,
    new_description: str,
    *,
    new_notes: str | None = None,
    notes_in_request: bool = False,
    max_description_length: int | None = None,
    max_notes_length: int | None = None,
) -> UpdateTodoResult:
    """説明文/メモを更新する。

    バリデーション（空文字チェック、最大長チェック）を行い、
    問題なければ更新する。

    Args:
        todo_item: 対象のTodoItem。
        new_description: 新しい説明文（strip済みを期待）。
        new_notes: 新しいメモ（strip済み）。notes_in_request=False のときは無視。
        notes_in_request: notes がリクエストに含まれているか。
        max_description_length: 説明文の最大長。Noneの場合はモデルから取得。
        max_notes_length: メモの最大長。Noneの場合はモデルから取得。

    Returns:
        UpdateTodoResult。changedは実際に変更があったか。
    """
    if max_description_length is None:
        description_field = TodoItem._meta.get_field("description")
        field_max_length = getattr(description_field, "max_length", None)
        max_description_length = (
            field_max_length if isinstance(field_max_length, int) else DESCRIPTION_MAX_LENGTH
        )

    if not new_description:
        return UpdateTodoResult(
            success=False,
            todo_item=todo_item,
            error="Todoを入力してください。",
        )

    if len(new_description) > max_description_length:
        return UpdateTodoResult(
            success=False,
            todo_item=todo_item,
            error=f"Todoは最大{max_description_length}文字までです。",
        )

    if notes_in_request:
        if new_notes is None:
            new_notes = ""

        if max_notes_length is None:
            notes_field = TodoItem._meta.get_field("notes")
            field_max_length = getattr(notes_field, "max_length", None)
            max_notes_length = field_max_length if isinstance(field_max_length, int) else NOTES_MAX_LENGTH

        if len(new_notes) > max_notes_length:
            return UpdateTodoResult(
                success=False,
                todo_item=todo_item,
                error=f"メモは最大{max_notes_length}文字までです。",
            )

    changed_fields: list[str] = []
    if new_description != todo_item.description:
        todo_item.description = new_description
        changed_fields.append("description")
    if notes_in_request and new_notes is not None and new_notes != todo_item.notes:
        todo_item.notes = new_notes
        changed_fields.append("notes")

    if not changed_fields:
        return UpdateTodoResult(
            success=True,
            todo_item=todo_item,
            changed=False,
        )

    todo_item.save(update_fields=[*changed_fields, "updated_at"])
    return UpdateTodoResult(
        success=True,
        todo_item=todo_item,
        changed=True,
    )


def update_todo_description(
    todo_item: TodoItem,
    new_description: str,
    *,
    max_length: int | None = None,
) -> UpdateTodoResult:
    """説明文を更新する。

    Args:
        todo_item: 対象のTodoItem。
        new_description: 新しい説明文（strip済みを期待）。
        max_length: 最大長。Noneの場合はモデルから取得。

    Returns:
        UpdateTodoResult。changedは実際に変更があったか。
    """
    return update_todo_content(
        todo_item,
        new_description,
        notes_in_request=False,
        max_description_length=max_length,
    )


# =============================================================================
# 削除
# =============================================================================


def delete_todo(todo_item: TodoItem) -> DeleteResult:
    """単一のTodoを削除する。

    Args:
        todo_item: 削除対象のTodoItem。

    Returns:
        DeleteResult。descriptionにログ用の説明文。
    """
    description = todo_item.description
    todo_item.delete()
    return DeleteResult(success=True, deleted_count=1, description=description)


def delete_all_todos(user_id: int) -> DeleteResult:
    """指定ユーザーの全Todoを削除する。

    Args:
        user_id: 対象ユーザーID。

    Returns:
        DeleteResult。deleted_countに削除件数。
    """
    deleted_count, _ = TodoItem.objects.filter(user_id=user_id).delete()
    return DeleteResult(success=True, deleted_count=deleted_count)


def delete_completed_todos(user_id: int) -> DeleteResult:
    """指定ユーザーの完了済みTodoを削除する。

    Args:
        user_id: 対象ユーザーID。

    Returns:
        DeleteResult。deleted_countに削除件数。
    """
    deleted_count, _ = TodoItem.objects.filter(user_id=user_id, completed=True).delete()
    return DeleteResult(success=True, deleted_count=deleted_count)


# =============================================================================
# ビジネスルール判定
# =============================================================================


def needs_list_refresh_on_toggle(
    *,
    status_filter: str,
    sort_key: str,
) -> bool:
    """完了トグル時に一覧の再描画が必要か判定する。

    Args:
        status_filter: 現在のフィルタ状態。
        sort_key: 現在の並び替えキー。

    Returns:
        再描画が必要ならTrue。
    """
    # status != all: トグルで一覧から消える/出る可能性
    # sort=active_first: completed が変わると順序が変わる
    # sort=updated: updated_at が更新され、順序が変わる
    return status_filter != "all" or sort_key in {"active_first", "updated"}


def needs_list_refresh_on_edit(
    *,
    changed: bool,
    query: str,
    sort_key: str,
) -> bool:
    """編集時に一覧の再描画が必要か判定する。

    Args:
        changed: 実際に変更があったか。
        query: 検索クエリ。
        sort_key: 現在の並び替えキー。

    Returns:
        再描画が必要ならTrue。
    """
    # 変更がなければ不要
    if not changed:
        return False
    # 検索中は、編集により検索結果から外れる/入る可能性がある
    # sort=updated は updated_at で順序が動く
    return bool(query) or sort_key == "updated"

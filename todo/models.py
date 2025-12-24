"""Todoアプリケーションのデータモデル定義。

Todoアイテムを管理するためのモデルを提供する。
"""

from django.conf import settings
from django.db import models


class TodoItem(models.Model):
    """Todoアイテムを表すモデル。

    各Todoアイテムは説明文、完了状態、作成日時、更新日時を持つ。
    Todoアイテムは作成者（User）に紐づく。

    Attributes:
        id: 自動生成されるプライマリキー。
        user: Todoアイテムの所有者（ユーザー）。
        description: Todoアイテムの説明文。最大255文字。
        completed: 完了状態を示すブール値。デフォルトはFalse。
        created_at: アイテムの作成日時。自動設定される。
        updated_at: アイテムの最終更新日時。自動更新される。
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="todo_items",
        null=True,
        blank=True,
        db_index=True,
    )
    description = models.CharField(max_length=255)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "-created_at"], name="todo_user_created_at"),
        ]

    def __str__(self) -> str:
        """Todoアイテムの文字列表現を返す。

        Returns:
            Todoアイテムの説明文。
        """
        return self.description

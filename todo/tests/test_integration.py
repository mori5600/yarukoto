"""統合テスト。"""

from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from ..models import TodoItem


class IntegrationTests(TestCase):
    """統合テストケース。"""

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="user", password="pass")
        self.client.force_login(self.user)

    def test_full_todo_lifecycle(self):
        """Todo作成から削除までの完全なライフサイクルを確認する。"""
        # 作成
        response = self.client.post(
            reverse("todo:create_todo_item"), {"description": "ライフサイクルテスト"}
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(TodoItem.objects.count(), 1)

        todo = TodoItem.objects.first()
        assert todo is not None
        self.assertFalse(todo.completed)

        # 更新（完了状態切り替え）
        response = self.client.post(reverse("todo:update_todo_item", args=[todo.pk]))
        self.assertEqual(response.status_code, HTTPStatus.OK)

        todo.refresh_from_db()
        self.assertTrue(todo.completed)

        # 削除
        response = self.client.delete(reverse("todo:delete_todo_item", args=[todo.pk]))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(TodoItem.objects.count(), 0)

    def test_pagination_after_operations(self):
        """操作後のページネーションが正しく機能することを確認する。"""
        # 15個のアイテムを作成
        for i in range(15):
            TodoItem.objects.create(user=self.user, description=f"タスク {i + 1}")

        # 1ページ目の確認
        response = self.client.get(reverse("todo:todo_list"))
        self.assertEqual(len(response.context["page_obj"]), 10)

        # 新しいアイテムを追加
        self.client.post(
            reverse("todo:create_todo_item"), {"description": "新規タスク"}
        )

        # 合計16個になり、2ページ必要
        response = self.client.get(reverse("todo:todo_list"))
        self.assertEqual(response.context["page_obj"].paginator.num_pages, 2)

    def test_delete_all_after_create(self):
        """複数アイテム作成後の全削除を確認する。"""
        # 複数のアイテムを作成
        for i in range(5):
            self.client.post(
                reverse("todo:create_todo_item"),
                {"description": f"タスク {i + 1}"},
            )
        self.assertEqual(TodoItem.objects.count(), 5)

        # 全削除
        response = self.client.delete(reverse("todo:delete_all_todo_items"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(TodoItem.objects.count(), 0)

    def test_delete_all_with_mixed_completion_status(self):
        """完了・未完了が混在する状態での全削除を確認する。"""
        # アイテムを作成
        todo1 = TodoItem.objects.create(user=self.user, description="未完了タスク1")
        todo2 = TodoItem.objects.create(
            user=self.user, description="完了タスク", completed=True
        )
        todo3 = TodoItem.objects.create(user=self.user, description="未完了タスク2")
        self.assertEqual(TodoItem.objects.count(), 3)

        # 全削除（完了状態に関わらず全て削除される）
        response = self.client.delete(reverse("todo:delete_all_todo_items"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(TodoItem.objects.count(), 0)

    def test_create_after_delete_all(self):
        """全削除後に新規作成できることを確認する。"""
        # アイテムを作成
        TodoItem.objects.create(user=self.user, description="タスク1")
        TodoItem.objects.create(user=self.user, description="タスク2")

        # 全削除
        self.client.delete(reverse("todo:delete_all_todo_items"))
        self.assertEqual(TodoItem.objects.count(), 0)

        # 新規作成
        response = self.client.post(
            reverse("todo:create_todo_item"), {"description": "新しいタスク"}
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(TodoItem.objects.count(), 1)

        todo = TodoItem.objects.first()
        assert todo is not None
        self.assertEqual(todo.description, "新しいタスク")

    def test_pagination_reset_after_delete_all(self):
        """全削除後にページネーションがリセットされることを確認する。"""
        # 15個のアイテムを作成（2ページ分）
        for i in range(15):
            TodoItem.objects.create(user=self.user, description=f"タスク {i + 1}")

        response = self.client.get(reverse("todo:todo_list"))
        self.assertEqual(response.context["page_obj"].paginator.num_pages, 2)

        # 全削除
        self.client.delete(reverse("todo:delete_all_todo_items"))

        # ページネーションがリセットされる
        response = self.client.get(reverse("todo:todo_list"))
        self.assertEqual(response.context["page_obj"].paginator.count, 0)
        self.assertEqual(response.context["page_obj"].paginator.num_pages, 1)

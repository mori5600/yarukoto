"""TodoItemモデルのテスト。"""

from django.contrib.auth import get_user_model
from django.db.models import CharField, TextField
from django.test import TestCase

from ..models import TodoItem


class TodoItemModelTests(TestCase):
    """TodoItemモデルのテストケース。"""

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="user", password="pass")

    def test_create_todo_item(self):
        """Todoアイテムが正しく作成されることを確認する。"""
        todo = TodoItem.objects.create(user=self.user, description="テストタスク")
        self.assertEqual(todo.description, "テストタスク")
        self.assertEqual(todo.user, self.user)
        self.assertFalse(todo.completed)
        self.assertIsNotNone(todo.created_at)
        self.assertIsNotNone(todo.updated_at)

    def test_str_representation(self):
        """__str__メソッドが説明文を返すことを確認する。"""
        todo = TodoItem.objects.create(user=self.user, description="テストタスク")
        self.assertEqual(str(todo), "テストタスク")

    def test_default_completed_is_false(self):
        """completedフィールドのデフォルト値がFalseであることを確認する。"""
        todo = TodoItem.objects.create(user=self.user, description="テストタスク")
        self.assertFalse(todo.completed)

    def test_toggle_completed(self):
        """完了状態の切り替えが正しく動作することを確認する。"""
        todo = TodoItem.objects.create(user=self.user, description="テストタスク")
        self.assertFalse(todo.completed)

        todo.completed = True
        todo.save()
        todo.refresh_from_db()
        self.assertTrue(todo.completed)

    def test_description_max_length(self):
        """説明文の最大長が255文字であることを確認する。"""
        field = TodoItem._meta.get_field("description")
        assert isinstance(field, CharField)
        self.assertEqual(field.max_length, 255)

    def test_notes_default_empty(self):
        """メモがデフォルトで空文字になることを確認する。"""
        todo = TodoItem.objects.create(user=self.user, description="テストタスク")
        self.assertEqual(todo.notes, "")

    def test_notes_max_length(self):
        """メモの最大長が1000文字であることを確認する。"""
        field = TodoItem._meta.get_field("notes")
        assert isinstance(field, TextField)
        self.assertEqual(field.max_length, 1000)

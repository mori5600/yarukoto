"""TodoItemFormのテスト。"""

from django.test import TestCase

from ..forms import TodoItemForm


class TodoItemFormTests(TestCase):
    """TodoItemFormのテストケース。"""

    def test_valid_form(self):
        """有効なデータでフォームが正しく検証されることを確認する。"""
        form_data = {"description": "新しいタスク"}
        form = TodoItemForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_empty_description(self):
        """空の説明文でフォームが無効になることを確認する。"""
        form_data = {"description": ""}
        form = TodoItemForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("description", form.errors)

    def test_form_saves_correctly(self):
        """フォームが正しくデータを保存することを確認する。"""
        form_data = {"description": "保存テスト"}
        form = TodoItemForm(data=form_data)
        self.assertTrue(form.is_valid())

        todo = form.save()
        self.assertEqual(todo.description, "保存テスト")
        self.assertFalse(todo.completed)

    def test_form_widget_attributes(self):
        """フォームウィジェットに正しい属性が設定されていることを確認する。"""
        form = TodoItemForm()
        widget_attrs = form.fields["description"].widget.attrs
        self.assertEqual(widget_attrs["class"], "form-control")
        self.assertEqual(widget_attrs["placeholder"], "新しいTodoを入力...")
        self.assertTrue(widget_attrs["required"])

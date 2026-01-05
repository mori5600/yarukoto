"""ビューのテスト。"""

from http import HTTPStatus
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from ..forms import TodoItemForm
from ..models import TodoItem


class TodoListViewTests(TestCase):
    """todo_listビューのテストケース。"""

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="user", password="pass")
        self.client.force_login(self.user)

    def test_view_url_exists(self):
        """ビューのURLが存在することを確認する。"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_view_redirects_when_not_logged_in(self):
        """未ログイン時はログインページへリダイレクトされることを確認する。"""
        self.client.logout()
        response = self.client.get("/")
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        self.assertIn("/accounts/login/", response["Location"])

    def test_view_url_accessible_by_name(self):
        """名前付きURLでビューにアクセスできることを確認する。"""
        response = self.client.get(reverse("todo:todo_list"))
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_view_uses_correct_template(self):
        """正しいテンプレートが使用されることを確認する。"""
        response = self.client.get(reverse("todo:todo_list"))
        self.assertTemplateUsed(response, "todo/todo_list.html")

    def test_view_contains_form(self):
        """ビューのコンテキストにフォームが含まれることを確認する。"""
        response = self.client.get(reverse("todo:todo_list"))
        self.assertIn("form", response.context)
        self.assertIsInstance(response.context["form"], TodoItemForm)

    def test_view_contains_page_obj(self):
        """ビューのコンテキストにページオブジェクトが含まれることを確認する。"""
        response = self.client.get(reverse("todo:todo_list"))
        self.assertIn("page_obj", response.context)

    def test_pagination_with_items(self):
        """Todoアイテムが存在する場合のページネーションを確認する。"""
        for i in range(15):
            TodoItem.objects.create(user=self.user, description=f"タスク {i + 1}")

        response = self.client.get(reverse("todo:todo_list"))
        self.assertEqual(len(response.context["page_obj"]), 10)


class TodoItemsViewTests(TestCase):
    """todo_itemsビューのテストケース。"""

    def setUp(self):
        """テスト用のTodoアイテムを作成する。"""
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="user", password="pass")
        self.client.force_login(self.user)
        for i in range(5):
            TodoItem.objects.create(user=self.user, description=f"タスク {i + 1}")

    def test_view_url_exists(self):
        """ビューのURLが存在することを確認する。"""
        response = self.client.get("/items/")
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_view_uses_partial_template(self):
        """部分テンプレートが使用されることを確認する。"""
        response = self.client.get(reverse("todo:todo_items"))
        self.assertTemplateUsed(response, "todo/_todo_list.html")

    def test_view_with_page_parameter(self):
        """ページパラメータが正しく処理されることを確認する。"""
        response = self.client.get(reverse("todo:todo_items"), {"page": "1"})
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_infinite_scroll_keeps_querystring(self):
        """無限スクロールの次ページURLが検索/フィルタ条件を保持することを確認する。"""
        TodoItem.objects.all().delete()
        for i in range(15):
            TodoItem.objects.create(user=self.user, description=f"タスク {i + 1}")

        response = self.client.get(
            reverse("todo:todo_items"),
            {"page": "1", "q": "タスク", "status": "active"},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

        expected_filter = urlencode({"q": "タスク", "status": "active"}).replace("&", "&amp;")
        content = response.content.decode()
        self.assertIn(f"?page=2&{expected_filter}", content)


class CreateTodoItemViewTests(TestCase):
    """create_todo_itemビューのテストケース。"""

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="user", password="pass")
        self.client.force_login(self.user)

    def test_create_with_valid_data(self):
        """有効なデータでTodoアイテムが作成されることを確認する。"""
        response = self.client.post(reverse("todo:create_todo_item"), {"description": "新しいタスク"})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(TodoItem.objects.count(), 1)

        todo = TodoItem.objects.first()
        assert todo is not None
        self.assertEqual(todo.description, "新しいタスク")

    def test_create_with_invalid_data(self):
        """無効なデータでBad Requestが返されることを確認する。"""
        response = self.client.post(reverse("todo:create_todo_item"), {"description": ""})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(TodoItem.objects.count(), 0)

    def test_create_with_get_method(self):
        """GETメソッドでBad Requestが返されることを確認する。"""
        response = self.client.get(reverse("todo:create_todo_item"))
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_response_contains_pagination_oob(self):
        """レスポンスにOOBスワップ属性が含まれることを確認する。"""
        response = self.client.post(reverse("todo:create_todo_item"), {"description": "新しいタスク"})
        content = response.content.decode()
        self.assertIn('hx-swap-oob="true"', content)

    @override_settings(TODO_MAX_ITEMS_PER_USER=1)
    def test_create_is_rejected_when_limit_reached(self):
        """上限到達時にTodo作成が拒否されることを確認する。"""
        response = self.client.post(reverse("todo:create_todo_item"), {"description": "1件目"})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(TodoItem.objects.filter(user=self.user).count(), 1)

        response = self.client.post(reverse("todo:create_todo_item"), {"description": "2件目"})
        self.assertEqual(response.status_code, HTTPStatus.CONFLICT)
        self.assertEqual(TodoItem.objects.filter(user=self.user).count(), 1)

        content = response.content.decode()
        self.assertIn("最大1件", content)


class UpdateTodoItemViewTests(TestCase):
    """update_todo_itemビューのテストケース。"""

    def setUp(self):
        """テスト用のTodoアイテムを作成する。"""
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="user", password="pass")
        self.other_user = user_model.objects.create_user(username="other", password="pass")
        self.client.force_login(self.user)
        self.todo: TodoItem = TodoItem.objects.create(user=self.user, description="テストタスク")

    def test_update_toggles_completed(self):
        """完了状態が正しく切り替わることを確認する。"""
        self.assertFalse(self.todo.completed)

        response = self.client.post(reverse("todo:update_todo_item", args=[self.todo.pk]))
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.todo.refresh_from_db()
        self.assertTrue(self.todo.completed)

    def test_update_with_nonexistent_id(self):
        """存在しないIDで404が返されることを確認する。"""
        response = self.client.post(reverse("todo:update_todo_item", args=[9999]))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_update_cannot_touch_other_users_item(self):
        """他ユーザーのTodoは更新できないことを確認する。"""
        other_todo = TodoItem.objects.create(user=self.other_user, description="他人のタスク")
        response = self.client.post(reverse("todo:update_todo_item", args=[other_todo.pk]))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_update_with_get_method(self):
        """GETメソッドでMethod Not Allowedが返されることを確認する。"""
        response = self.client.get(reverse("todo:update_todo_item", args=[self.todo.pk]))
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_response_uses_item_template(self):
        """レスポンスが_todo_item.htmlテンプレートを使用することを確認する。"""
        response = self.client.post(reverse("todo:update_todo_item", args=[self.todo.pk]))
        self.assertTemplateUsed(response, "todo/_todo_item.html")


class DeleteTodoItemViewTests(TestCase):
    """delete_todo_itemビューのテストケース。"""

    def setUp(self):
        """テスト用のTodoアイテムを作成する。"""
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="user", password="pass")
        self.other_user = user_model.objects.create_user(username="other", password="pass")
        self.client.force_login(self.user)
        self.todo: TodoItem = TodoItem.objects.create(user=self.user, description="削除テスト")

    def test_delete_removes_item(self):
        """Todoアイテムが正しく削除されることを確認する。"""
        self.assertEqual(TodoItem.objects.count(), 1)

        response = self.client.delete(reverse("todo:delete_todo_item", args=[self.todo.pk]))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(TodoItem.objects.count(), 0)

    def test_delete_with_nonexistent_id(self):
        """存在しないIDで404が返されることを確認する。"""
        response = self.client.delete(reverse("todo:delete_todo_item", args=[9999]))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_delete_with_post_method(self):
        """POSTメソッドでMethod Not Allowedが返されることを確認する。"""
        response = self.client.post(reverse("todo:delete_todo_item", args=[self.todo.pk]))
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_response_contains_pagination_oob(self):
        """レスポンスにOOBスワップ属性が含まれることを確認する。"""
        response = self.client.delete(reverse("todo:delete_todo_item", args=[self.todo.pk]))
        content = response.content.decode()
        self.assertIn('hx-swap-oob="true"', content)

    def test_delete_with_multiple_items(self):
        """複数アイテムがある場合の削除を確認する。"""
        TodoItem.objects.create(user=self.user, description="タスク2")
        TodoItem.objects.create(user=self.user, description="タスク3")
        self.assertEqual(TodoItem.objects.count(), 3)

        response = self.client.delete(reverse("todo:delete_todo_item", args=[self.todo.pk]))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(TodoItem.objects.count(), 2)
        self.assertFalse(TodoItem.objects.filter(id=self.todo.pk).exists())

    def test_delete_cannot_touch_other_users_item(self):
        """他ユーザーのTodoは削除できないことを確認する。"""
        other_todo = TodoItem.objects.create(user=self.other_user, description="他人のタスク")
        response = self.client.delete(reverse("todo:delete_todo_item", args=[other_todo.pk]))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


class DeleteAllTodoItemsViewTests(TestCase):
    """delete_all_todo_itemsビューのテストケース。"""

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="user", password="pass")
        self.other_user = user_model.objects.create_user(username="other", password="pass")
        self.client.force_login(self.user)

    def test_delete_all_removes_all_items(self):
        """全てのTodoアイテムが削除されることを確認する。"""
        TodoItem.objects.create(user=self.user, description="タスク1")
        TodoItem.objects.create(user=self.user, description="タスク2")
        TodoItem.objects.create(user=self.user, description="タスク3")
        self.assertEqual(TodoItem.objects.count(), 3)

        response = self.client.delete(reverse("todo:delete_all_todo_items"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(TodoItem.objects.count(), 0)

    def test_delete_all_with_empty_list(self):
        """Todoリストが空の場合も正常に動作することを確認する。"""
        self.assertEqual(TodoItem.objects.count(), 0)

        response = self.client.delete(reverse("todo:delete_all_todo_items"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(TodoItem.objects.count(), 0)

    def test_delete_all_with_post_method(self):
        """POSTメソッドでMethod Not Allowedが返されることを確認する。"""
        TodoItem.objects.create(user=self.user, description="タスク1")

        response = self.client.post(reverse("todo:delete_all_todo_items"))
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertEqual(TodoItem.objects.count(), 1)

    def test_delete_all_with_get_method(self):
        """GETメソッドでMethod Not Allowedが返されることを確認する。"""
        TodoItem.objects.create(user=self.user, description="タスク1")

        response = self.client.get(reverse("todo:delete_all_todo_items"))
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertEqual(TodoItem.objects.count(), 1)

    def test_response_contains_pagination_oob(self):
        """レスポンスにOOBスワップ属性が含まれることを確認する。"""
        TodoItem.objects.create(user=self.user, description="タスク1")

        response = self.client.delete(reverse("todo:delete_all_todo_items"))
        content = response.content.decode()
        self.assertIn('hx-swap-oob="true"', content)

    def test_delete_all_with_many_items(self):
        """多数のアイテムがある場合も全て削除されることを確認する。"""
        for i in range(25):
            TodoItem.objects.create(user=self.user, description=f"タスク {i + 1}")
        self.assertEqual(TodoItem.objects.count(), 25)

        response = self.client.delete(reverse("todo:delete_all_todo_items"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(TodoItem.objects.count(), 0)

    def test_delete_all_url_exists(self):
        """ビューのURLが存在することを確認する。"""
        response = self.client.delete("/delete-all/")
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_delete_all_does_not_delete_other_users_items(self):
        """全削除は自分のTodoのみ対象になることを確認する。"""
        TodoItem.objects.create(user=self.user, description="自分のタスク")
        TodoItem.objects.create(user=self.other_user, description="他人のタスク")
        self.assertEqual(TodoItem.objects.count(), 2)

        response = self.client.delete(reverse("todo:delete_all_todo_items"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(TodoItem.objects.filter(user=self.user).count(), 0)
        self.assertEqual(TodoItem.objects.filter(user=self.other_user).count(), 1)

    def test_response_contains_empty_list(self):
        """レスポンスに空のリストが含まれることを確認する。"""
        TodoItem.objects.create(user=self.user, description="タスク1")
        TodoItem.objects.create(user=self.user, description="タスク2")

        response = self.client.delete(reverse("todo:delete_all_todo_items"))
        content = response.content.decode()
        # ページネーション情報が0件を示していることを確認
        self.assertIn("全0件", content)


class DeleteCompletedTodoItemsViewTests(TestCase):
    """delete_completed_todo_itemsビューのテストケース。"""

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="user", password="pass")
        self.other_user = user_model.objects.create_user(username="other", password="pass")
        self.client.force_login(self.user)

    def test_delete_completed_removes_only_completed_items(self):
        """完了済みのみ削除され、未完了は残ることを確認する。"""
        active = TodoItem.objects.create(user=self.user, description="未完了", completed=False)
        completed1 = TodoItem.objects.create(user=self.user, description="完了1", completed=True)
        completed2 = TodoItem.objects.create(user=self.user, description="完了2", completed=True)
        other_completed = TodoItem.objects.create(
            user=self.other_user,
            description="他人の完了",
            completed=True,
        )
        self.assertEqual(TodoItem.objects.count(), 4)

        response = self.client.delete(reverse("todo:delete_completed_todo_items"))
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.assertTrue(TodoItem.objects.filter(id=active.pk).exists())
        self.assertFalse(TodoItem.objects.filter(id=completed1.pk).exists())
        self.assertFalse(TodoItem.objects.filter(id=completed2.pk).exists())
        self.assertTrue(TodoItem.objects.filter(id=other_completed.pk).exists())

    def test_delete_completed_is_not_affected_by_search_query(self):
        """検索条件に依存せず全完了が削除されることを確認する。"""
        TodoItem.objects.create(user=self.user, description="完了A", completed=True)
        TodoItem.objects.create(user=self.user, description="完了B", completed=True)
        TodoItem.objects.create(user=self.user, description="未完了", completed=False)

        url = reverse("todo:delete_completed_todo_items") + "?q=完了A&status=active"
        response = self.client.delete(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(TodoItem.objects.filter(user=self.user, completed=True).count(), 0)
        self.assertEqual(TodoItem.objects.filter(user=self.user, completed=False).count(), 1)

    def test_delete_completed_with_post_method(self):
        """POSTメソッドでMethod Not Allowedが返されることを確認する。"""
        TodoItem.objects.create(user=self.user, description="完了", completed=True)

        response = self.client.post(reverse("todo:delete_completed_todo_items"))
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertEqual(TodoItem.objects.filter(user=self.user, completed=True).count(), 1)

    def test_delete_completed_with_get_method(self):
        """GETメソッドでMethod Not Allowedが返されることを確認する。"""
        TodoItem.objects.create(user=self.user, description="完了", completed=True)

        response = self.client.get(reverse("todo:delete_completed_todo_items"))
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        self.assertEqual(TodoItem.objects.filter(user=self.user, completed=True).count(), 1)

    def test_response_contains_pagination_oob(self):
        """レスポンスにOOBスワップ属性が含まれることを確認する。"""
        TodoItem.objects.create(user=self.user, description="完了", completed=True)

        response = self.client.delete(reverse("todo:delete_completed_todo_items"))
        content = response.content.decode()
        self.assertIn('hx-swap-oob="true"', content)

    def test_delete_completed_url_exists(self):
        """ビューのURLが存在することを確認する。"""
        response = self.client.delete("/delete-completed/")
        self.assertEqual(response.status_code, HTTPStatus.OK)


class EditTodoItemViewTests(TestCase):
    """edit_todo_item / todo_item_partial のテストケース。"""

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="user", password="pass")
        self.other_user = user_model.objects.create_user(username="other", password="pass")
        self.client.force_login(self.user)
        self.todo: TodoItem = TodoItem.objects.create(user=self.user, description="編集前")

    def test_get_edit_renders_edit_partial(self):
        response = self.client.get(
            reverse("todo:edit_todo_item", args=[self.todo.pk]),
            {"page": "1", "sort": "created"},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "todo/_todo_item_edit.html")
        content = response.content.decode()
        self.assertIn('name="description"', content)
        self.assertIn('value="編集前"', content)

    def test_post_edit_updates_description_and_returns_list_oob(self):
        url = reverse("todo:edit_todo_item", args=[self.todo.pk]) + "?page=1&sort=updated"
        response = self.client.post(url, {"description": "編集後"})
        self.assertEqual(response.status_code, HTTPStatus.OK)

        self.todo.refresh_from_db()
        self.assertEqual(self.todo.description, "編集後")

        content = response.content.decode()
        self.assertIn('id="todo-list"', content)
        self.assertIn('hx-swap-oob="innerHTML"', content)

    def test_post_edit_rejected_when_empty(self):
        url = reverse("todo:edit_todo_item", args=[self.todo.pk]) + "?page=1"
        response = self.client.post(url, {"description": ""})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertTemplateUsed(response, "todo/_todo_item_edit.html")

    def test_cancel_uses_item_partial(self):
        response = self.client.get(
            reverse("todo:todo_item_partial", args=[self.todo.pk]),
            {"page": "1"},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "todo/_todo_item.html")

    def test_other_users_item_is_not_accessible(self):
        other_todo = TodoItem.objects.create(user=self.other_user, description="他人")
        response = self.client.get(reverse("todo:edit_todo_item", args=[other_todo.pk]))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

"""ヘルパー関数のテスト。"""

from datetime import timedelta
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from ..models import TodoItem
from ..views import get_paginated_todos


class GetPaginatedTodosTests(TestCase):
    """get_paginated_todos関数のテストケース。"""

    def setUp(self):
        """テスト用のTodoアイテムを作成する。"""
        user_model = get_user_model()
        self.user = user_model.objects.create_user(username="user", password="pass")
        for i in range(25):
            TodoItem.objects.create(user=self.user, description=f"タスク {i + 1}")

    def test_default_pagination(self):
        """デフォルトのページネーション（10件/ページ）が正しく動作することを確認する。"""
        assert self.user.id is not None
        page_obj = get_paginated_todos(user_id=self.user.id)
        self.assertEqual(len(page_obj), 10)
        self.assertEqual(page_obj.paginator.count, 25)
        self.assertEqual(page_obj.paginator.num_pages, 3)

    def test_custom_page_number(self):
        """指定したページ番号が正しく取得されることを確認する。"""
        assert self.user.id is not None
        page_obj = get_paginated_todos(user_id=self.user.id, page_number=2)
        self.assertEqual(page_obj.number, 2)
        self.assertEqual(len(page_obj), 10)

    def test_custom_per_page(self):
        """カスタムのページサイズが正しく適用されることを確認する。"""
        assert self.user.id is not None
        page_obj = get_paginated_todos(user_id=self.user.id, per_page=5)
        self.assertEqual(len(page_obj), 5)
        self.assertEqual(page_obj.paginator.num_pages, 5)

    def test_invalid_page_number(self):
        """無効なページ番号でも最終ページが返されることを確認する。"""
        assert self.user.id is not None
        page_obj = get_paginated_todos(user_id=self.user.id, page_number=999)
        self.assertEqual(page_obj.number, 3)  # 最終ページ

    def test_ordering(self):
        """Todoアイテムが作成日時の降順で並ぶことを確認する。"""
        assert self.user.id is not None
        page_obj = get_paginated_todos(user_id=self.user.id)
        first_item = page_obj[0]
        last_item = page_obj[len(page_obj) - 1]
        self.assertGreater(first_item.created_at, last_item.created_at)

    def test_filter_active(self):
        """未完了のみのフィルタが正しく動作することを確認する。"""
        assert self.user.id is not None
        ids = list(TodoItem.objects.filter(user=self.user).order_by("id").values_list("id", flat=True)[:5])
        TodoItem.objects.filter(id__in=ids).update(completed=True)
        page_obj = get_paginated_todos(user_id=self.user.id, status="active")
        self.assertEqual(page_obj.paginator.count, 20)
        self.assertTrue(all(not item.completed for item in page_obj))

    def test_filter_completed(self):
        """完了のみのフィルタが正しく動作することを確認する。"""
        assert self.user.id is not None
        ids = list(TodoItem.objects.filter(user=self.user).order_by("id").values_list("id", flat=True)[:5])
        TodoItem.objects.filter(id__in=ids).update(completed=True)
        page_obj = get_paginated_todos(user_id=self.user.id, status="completed")
        self.assertEqual(page_obj.paginator.count, 5)
        self.assertTrue(all(item.completed for item in page_obj))

    def test_search_query(self):
        """検索クエリで説明文が絞り込まれることを確認する。"""
        assert self.user.id is not None
        TodoItem.objects.create(user=self.user, description="買い物: りんご")
        TodoItem.objects.create(user=self.user, description="買い物: ばなな")
        page_obj = get_paginated_todos(user_id=self.user.id, query="りんご")
        self.assertEqual(page_obj.paginator.count, 1)
        self.assertEqual(page_obj[0].description, "買い物: りんご")

    def test_sort_updated_orders_by_updated_at_desc(self):
        """updated 指定時に updated_at の降順で並ぶことを確認する。"""
        assert self.user.id is not None

        target = TodoItem.objects.filter(user=self.user).order_by("id").first()
        assert target is not None

        TodoItem.objects.filter(id=target.id).update(updated_at=timezone.now() + timedelta(days=1))

        page_obj = get_paginated_todos(user_id=self.user.id, sort_key="updated")
        self.assertEqual(page_obj[0].id, target.id)

    def test_sort_active_first_orders_active_before_completed(self):
        """active_first 指定時に未完了が先頭へ来ることを確認する。"""
        assert self.user.id is not None

        newest = TodoItem.objects.filter(user=self.user).order_by("-created_at").first()
        assert newest is not None
        TodoItem.objects.filter(id=newest.id).update(completed=True)

        page_obj = get_paginated_todos(user_id=self.user.id, sort_key="active_first")
        self.assertFalse(page_obj[0].completed)


class QuerystringEncodingTests(TestCase):
    """テンプレで利用するクエリ文字列のエンコード例を固定する。"""

    def test_python_urlencode_matches_expected_order(self):
        """テスト内で使うエンコード順（q → status）を明示する。"""
        encoded = urlencode({"q": "abc", "status": "active"})
        self.assertEqual(encoded, "q=abc&status=active")

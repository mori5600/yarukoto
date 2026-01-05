"""ビューのテスト。"""

from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class DocsViewTests(TestCase):
    """docsビューのテストケース。"""

    def test_docs_is_accessible_when_not_logged_in(self):
        """未ログインでもdocsが表示できることを確認する。"""
        response = self.client.get(reverse("info:docs"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "docs.html")

    def test_docs_is_accessible_when_logged_in(self):
        """ログイン済みでもdocsが表示できることを確認する。"""
        user_model = get_user_model()
        user = user_model.objects.create_user(username="user", password="pass")
        self.client.force_login(user)
        response = self.client.get(reverse("info:docs"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(response, "docs.html")

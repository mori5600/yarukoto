"""accountsアプリケーションのテスト。

ユーザー登録機能のテストを提供する。
"""

from typing import cast

from django import forms
from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from accounts.forms import SignUpForm
from accounts.validators import (
    InvitationCodeValidator,
    NoOpValidator,
    get_signup_validator,
)


class InvitationCodeValidatorTest(TestCase):
    """招待コードバリデータのテスト。"""

    def test_get_form_field_returns_char_field(self) -> None:
        """フォームフィールドが返されることを確認する。"""
        validator = InvitationCodeValidator()
        field = validator.get_form_field()
        self.assertIsNotNone(field)
        # CharField の max_length を確認
        self.assertIsInstance(field, forms.CharField)
        char_field = cast(forms.CharField, field)
        self.assertEqual(char_field.max_length, 100)

    @override_settings(SIGNUP_INVITATION_CODE="test-code")
    def test_validate_success_with_correct_code(self) -> None:
        """正しいコードで検証が通ることを確認する。"""
        validator = InvitationCodeValidator()
        # 例外が発生しなければ成功
        validator.validate("test-code")

    @override_settings(SIGNUP_INVITATION_CODE="test-code")
    def test_validate_fails_with_wrong_code(self) -> None:
        """間違ったコードで検証が失敗することを確認する。"""
        from django.core.exceptions import ValidationError

        validator = InvitationCodeValidator()
        with self.assertRaises(ValidationError):
            validator.validate("wrong-code")

    @override_settings(SIGNUP_INVITATION_CODE="")
    def test_validate_fails_when_code_not_configured(self) -> None:
        """コードが設定されていない場合に検証が失敗することを確認する。"""
        from django.core.exceptions import ValidationError

        validator = InvitationCodeValidator()
        with self.assertRaises(ValidationError):
            validator.validate("any-code")


class NoOpValidatorTest(TestCase):
    """NoOpバリデータのテスト。"""

    def test_get_form_field_returns_none(self) -> None:
        """フィールドがNoneを返すことを確認する。"""
        validator = NoOpValidator()
        # NoOpValidator.get_form_field() は常にNoneを返す
        validator.get_form_field()  # 例外なく呼び出せることを確認
        # 型システムはこのメソッドがNoneを返すことを知っている

    def test_validate_always_passes(self) -> None:
        """常に検証が通ることを確認する。"""
        validator = NoOpValidator()
        # 例外が発生しなければ成功
        validator.validate("")
        validator.validate("any-value")


class GetSignupValidatorTest(TestCase):
    """get_signup_validator関数のテスト。"""

    @override_settings(SIGNUP_VALIDATOR="accounts.validators.InvitationCodeValidator")
    def test_returns_invitation_code_validator(self) -> None:
        """InvitationCodeValidatorが返されることを確認する。"""
        validator = get_signup_validator()
        self.assertIsInstance(validator, InvitationCodeValidator)

    @override_settings(SIGNUP_VALIDATOR="accounts.validators.NoOpValidator")
    def test_returns_noop_validator(self) -> None:
        """NoOpValidatorが返されることを確認する。"""
        validator = get_signup_validator()
        self.assertIsInstance(validator, NoOpValidator)


@override_settings(
    SIGNUP_VALIDATOR="accounts.validators.InvitationCodeValidator",
    SIGNUP_INVITATION_CODE="secret123",
)
class SignUpFormTest(TestCase):
    """SignUpFormのテスト。"""

    def test_form_has_invitation_code_field(self) -> None:
        """招待コードフィールドが存在することを確認する。"""
        form = SignUpForm()
        self.assertIn("invitation_code", form.fields)

    def test_form_valid_with_correct_data(self) -> None:
        """正しいデータでフォームが有効になることを確認する。"""
        form = SignUpForm(
            data={
                "username": "testuser",
                "password1": "TestPass123!",
                "password2": "TestPass123!",
                "invitation_code": "secret123",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_form_invalid_with_wrong_invitation_code(self) -> None:
        """間違った招待コードでフォームが無効になることを確認する。"""
        form = SignUpForm(
            data={
                "username": "testuser",
                "password1": "TestPass123!",
                "password2": "TestPass123!",
                "invitation_code": "wrong-code",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("invitation_code", form.errors)


@override_settings(SIGNUP_VALIDATOR="accounts.validators.NoOpValidator")
class SignUpFormNoOpTest(TestCase):
    """NoOpバリデータ使用時のSignUpFormのテスト。"""

    def test_form_does_not_have_invitation_code_field(self) -> None:
        """招待コードフィールドが存在しないことを確認する。"""
        form = SignUpForm()
        self.assertNotIn("invitation_code", form.fields)

    def test_form_valid_without_invitation_code(self) -> None:
        """招待コードなしでフォームが有効になることを確認する。"""
        form = SignUpForm(
            data={
                "username": "testuser",
                "password1": "TestPass123!",
                "password2": "TestPass123!",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)


@override_settings(
    SIGNUP_VALIDATOR="accounts.validators.InvitationCodeValidator",
    SIGNUP_INVITATION_CODE="secret123",
)
class SignUpViewTest(TestCase):
    """SignUpビューのテスト。"""

    def setUp(self) -> None:
        """テスト用クライアントを設定する。"""
        self.client = Client()
        self.signup_url = reverse("accounts:signup")

    def test_signup_page_returns_200(self) -> None:
        """登録ページが200を返すことを確認する。"""
        response = self.client.get(self.signup_url)
        self.assertEqual(response.status_code, 200)

    def test_signup_page_uses_correct_template(self) -> None:
        """正しいテンプレートが使用されることを確認する。"""
        response = self.client.get(self.signup_url)
        self.assertTemplateUsed(response, "account/signup.html")

    def test_signup_creates_user_with_valid_data(self) -> None:
        """有効なデータでユーザーが作成されることを確認する。"""
        response = self.client.post(
            self.signup_url,
            {
                "username": "newuser",
                "password1": "TestPass123!",
                "password2": "TestPass123!",
                "invitation_code": "secret123",
            },
        )
        self.assertRedirects(response, "/")
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_signup_logs_in_user_after_creation(self) -> None:
        """登録後にユーザーがログインしていることを確認する。"""
        self.client.post(
            self.signup_url,
            {
                "username": "newuser",
                "password1": "TestPass123!",
                "password2": "TestPass123!",
                "invitation_code": "secret123",
            },
        )
        # ログインしていることを確認（ホームページにアクセスできる）
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_signup_fails_with_wrong_invitation_code(self) -> None:
        """間違った招待コードで登録が失敗することを確認する。"""
        response = self.client.post(
            self.signup_url,
            {
                "username": "newuser",
                "password1": "TestPass123!",
                "password2": "TestPass123!",
                "invitation_code": "wrong-code",
            },
        )
        self.assertEqual(response.status_code, 200)  # フォーム再表示
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_authenticated_user_redirected_from_signup(self) -> None:
        """ログイン済みユーザーがリダイレクトされることを確認する。"""
        User.objects.create_user(username="existinguser", password="TestPass123!")
        self.client.login(username="existinguser", password="TestPass123!")
        response = self.client.get(self.signup_url)
        self.assertRedirects(response, "/")

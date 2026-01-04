"""ユーザー登録時の追加バリデーションモジュール。

登録フォームに追加するバリデーションロジックを提供する。
将来的に別の認証方式（reCAPTCHA、Turnstile等）に移行する場合は、
このモジュール内に新しいバリデータクラスを追加し、settings.SIGNUP_VALIDATOR を変更する。

使用方法:
    1. settings.SIGNUP_VALIDATOR に使用するバリデータクラスのパスを設定
    2. バリデータが get_form_field() で返すフィールドがフォームに追加される
    3. バリデータの validate() メソッドで入力値を検証する
"""

from abc import ABC, abstractmethod
from typing import Final

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.module_loading import import_string


class SignupValidator(ABC):
    """ユーザー登録バリデータの基底クラス。

    新しい検証方式を追加する場合は、このクラスを継承して実装する。
    """

    @abstractmethod
    def get_form_field(self) -> forms.Field | None:
        """フォームに追加するフィールドを返す。

        Returns:
            追加するフォームフィールド。フィールドが不要な場合はNone。
        """

    @abstractmethod
    def validate(self, value: str) -> None:
        """入力値を検証する。

        Args:
            value: フォームから受け取った値。

        Raises:
            ValidationError: 検証に失敗した場合。
        """


class InvitationCodeValidator(SignupValidator):
    """招待コード方式のバリデータ。

    settings.SIGNUP_INVITATION_CODE に設定されたコードと一致するかを検証する。
    """

    FIELD_NAME: Final[str] = "invitation_code"
    ERROR_MESSAGE: Final[str] = "招待コードが正しくありません。"
    MISSING_CODE_MESSAGE: Final[str] = "招待コードが設定されていません。管理者に連絡してください。"

    def get_form_field(self) -> forms.Field:
        """招待コード入力フィールドを返す。

        Returns:
            招待コード用のCharField。
        """
        return forms.CharField(
            max_length=100,
            widget=forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "招待コード",
                    "autocomplete": "off",
                }
            ),
            label="",
            help_text="登録には招待コードが必要です。",
        )

    def validate(self, value: str) -> None:
        """招待コードを検証する。

        Args:
            value: 入力された招待コード。

        Raises:
            ValidationError: コードが未設定または不一致の場合。
        """
        expected_code: str = getattr(settings, "SIGNUP_INVITATION_CODE", "")
        if not expected_code:
            raise ValidationError(self.MISSING_CODE_MESSAGE)
        if value != expected_code:
            raise ValidationError(self.ERROR_MESSAGE)


class NoOpValidator(SignupValidator):
    """検証なしのバリデータ。

    オープン登録を許可する場合に使用する。
    フォームにフィールドを追加せず、常に検証を通過する。
    """

    def get_form_field(self) -> None:
        """フィールドなし。

        Returns:
            None（フィールドを追加しない）。
        """
        return None

    def validate(self, value: str) -> None:
        """常に検証を通過する。

        Args:
            value: 未使用。
        """


def get_signup_validator() -> SignupValidator:
    """設定に基づいてバリデータインスタンスを取得する。

    settings.SIGNUP_VALIDATOR に指定されたクラスをインポートしてインスタンス化する。

    Returns:
        設定されたバリデータのインスタンス。

    Raises:
        ImportError: 指定されたバリデータクラスが見つからない場合。
    """
    validator_path: str = getattr(
        settings,
        "SIGNUP_VALIDATOR",
        "accounts.validators.InvitationCodeValidator",
    )
    validator_class = import_string(validator_path)
    return validator_class()

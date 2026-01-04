"""ユーザー登録フォーム。

Django標準のUserCreationFormを拡張し、追加バリデーションを組み込む。
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .validators import SignupValidator, get_signup_validator


class SignUpForm(UserCreationForm):
    """ユーザー登録フォーム。

    UserCreationFormを継承し、以下の機能を追加:
    - Bootstrapスタイルの適用
    - 設定に基づく追加バリデーション（招待コード等）

    Attributes:
        _validator: 使用するバリデータインスタンス。
    """

    _validator: SignupValidator

    def __init__(self, *args, **kwargs) -> None:
        """フォームを初期化する。

        Bootstrapスタイルを適用し、バリデータのフィールドを追加する。
        """
        super().__init__(*args, **kwargs)

        # Bootstrapスタイルを適用
        self.fields["username"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "ユーザー名",
            }
        )
        self.fields["username"].label = ""
        self.fields["username"].help_text = ""

        self.fields["password1"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "パスワード",
            }
        )
        self.fields["password1"].label = ""
        self.fields["password1"].help_text = ""

        self.fields["password2"].widget.attrs.update(
            {
                "class": "form-control",
                "placeholder": "パスワード（確認）",
            }
        )
        self.fields["password2"].label = ""
        self.fields["password2"].help_text = ""

        # バリデータからフィールドを追加
        self._validator = get_signup_validator()
        validator_field = self._validator.get_form_field()
        if validator_field is not None:
            # バリデータのフィールド名を取得（デフォルトは 'validation_field'）
            field_name = getattr(self._validator, "FIELD_NAME", "validation_field")
            self.fields[field_name] = validator_field

    class Meta:
        model = User
        fields = ("username", "password1", "password2")

    def clean(self) -> dict[str, object]:
        """フォーム全体のバリデーションを実行する。

        追加バリデータによる検証を実行する。

        Returns:
            クリーンされたデータ。

        Raises:
            ValidationError: バリデーションに失敗した場合。
        """
        cleaned_data = super().clean() or {}

        # バリデータのフィールド値を取得して検証
        field_name = getattr(self._validator, "FIELD_NAME", "validation_field")
        if field_name in self.fields:
            value = cleaned_data.get(field_name, "")
            try:
                self._validator.validate(str(value))
            except forms.ValidationError as e:
                self.add_error(field_name, e)

        return cleaned_data

"""認証関連フォーム。

Django標準の認証フォームにBootstrapの見た目を適用する。
"""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UsernameField


class BootstrapAuthenticationForm(AuthenticationForm):
    """Bootstrap対応のログインフォーム。"""

    username = UsernameField(
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "ユーザー名",
                "autocomplete": "username",
            }
        )
    )

    password = forms.CharField(
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "パスワード",
                "autocomplete": "current-password",
            }
        ),
    )

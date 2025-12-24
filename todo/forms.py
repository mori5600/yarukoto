"""Todoアプリケーションのフォーム定義。

Todoアイテムの作成・編集に使用するフォームを提供する。
"""

from django import forms

from .models import TodoItem


class TodoItemForm(forms.ModelForm):
    """Todoアイテムの作成・編集フォーム。

    ModelFormを使用してTodoItemモデルからフォームを自動生成する。
    descriptionフィールドのみを含み、Bootstrap対応のウィジェットを使用する。

    Note:
        ラベルは空文字列に設定されており、プレースホルダーで代替される。
    """

    class Meta:
        model = TodoItem
        fields = ["description"]
        widgets = {
            "description": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "新しいTodoを入力...",
                    "required": True,
                }
            )
        }
        labels = {
            "description": "",
        }

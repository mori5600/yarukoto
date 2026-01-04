"""accountsアプリケーションのビュー。

ユーザー登録に関するビューを提供する。
"""

from django.contrib.auth import login
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import SignUpForm


@require_http_methods(["GET", "POST"])
def signup(request: HttpRequest) -> HttpResponse:
    """ユーザー登録ビュー。

    GETリクエスト: 登録フォームを表示する。
    POSTリクエスト: フォームを検証し、ユーザーを作成する。

    Args:
        request: HTTPリクエスト。

    Returns:
        登録フォームのレンダリング結果、または登録成功時のリダイレクト。
    """
    if request.user.is_authenticated:
        return redirect("/")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("/")
    else:
        form = SignUpForm()

    return render(request, "account/signup.html", {"form": form})

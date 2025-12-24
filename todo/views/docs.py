"""ドキュメント（アプリ説明）ページのビュー。

本アプリの使い方・構成（Django + HTMX）を簡潔に説明する。
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def docs(request: HttpRequest) -> HttpResponse:
    """docsページを表示する。

    Args:
        request: HTTPリクエストオブジェクト。

    Returns:
        docsページのHttpResponse。
    """

    return render(request, "docs.html")

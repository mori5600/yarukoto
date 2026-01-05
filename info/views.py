"""案内ページ（ヘルプ/概要など）のビュー。

Todo機能とは独立した、サイト共通の情報ページを提供する。
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def docs(request: HttpRequest) -> HttpResponse:
    """Docsページ（使い方・構成説明）を表示する。

    Args:
            request: HTTPリクエストオブジェクト。

    Returns:
            docsページのHttpResponse。
    """

    return render(request, "docs.html")

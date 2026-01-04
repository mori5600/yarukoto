"""アプリケーション全体で使用される列挙型を定義するモジュール。

このモジュールには、HTTPリクエストメソッドなどの共有列挙型が含まれています。
"""

from enum import StrEnum


class RequestMethod(StrEnum):
    """HTTPリクエストメソッドを定義する列挙型。

    Attributes:
        GET (str): HTTPGETメソッド。
        POST (str): HTTPPOSTメソッド。
        PUT (str): HTTPPUTメソッド。
        DELETE (str): HTTPDELETEメソッド。
        PATCH (str): HTTPPATCHメソッド。
        HEAD (str): HTTPHEADメソッド。
        OPTIONS (str): HTTPOPTIONSメソッド。
    """

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"

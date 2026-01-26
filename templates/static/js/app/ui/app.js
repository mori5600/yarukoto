/**
 * Yarukoto - キーボードショートカット & UXエンハンスメント
 *
 * ショートカット:
 *   / : 検索欄にフォーカス
 *   n : 新規Todo入力欄にフォーカス
 *   f : フォーカスモードで最初のTodoを開く
 *   Esc : 編集モードをキャンセル（編集中の行を元に戻す）
 *
 * アニメーション:
 *   - 完了トグル時に行を軽くポップさせる
 *
 * @requires jQuery 3.7.1+ (MIT License)
 */
(function ($) {
  "use strict";

  function setHintStatus(message, tone) {
    var $status = $("#focus-first-status");
    if (!$status.length) return;

    var existingTimeout = $status.data("timeoutId");
    if (existingTimeout) {
      clearTimeout(existingTimeout);
      $status.removeData("timeoutId");
    }

    $status.removeClass("todo-hint-bar__message--info todo-hint-bar__message--warn");

    if (!message) {
      $status.text("");
      return;
    }

    if (tone) {
      $status.addClass("todo-hint-bar__message--" + tone);
    }

    $status.text(message);

    var timeoutId = setTimeout(function () {
      $status.text("");
      $status.removeClass("todo-hint-bar__message--info todo-hint-bar__message--warn");
    }, 2400);

    $status.data("timeoutId", timeoutId);
  }

  function openFirstTodoInFocusMode() {
    var $firstActive = $(".todo-item")
      .not(".todo-item--completed")
      .find(".todo-item__focus")
      .first();
    var $target = $firstActive.length ? $firstActive : $(".todo-item__focus").first();

    if (!$target.length) {
      setHintStatus("Todoがありません", "warn");
      return;
    }

    setHintStatus("フォーカスモードを開きます", "info");
    $target[0].click();
  }

  // ========================================
  // キーボードショートカット
  // ========================================
  $(document).on("keydown", function (e) {
    var $target = $(e.target);
    var isEditable = $target.is("input, textarea, select, [contenteditable]");

    // Escは編集中でも発動（編集キャンセル用）
    if (e.key === "Escape") {
      var $cancelBtn = $(".todo-item__edit-form").find('a[href*="item/"]');
      if ($cancelBtn.length) {
        e.preventDefault();
        $cancelBtn[0].click();
        return;
      }
      if (isEditable) {
        $target.blur();
        return;
      }
    }

    // 入力中は他のショートカットを無視
    if (isEditable) return;

    // / : 検索欄にフォーカス
    if (e.key === "/" || e.key === "／") {
      e.preventDefault();
      $('input[name="q"]').focus().select();
      return;
    }

    // n : 新規Todo入力欄にフォーカス
    if (e.key === "n" || e.key === "N") {
      e.preventDefault();
      $('.todo-form input[name="description"]').focus();
      return;
    }

    // f : フォーカスモードで最初のTodoを開く
    if (e.key === "f" || e.key === "F") {
      e.preventDefault();
      openFirstTodoInFocusMode();
      return;
    }
  });

  // ========================================
  // 完了トグル時のアニメーション
  // ========================================
  $(document.body).on("htmx:afterSwap", function (e) {
    var $target = $(e.detail.target);

    // Todo行の更新（チェックボックストグル）を検出
    if ($target.attr("id") && $target.attr("id").indexOf("todo-item-") === 0) {
      $target.addClass("todo-item--pop").one("animationend", function () {
        $(this).removeClass("todo-item--pop");
      });
    }
  });

  $(document).on("click", "#focus-first-btn", function (e) {
    e.preventDefault();
    openFirstTodoInFocusMode();
  });

  // ========================================
  // ショートカットヘルプ（コンソール表示）
  // ========================================
  console.log(
    "%c⌨️ Yarukoto ショートカット",
    "font-weight: bold; font-size: 14px;"
  );
  console.log("  / : 検索欄にフォーカス");
  console.log("  n : 新規Todo入力欄にフォーカス");
  console.log("  f : フォーカスモードで最初のTodoを開く");
  console.log("  Esc : 編集キャンセル / フォーカス解除");
})(jQuery);

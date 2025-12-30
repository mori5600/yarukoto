/**
 * Yarukoto - キーボードショートカット & UXエンハンスメント
 *
 * ショートカット:
 *   / : 検索欄にフォーカス
 *   n : 新規Todo入力欄にフォーカス
 *   Esc : 編集モードをキャンセル（編集中の行を元に戻す）
 *
 * アニメーション:
 *   - 完了トグル時に行を軽くポップさせる
 */
(function () {
  "use strict";

  // ========================================
  // キーボードショートカット
  // ========================================
  document.addEventListener("keydown", function (e) {
    // 入力中（input, textarea, select, contenteditable）は無視
    const target = e.target;
    const tagName = target.tagName.toLowerCase();
    const isEditable =
      tagName === "input" ||
      tagName === "textarea" ||
      tagName === "select" ||
      target.isContentEditable;

    // Escは編集中でも発動（編集キャンセル用）
    if (e.key === "Escape") {
      // 編集中のTodo行があればキャンセルボタンをクリック
      const editForm = document.querySelector(".todo-item__edit-form");
      if (editForm) {
        const cancelBtn = editForm.querySelector('a[href*="item/"]');
        if (cancelBtn) {
          e.preventDefault();
          cancelBtn.click();
          return;
        }
      }
      // 入力欄からフォーカスを外す
      if (isEditable) {
        target.blur();
        return;
      }
    }

    // 入力中は他のショートカットを無視
    if (isEditable) return;

    // / : 検索欄にフォーカス
    if (e.key === "/" || e.key === "／") {
      e.preventDefault();
      const searchInput = document.querySelector('input[name="q"]');
      if (searchInput) {
        searchInput.focus();
        searchInput.select();
      }
      return;
    }

    // n : 新規Todo入力欄にフォーカス
    if (e.key === "n" || e.key === "N") {
      e.preventDefault();
      const todoInput = document.querySelector(
        '.todo-form input[name="description"]'
      );
      if (todoInput) {
        todoInput.focus();
      }
      return;
    }
  });

  // ========================================
  // 完了トグル時のアニメーション
  // ========================================
  // HTMXのスワップ後に発火
  document.body.addEventListener("htmx:afterSwap", function (e) {
    const target = e.detail.target;

    // Todo行の更新（チェックボックストグル）を検出
    if (target && target.id && target.id.startsWith("todo-item-")) {
      // ポップアニメーションを付与
      target.classList.add("todo-item--pop");

      // アニメーション終了後にクラスを除去
      target.addEventListener(
        "animationend",
        function () {
          target.classList.remove("todo-item--pop");
        },
        { once: true }
      );
    }
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
  console.log("  Esc : 編集キャンセル / フォーカス解除");
})();

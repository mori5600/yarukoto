/**
 * Focus Mode - フォーカスモード制御とPomodoroタイマー
 */
(function ($) {
  "use strict";

  // ========================================
  // Escキーでフォーカスモード終了
  // ========================================
  $(document).on("keydown", function (e) {
    if (e.key === "Escape" && $("#todo-focus-mode").length) {
      // 編集中の場合はキャンセルボタンをクリック
      if ($(".todo-focus-mode__edit-form").length) {
        $(".todo-focus-mode__edit-form .btn-outline-secondary").click();
      } else {
        // 通常時はフォーカスモードを終了
        e.preventDefault();
        $(".todo-focus-mode__close").click();
      }
    }
  });

  // ========================================
  // Pomodoroタイマー（オプション機能）
  // ========================================
  let timerInterval = null;
  let remainingSeconds = 25 * 60; // 25分
  const POMODORO_DURATION = 25 * 60;

  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }

  function updateTimerDisplay() {
    $("#timer-display").text(formatTime(remainingSeconds));
  }

  function startTimer() {
    if (timerInterval) return;
    $("#timer-start").hide();
    $("#timer-pause").removeClass("todo-focus-mode__timer-pause--hidden");

    timerInterval = setInterval(function () {
      remainingSeconds--;
      updateTimerDisplay();

      if (remainingSeconds <= 0) {
        clearInterval(timerInterval);
        timerInterval = null;
        alert("⏰ Pomodoro終了！お疲れ様でした！");
        $("#timer-start").show();
        $("#timer-pause").addClass("todo-focus-mode__timer-pause--hidden");
        remainingSeconds = POMODORO_DURATION;
        updateTimerDisplay();
      }
    }, 1000);
  }

  function pauseTimer() {
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
      $("#timer-start").show();
      $("#timer-pause").addClass("todo-focus-mode__timer-pause--hidden");
    }
  }

  function resetTimer() {
    pauseTimer();
    remainingSeconds = POMODORO_DURATION;
    updateTimerDisplay();
  }

  $(document).on("click", "#timer-start", startTimer);
  $(document).on("click", "#timer-pause", pauseTimer);
  $(document).on("click", "#timer-reset", resetTimer);

  // ========================================
  // フォーカスモード起動時にタイマーを初期化
  // ========================================
  $(document.body).on("htmx:afterSwap", function (e) {
    if (
      $(e.detail.target).attr("id") === "todo-focus-mode" ||
      (e.detail.target.tagName === "BODY" && $("#todo-focus-mode").length)
    ) {
      resetTimer();
    }
  });
})(jQuery);

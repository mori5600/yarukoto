/**
 * フォーカスモード - UI制御
 * @file focus.js
 * @requires pomodoro-timer.js
 * @requires notification.js
 * @requires jQuery
 */

(function ($) {
  "use strict";

  // ========================================
  // 通知UI
  // ========================================

  /**
   * 通知許可UIを更新
   */
  function updateNotificationPermissionUI() {
    const $status = $("#notification-permission-status");
    const $btn = $("#notification-permission-btn");
    const status = NotificationService.getPermissionStatus();

    // リセット
    $status.removeClass(
      "todo-focus-mode__notification-status--granted " +
        "todo-focus-mode__notification-status--denied " +
        "todo-focus-mode__notification-status--unsupported"
    );

    switch (status) {
      case "unsupported":
        $status
          .text("このブラウザは通知に対応していません")
          .addClass("todo-focus-mode__notification-status--unsupported");
        $btn.hide();
        break;
      case "granted":
        $status
          .text("✅ 通知は許可されています")
          .addClass("todo-focus-mode__notification-status--granted");
        $btn.hide();
        break;
      case "denied":
        $status
          .text(
            "❌ 通知はブロックされています。ブラウザの設定から許可してください。"
          )
          .addClass("todo-focus-mode__notification-status--denied");
        $btn.hide();
        break;
      default:
        $status.text("通知を許可すると、タイマー終了時にお知らせします");
        $btn.show();
    }
  }

  // ========================================
  // 設定パネル
  // ========================================

  /** @type {PomodoroTimer | null} */
  let timer = null;

  function setSettingsPanelState(isOpen) {
    const $panel = $("#timer-settings-panel");
    const $toggle = $("#timer-settings");

    if (isOpen) {
      $panel.removeClass("todo-focus-mode__settings-panel--hidden");
      $panel.attr("aria-hidden", "false");
      $toggle.attr("aria-expanded", "true");
    } else {
      $panel.addClass("todo-focus-mode__settings-panel--hidden");
      $panel.attr("aria-hidden", "true");
      $toggle.attr("aria-expanded", "false");
    }
  }

  function closeSettingsPanel() {
    setSettingsPanelState(false);
  }

  function openSettingsPanel() {
    initSettingsPanel();
    setSettingsPanelState(true);
    $("#timer-work-duration").trigger("focus");
  }

  /**
   * @returns {boolean}
   */
  function isSettingsPanelOpen() {
    return !$("#timer-settings-panel").hasClass(
      "todo-focus-mode__settings-panel--hidden"
    );
  }

  function initSettingsPanel() {
    const settings = timer?.getSettings();
    if (!settings) return;

    $("#timer-work-duration").val(settings.workDuration / 60);
    $("#timer-break-duration").val(settings.breakDuration / 60);
    $("#timer-long-break-duration").val(settings.longBreakDuration / 60);
    $("#timer-sessions-before-long-break").val(
      settings.sessionsBeforeLongBreak
    );
    updateNotificationPermissionUI();
  }

  function saveSettings() {
    const workDuration = parseInt(String($("#timer-work-duration").val()), 10);
    const breakDuration = parseInt(
      String($("#timer-break-duration").val()),
      10
    );
    const longBreakDuration = parseInt(
      String($("#timer-long-break-duration").val()),
      10
    );
    const sessionsBeforeLongBreak = parseInt(
      String($("#timer-sessions-before-long-break").val()),
      10
    );

    if (
      isNaN(workDuration) ||
      workDuration < 1 ||
      workDuration > 120 ||
      isNaN(breakDuration) ||
      breakDuration < 1 ||
      breakDuration > 60 ||
      isNaN(longBreakDuration) ||
      longBreakDuration < 1 ||
      longBreakDuration > 60 ||
      isNaN(sessionsBeforeLongBreak) ||
      sessionsBeforeLongBreak < 1 ||
      sessionsBeforeLongBreak > 10
    ) {
      alert("入力値が不正です。");
      return;
    }

    PomodoroTimer.saveSettings({
      workDuration,
      breakDuration,
      longBreakDuration,
      sessionsBeforeLongBreak,
    });

    timer?.updateSettings({
      workDuration: workDuration * 60,
      breakDuration: breakDuration * 60,
      longBreakDuration: longBreakDuration * 60,
      sessionsBeforeLongBreak,
    });

    closeSettingsPanel();
  }

  // ========================================
  // タイマーUI
  // ========================================

  function updatePhaseIndicator() {
    const state = timer?.getState();
    if (!state) return;

    const $display = $("#timer-display");
    $display.removeClass(
      "todo-focus-mode__timer-work todo-focus-mode__timer-break todo-focus-mode__timer-longbreak"
    );

    switch (state.currentPhase) {
      case "work":
        $display.addClass("todo-focus-mode__timer-work");
        break;
      case "break":
        $display.addClass("todo-focus-mode__timer-break");
        break;
      case "longBreak":
        $display.addClass("todo-focus-mode__timer-longbreak");
        break;
    }
  }

  function initTimer() {
    const settings = PomodoroTimer.loadSettings();
    timer = new PomodoroTimer(settings);

    timer.setHandlers({
      onStart: () => {
        $("#timer-start").hide();
        $("#timer-pause").removeClass("todo-focus-mode__timer-pause--hidden");
        updatePhaseIndicator();
      },
      onPause: () => {
        $("#timer-start").show();
        $("#timer-pause").addClass("todo-focus-mode__timer-pause--hidden");
      },
      onReset: () => {
        $("#timer-start").show();
        $("#timer-pause").addClass("todo-focus-mode__timer-pause--hidden");
        updatePhaseIndicator();
      },
      onTick: (remainingSeconds) => {
        $("#timer-display").text(PomodoroTimer.formatTime(remainingSeconds));
      },
      onPhaseComplete: (phase) => {
        const state = timer?.getState();
        if (phase === "work") {
          const sessions = state?.completedSessions || 0;
          const nextPhase = state?.currentPhase;
          const breakType = nextPhase === "longBreak" ? "長休憩" : "休憩";
          NotificationService.show(
            `🎉 作業セッション ${sessions} 完了！${breakType}をとりましょう。`,
            { title: "Yarukoto - ポモドーロタイマー" }
          );
        } else {
          NotificationService.show("💪 休憩終了！次の作業を始めましょう。", {
            title: "Yarukoto - ポモドーロタイマー",
          });
        }
        updatePhaseIndicator();
      },
    });

    const state = timer.getState();
    $("#timer-display").text(PomodoroTimer.formatTime(state.remainingSeconds));
    updatePhaseIndicator();
    initSettingsPanel();
  }

  // ========================================
  // イベントハンドラ
  // ========================================

  // Escキーでフォーカスモード終了
  $(document).on("keydown", function (e) {
    if (e.key === "Escape" && $("#todo-focus-mode").length) {
      if (isSettingsPanelOpen()) {
        closeSettingsPanel();
        return;
      }
      if ($(".todo-focus-mode__edit-form").length) {
        $(".todo-focus-mode__edit-form .btn-outline-secondary").click();
      } else {
        e.preventDefault();
        $(".todo-focus-mode__close").click();
      }
    }
  });

  // タイマー操作
  $(document).on("click", "#timer-start", () => timer?.start());
  $(document).on("click", "#timer-pause", () => timer?.pause());
  $(document).on("click", "#timer-reset", () => timer?.reset());

  // 設定パネル
  $(document).on("click", "#timer-settings", function () {
    isSettingsPanelOpen() ? closeSettingsPanel() : openSettingsPanel();
  });
  $(document).on("click", "#timer-settings-close", closeSettingsPanel);
  $(document).on("click", "#timer-settings-cancel", function () {
    initSettingsPanel();
    closeSettingsPanel();
  });
  $(document).on("click", "#timer-settings-save", saveSettings);

  // 通知許可
  $(document).on("click", "#notification-permission-btn", async function () {
    const permission = await NotificationService.requestPermission();
    updateNotificationPermissionUI();
    if (permission === "granted") {
      new Notification("Yarukoto", { body: "通知が有効になりました！" });
    }
  });

  // ========================================
  // 初期化
  // ========================================

  $(document.body).on("htmx:afterSwap", function (e) {
    if (
      $(e.detail.target).attr("id") === "todo-focus-mode" ||
      (e.detail.target.tagName === "BODY" && $("#todo-focus-mode").length)
    ) {
      initTimer();
    }
  });

  $(function () {
    if ($("#todo-focus-mode").length) {
      initTimer();
    }
  });
})(jQuery);

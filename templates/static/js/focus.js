/**
 * Focus Mode - フォーカスモード制御とPomodoroタイマー
 * @file focus.js
 */

// ========================================
// 型定義 (JSDoc)
// ========================================

/**
 * ポモドーロタイマーの設定
 * @typedef {Object} PomodoroSettings
 * @property {number} workDuration - 作業時間（秒）
 * @property {number} breakDuration - 休憩時間（秒）
 * @property {number} longBreakDuration - 長休憩時間（秒）
 * @property {number} sessionsBeforeLongBreak - 長休憩までのセッション数
 */

/**
 * ポモドーロタイマーの状態
 * @typedef {Object} PomodoroState
 * @property {number} remainingSeconds - 残り時間（秒）
 * @property {number} completedSessions - 完了したセッション数
 * @property {PomodoroPhase} currentPhase - 現在のフェーズ
 * @property {boolean} isRunning - タイマーが実行中かどうか
 */

/**
 * ポモドーロのフェーズ
 * @typedef {'work' | 'break' | 'longBreak'} PomodoroPhase
 */

/**
 * ポモドーロタイマーのイベントハンドラ
 * @typedef {Object} PomodoroEventHandlers
 * @property {function(): void} onStart - タイマー開始時
 * @property {function(): void} onPause - タイマー一時停止時
 * @property {function(): void} onReset - タイマーリセット時
 * @property {function(PomodoroPhase): void} onPhaseComplete - フェーズ完了時
 * @property {function(number): void} onTick - 毎秒のコールバック
 */

/**
 * ポモドーロタイマークラス
 */
class PomodoroTimer {
  /** @type {PomodoroSettings} */
  #settings;

  /** @type {PomodoroState} */
  #state;

  /** @type {number | null} */
  #intervalId = null;

  /** @type {Partial<PomodoroEventHandlers>} */
  #handlers = {};

  /** @type {string} */
  static STORAGE_KEY = "yarukoto_pomodoro_settings";

  /**
   * デフォルト設定
   * @type {PomodoroSettings}
   */
  static DEFAULT_SETTINGS = {
    workDuration: 25 * 60,
    breakDuration: 5 * 60,
    longBreakDuration: 15 * 60,
    sessionsBeforeLongBreak: 4,
  };

  /**
   * @param {Partial<PomodoroSettings>} [settings]
   */
  constructor(settings) {
    this.#settings = { ...PomodoroTimer.DEFAULT_SETTINGS, ...settings };
    this.#state = this.#createInitialState();
  }

  /**
   * 初期状態を作成
   * @returns {PomodoroState}
   */
  #createInitialState() {
    return {
      remainingSeconds: this.#settings.workDuration,
      completedSessions: 0,
      currentPhase: "work",
      isRunning: false,
    };
  }

  /**
   * ローカルストレージから設定を読み込む
   * @returns {PomodoroSettings}
   */
  static loadSettings() {
    try {
      const saved = localStorage.getItem(PomodoroTimer.STORAGE_KEY);
      if (saved) {
        const parsed = JSON.parse(saved);
        return {
          workDuration: (parsed.workDuration || 25) * 60,
          breakDuration: (parsed.breakDuration || 5) * 60,
          longBreakDuration: (parsed.longBreakDuration || 15) * 60,
          sessionsBeforeLongBreak: parsed.sessionsBeforeLongBreak || 4,
        };
      }
    } catch (e) {
      console.warn("Failed to load pomodoro settings:", e);
    }
    return PomodoroTimer.DEFAULT_SETTINGS;
  }

  /**
   * 設定をローカルストレージに保存
   * @param {Object} settingsInMinutes - 分単位の設定
   * @param {number} settingsInMinutes.workDuration - 作業時間（分）
   * @param {number} settingsInMinutes.breakDuration - 休憩時間（分）
   * @param {number} settingsInMinutes.longBreakDuration - 長休憩時間（分）
   * @param {number} settingsInMinutes.sessionsBeforeLongBreak - 長休憩までのセッション数
   */
  static saveSettings(settingsInMinutes) {
    try {
      localStorage.setItem(
        PomodoroTimer.STORAGE_KEY,
        JSON.stringify(settingsInMinutes)
      );
    } catch (e) {
      console.warn("Failed to save pomodoro settings:", e);
    }
  }

  /**
   * イベントハンドラを設定
   * @param {Partial<PomodoroEventHandlers>} handlers
   */
  setHandlers(handlers) {
    this.#handlers = { ...this.#handlers, ...handlers };
  }

  /**
   * 設定を更新
   * @param {Partial<PomodoroSettings>} newSettings
   */
  updateSettings(newSettings) {
    this.#settings = { ...this.#settings, ...newSettings };
    this.reset();
  }

  /**
   * 現在の設定を取得
   * @returns {PomodoroSettings}
   */
  getSettings() {
    return { ...this.#settings };
  }

  /**
   * 現在の状態を取得
   * @returns {PomodoroState}
   */
  getState() {
    return { ...this.#state };
  }

  /**
   * 時間をフォーマット
   * @param {number} seconds
   * @returns {string}
   */
  static formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
  }

  /**
   * タイマーを開始
   */
  start() {
    if (this.#intervalId !== null) return;

    this.#state.isRunning = true;
    this.#handlers.onStart?.();

    this.#intervalId = window.setInterval(() => {
      this.#state.remainingSeconds--;
      this.#handlers.onTick?.(this.#state.remainingSeconds);

      if (this.#state.remainingSeconds <= 0) {
        this.#completePhase();
      }
    }, 1000);
  }

  /**
   * タイマーを一時停止
   */
  pause() {
    if (this.#intervalId !== null) {
      window.clearInterval(this.#intervalId);
      this.#intervalId = null;
    }
    this.#state.isRunning = false;
    this.#handlers.onPause?.();
  }

  /**
   * タイマーをリセット
   */
  reset() {
    this.pause();
    this.#state = this.#createInitialState();
    this.#handlers.onReset?.();
    this.#handlers.onTick?.(this.#state.remainingSeconds);
  }

  /**
   * フェーズ完了処理
   */
  #completePhase() {
    this.pause();
    const completedPhase = this.#state.currentPhase;
    this.#handlers.onPhaseComplete?.(completedPhase);

    if (completedPhase === "work") {
      this.#state.completedSessions++;

      if (
        this.#state.completedSessions %
          this.#settings.sessionsBeforeLongBreak ===
        0
      ) {
        this.#state.currentPhase = "longBreak";
        this.#state.remainingSeconds = this.#settings.longBreakDuration;
      } else {
        this.#state.currentPhase = "break";
        this.#state.remainingSeconds = this.#settings.breakDuration;
      }
    } else {
      this.#state.currentPhase = "work";
      this.#state.remainingSeconds = this.#settings.workDuration;
    }

    this.#handlers.onTick?.(this.#state.remainingSeconds);
  }

  /**
   * 現在のフェーズをスキップ
   */
  skipPhase() {
    this.#completePhase();
  }
}

// ========================================
// jQuery プラグインとして初期化
// ========================================
(function ($) {
  "use strict";

  /** @type {PomodoroTimer | null} */
  let timer = null;

  /**
   * タイマーを初期化
   */
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
          showNotification(
            `🎉 作業セッション ${sessions} 完了！${breakType}をとりましょう。`
          );
        } else {
          showNotification("💪 休憩終了！次の作業を始めましょう。");
        }
        updatePhaseIndicator();
      },
    });

    // 初期表示を更新
    const state = timer.getState();
    $("#timer-display").text(PomodoroTimer.formatTime(state.remainingSeconds));
    updatePhaseIndicator();

    // 設定パネルの値を初期化
    initSettingsPanel();
  }

  /**
   * フェーズインジケーターを更新
   */
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

  /**
   * 通知を表示
   * @param {string} message
   */
  function showNotification(message) {
    // ブラウザ通知が許可されていれば使用
    if (Notification.permission === "granted") {
      new Notification("Yarukoto - ポモドーロタイマー", { body: message });
    } else if (Notification.permission !== "denied") {
      Notification.requestPermission().then((permission) => {
        if (permission === "granted") {
          new Notification("Yarukoto - ポモドーロタイマー", { body: message });
        } else {
          alert(message);
        }
      });
    } else {
      alert(message);
    }

    // 音を鳴らす（オプション）
    try {
      const audioContext = new (window.AudioContext ||
        /** @type {typeof AudioContext} */ (
          /** @type {any} */ (window).webkitAudioContext
        ))();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.frequency.value = 800;
      oscillator.type = "sine";
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(
        0.01,
        audioContext.currentTime + 0.5
      );

      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.5);
    } catch (e) {
      // 音声再生に失敗しても続行
    }
  }

  /**
   * 設定パネルを初期化
   */
  function initSettingsPanel() {
    const settings = timer?.getSettings();
    if (!settings) return;

    $("#timer-work-duration").val(settings.workDuration / 60);
    $("#timer-break-duration").val(settings.breakDuration / 60);
    $("#timer-long-break-duration").val(settings.longBreakDuration / 60);
    $("#timer-sessions-before-long-break").val(
      settings.sessionsBeforeLongBreak
    );
  }

  // ========================================
  // イベントハンドラ
  // ========================================

  /**
   * 設定パネルを閉じる
   */
  function closeSettingsPanel() {
    $("#timer-settings-panel").hide();
  }

  /**
   * 設定パネルを開く
   */
  function openSettingsPanel() {
    $("#timer-settings-panel").show();
  }

  /**
   * 設定パネルが開いているかどうか
   * @returns {boolean}
   */
  function isSettingsPanelOpen() {
    return $("#timer-settings-panel").is(":visible");
  }

  // Escキーでフォーカスモード終了
  $(document).on("keydown", function (e) {
    if (e.key === "Escape" && $("#todo-focus-mode").length) {
      // 設定パネルが開いていれば閉じる
      if (isSettingsPanelOpen()) {
        closeSettingsPanel();
        return;
      }
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

  // タイマー操作
  $(document).on("click", "#timer-start", () => timer?.start());
  $(document).on("click", "#timer-pause", () => timer?.pause());
  $(document).on("click", "#timer-reset", () => timer?.reset());

  // 設定パネルの表示/非表示
  $(document).on("click", "#timer-settings", function () {
    if (isSettingsPanelOpen()) {
      closeSettingsPanel();
    } else {
      openSettingsPanel();
    }
  });

  // 設定パネルの閉じるボタン
  $(document).on("click", "#timer-settings-close", closeSettingsPanel);
  $(document).on("click", "#timer-settings-cancel", function () {
    initSettingsPanel();
    closeSettingsPanel();
  });

  // 設定を保存
  $(document).on("click", "#timer-settings-save", function () {
    const workDuration = parseInt(
      /** @type {string} */ ($("#timer-work-duration").val()),
      10
    );
    const breakDuration = parseInt(
      /** @type {string} */ ($("#timer-break-duration").val()),
      10
    );
    const longBreakDuration = parseInt(
      /** @type {string} */ ($("#timer-long-break-duration").val()),
      10
    );
    const sessionsBeforeLongBreak = parseInt(
      /** @type {string} */ ($("#timer-sessions-before-long-break").val()),
      10
    );

    // バリデーション
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

    // 設定を保存
    PomodoroTimer.saveSettings({
      workDuration,
      breakDuration,
      longBreakDuration,
      sessionsBeforeLongBreak,
    });

    // タイマーを更新
    timer?.updateSettings({
      workDuration: workDuration * 60,
      breakDuration: breakDuration * 60,
      longBreakDuration: longBreakDuration * 60,
      sessionsBeforeLongBreak,
    });

    // パネルを閉じる
    closeSettingsPanel();
  });

  // ========================================
  // フォーカスモード起動時にタイマーを初期化
  // ========================================
  $(document.body).on("htmx:afterSwap", function (e) {
    if (
      $(e.detail.target).attr("id") === "todo-focus-mode" ||
      (e.detail.target.tagName === "BODY" && $("#todo-focus-mode").length)
    ) {
      initTimer();
    }
  });

  // 初期ロード時にフォーカスモードが存在すれば初期化
  $(function () {
    if ($("#todo-focus-mode").length) {
      initTimer();
    }
  });
})(jQuery);

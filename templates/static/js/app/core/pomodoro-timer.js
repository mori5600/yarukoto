/**
 * ポモドーロタイマー - コアロジック
 * @file pomodoro-timer.js
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
 * @property {function(): void} [onStart] - タイマー開始時
 * @property {function(): void} [onPause] - タイマー一時停止時
 * @property {function(): void} [onReset] - タイマーリセット時
 * @property {function(PomodoroPhase): void} [onPhaseComplete] - フェーズ完了時
 * @property {function(number): void} [onTick] - 毎秒のコールバック
 */

/**
 * 分単位の設定（保存用）
 * @typedef {Object} PomodoroSettingsInMinutes
 * @property {number} workDuration - 作業時間（分）
 * @property {number} breakDuration - 休憩時間（分）
 * @property {number} longBreakDuration - 長休憩時間（分）
 * @property {number} sessionsBeforeLongBreak - 長休憩までのセッション数
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
   * @param {PomodoroSettingsInMinutes} settingsInMinutes - 分単位の設定
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

// グローバルに公開
window.PomodoroTimer = PomodoroTimer;

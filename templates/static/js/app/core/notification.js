/**
 * 通知サービス - ブラウザ通知と音声再生
 * @file notification.js
 */

// ========================================
// 型定義 (JSDoc)
// ========================================

/**
 * 通知の許可状態
 * @typedef {'granted' | 'denied' | 'default' | 'unsupported'} NotificationPermissionStatus
 */

/**
 * 通知オプション
 * @typedef {Object} NotificationOptions
 * @property {string} [title] - 通知タイトル
 * @property {boolean} [playSound] - 音を鳴らすか
 */

/**
 * 通知サービス
 * ブラウザ通知と音声再生を担当
 */
const NotificationService = {
  /** @type {string} */
  defaultTitle: "Yarukoto",

  /**
   * ブラウザが通知をサポートしているか
   * @returns {boolean}
   */
  isSupported() {
    return "Notification" in window;
  },

  /**
   * 現在の許可状態を取得
   * @returns {NotificationPermissionStatus}
   */
  getPermissionStatus() {
    if (!this.isSupported()) {
      return "unsupported";
    }
    return Notification.permission;
  },

  /**
   * 通知許可をリクエスト
   * @returns {Promise<NotificationPermissionStatus>}
   */
  async requestPermission() {
    if (!this.isSupported()) {
      return "unsupported";
    }
    const permission = await Notification.requestPermission();
    return permission;
  },

  /**
   * 通知を表示
   * @param {string} message - 通知本文
   * @param {NotificationOptions} [options] - オプション
   * @returns {Promise<boolean>} - 通知が表示されたかどうか
   */
  async show(message, options = {}) {
    const { title = this.defaultTitle, playSound = true } = options;

    if (playSound) {
      this.playSound();
    }

    const status = this.getPermissionStatus();

    if (status === "granted") {
      new Notification(title, { body: message });
      return true;
    }

    if (status === "default") {
      const permission = await this.requestPermission();
      if (permission === "granted") {
        new Notification(title, { body: message });
        return true;
      }
    }

    // 通知が使えない場合はalertにフォールバック
    alert(message);
    return false;
  },

  /**
   * 通知音を再生
   */
  playSound() {
    try {
      const AudioContextClass =
        window.AudioContext ||
        /** @type {typeof AudioContext} */ (
          /** @type {any} */ (window).webkitAudioContext
        );
      const audioContext = new AudioContextClass();
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
      console.warn(
        "[NotificationService] 通知音の再生に失敗しました:",
        e instanceof Error ? e.message : "不明なエラー"
      );
    }
  },
};

// グローバルに公開
window.NotificationService = NotificationService;

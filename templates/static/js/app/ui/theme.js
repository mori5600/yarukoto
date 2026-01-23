/**
 * テーマ切り替え機能
 * - OS依存（デフォルト）
 * - ライトモード
 * - ダークモード
 */

class ThemeManager {
  constructor() {
    this.STORAGE_KEY = "app-theme-preference";
    this.THEME_LIGHT = "light";
    this.THEME_DARK = "dark";
    this.THEME_AUTO = "auto";
    this.init();
  }

  /**
   * 初期化：保存されたテーマ設定を復元、またはOSデフォルトを使用
   */
  init() {
    const saved = this.getSavedTheme();
    const theme = saved || this.THEME_AUTO;
    this.setTheme(theme);
  }

  /**
   * LocalStorageから保存されたテーマ設定を取得
   */
  getSavedTheme() {
    return localStorage.getItem(this.STORAGE_KEY);
  }

  /**
   * 現在のアクティブなテーマを取得（実際に適用されているもの）
   */
  getActiveTheme() {
    const theme = this.getSavedTheme() || this.THEME_AUTO;
    if (theme === this.THEME_AUTO) {
      return this.getOSTheme();
    }
    return theme;
  }

  /**
   * OSのカラースキーム設定を取得
   */
  getOSTheme() {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? this.THEME_DARK
      : this.THEME_LIGHT;
  }

  /**
   * テーマを設定
   */
  setTheme(theme) {
    localStorage.setItem(this.STORAGE_KEY, theme);
    this.applyTheme(theme);
    this.updateMenuState();
  }

  /**
   * テーマをDOMに適用
   */
  applyTheme(theme) {
    const html = document.documentElement;
    const body = document.body;
    const bsTheme = theme === this.THEME_AUTO ? this.getOSTheme() : theme;

    if (theme === this.THEME_AUTO) {
      html.removeAttribute("data-theme");
      html.style.colorScheme = "light dark";
    } else if (theme === this.THEME_LIGHT) {
      html.setAttribute("data-theme", this.THEME_LIGHT);
      html.style.colorScheme = "light";
    } else if (theme === this.THEME_DARK) {
      html.setAttribute("data-theme", this.THEME_DARK);
      html.style.colorScheme = "dark";
    }

    html.setAttribute("data-bs-theme", bsTheme);
    if (body) {
      body.setAttribute("data-bs-theme", bsTheme);
    }
  }

  /**
   * メニューの表示状態を更新
   */
  updateMenuState() {
    const button = document.getElementById("theme-toggle-btn");
    if (!button) return;

    const current = this.getSavedTheme() || this.THEME_AUTO;
    const icon = button.querySelector(".theme-icon");

    let newIcon = "🌐";

    if (current === this.THEME_LIGHT) {
      newIcon = "☀️";
    } else if (current === this.THEME_DARK) {
      newIcon = "🌙";
    }

    if (icon) {
      icon.textContent = newIcon;
    }

    // メニュー項目の選択状態を更新
    const menuItems = document.querySelectorAll(".theme-option");
    menuItems.forEach((item) => {
      if (item.getAttribute("data-theme") === current) {
        item.classList.add("active");
      } else {
        item.classList.remove("active");
      }
    });
  }

  /**
   * OS設定の変更を監視
   */
  watchOSThemeChange() {
    if (!window.matchMedia) return;

    const darkModeQuery = window.matchMedia("(prefers-color-scheme: dark)");
    darkModeQuery.addEventListener("change", () => {
      const saved = this.getSavedTheme();
      if (saved === this.THEME_AUTO || !saved) {
        this.applyTheme(this.THEME_AUTO);
        this.updateMenuState();
      }
    });
  }
}

// グローバルインスタンスを作成
const themeManager = new ThemeManager();

// OSのテーマ変更を監視
themeManager.watchOSThemeChange();

// メニュー項目のイベントリスナー設定（DOMロード後に実行）
document.addEventListener("DOMContentLoaded", () => {
  const themeOptions = document.querySelectorAll(".theme-option");
  themeOptions.forEach((option) => {
    option.addEventListener("click", (e) => {
      e.preventDefault();
      const theme = option.getAttribute("data-theme");
      themeManager.setTheme(theme);
    });
  });
});

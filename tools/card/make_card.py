#!/usr/bin/env python3
"""投稿カード画像（1200×675）を template.html から生成する。

使い方は同ディレクトリの README.md を参照。

実測値（--before-sec / --after-sec）は必須です。カードはワークフロー上、
実機検証を終えてから作るものなので、数値が無い状態では生成できません。
"""

import argparse
import html
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATE = HERE / "template.html"
CHROME = Path("/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
FONT_DIR = HERE / "node_modules/@fontsource/noto-sans-jp"

# 長いほうのバーの幅。README のバー幅ルールと一致させること
MAX_BAR = 560
MIN_BAR = 20

PILLARS = {
    "shortcut": "①ショートカット・時短Tips + ②Before/After",
    "verify": "③検証ログ",
    "light": "④地味だけど効くTips + ⑤あるある・小ネタ",
}


def bar_widths(before_sec: float, after_sec: float) -> tuple[int, int]:
    """実測値に厳密比例させた2本のバー幅を返す。長いほうが MAX_BAR。"""
    longest = max(before_sec, after_sec)
    if longest <= 0:
        sys.exit("エラー: 秒数は0より大きい値を指定してください")
    scale = MAX_BAR / longest
    return (
        max(MIN_BAR, round(before_sec * scale)),
        max(MIN_BAR, round(after_sec * scale)),
    )


def fmt_sec(v: float) -> str:
    return f"{int(v)}秒" if float(v).is_integer() else f"{v}秒"


def ensure_fonts() -> None:
    if FONT_DIR.is_dir():
        return
    print("Noto Sans JP が無いので取得します…", file=sys.stderr)
    r = subprocess.run(
        ["npm", "install", "@fontsource/noto-sans-jp", "--no-audit", "--no-fund"],
        cwd=HERE, capture_output=True, text=True,
    )
    if not FONT_DIR.is_dir():
        sys.exit(f"エラー: フォントを取得できませんでした\n{r.stderr[-500:]}")


def build_html(a: argparse.Namespace) -> Path:
    src = TEMPLATE.read_text(encoding="utf-8")
    bw, aw = bar_widths(a.before_sec, a.after_sec)
    e = html.escape

    head_line2 = f'<em>{e(a.headline2)}</em>' if a.headline2 else ""
    headline = e(a.headline1) + (f"<br>{head_line2}" if head_line2 else "")

    subs = [
        ('<body data-pillar="shortcut">', f'<body data-pillar="{a.pillar}">'),
        ('<div class="pill">PowerPoint 時短Tips</div>', f'<div class="pill">{e(a.label)}</div>'),
        ('<div class="no">#01</div>', f'<div class="no">{e(a.no)}</div>'),
        ('<div class="key">F4</div>', f'<div class="key">{e(a.key)}</div>'),
        ('<div class="headline">直前の操作を、<br><em>もう一度</em></div>',
         f'<div class="headline">{headline}</div>'),
        ('<div class="name">リボンから毎回変更</div>', f'<div class="name">{e(a.before_name)}</div>'),
        ('<div class="bar" style="width:560px"></div>', f'<div class="bar" style="width:{bw}px"></div>'),
        ('<div class="val">12秒</div>', f'<div class="val">{fmt_sec(a.before_sec)}</div>'),
        ('<div class="name">F4 を押すだけ</div>', f'<div class="name">{e(a.after_name)}</div>'),
        ('<div class="bar" style="width:93px"></div>', f'<div class="bar" style="width:{aw}px"></div>'),
        ('<div class="val">2秒</div>', f'<div class="val">{fmt_sec(a.after_sec)}</div>'),
        ('<div>図形10個の色を変える場合</div>', f'<div>{e(a.note)}</div>'),
        ('<div class="acct">@your_account</div>', f'<div class="acct">{e(a.account)}</div>'),
    ]
    for old, new in subs:
        if old not in src:
            sys.exit(f"エラー: template.html に想定の記述が見つかりません:\n  {old}")
        src = src.replace(old, new, 1)

    # フォントの相対パスを保つため、テンプレートと同じ階層に書き出す
    out = HERE / "_build.html"
    out.write_text(src, encoding="utf-8")
    return out


def render(html_path: Path, out: Path, scale: int) -> None:
    if not CHROME.exists():
        sys.exit(f"エラー: Chromium が見つかりません: {CHROME}")
    subprocess.run(
        [str(CHROME), "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
         f"--force-device-scale-factor={scale}", "--window-size=1200,675",
         f"--screenshot={out}", str(html_path)],
        capture_output=True, text=True, timeout=180,
    )
    if not out.exists():
        sys.exit("エラー: 画像の書き出しに失敗しました")


def main() -> None:
    p = argparse.ArgumentParser(description="投稿カード画像を生成する")
    p.add_argument("--pillar", required=True, choices=sorted(PILLARS),
                   help="柱に対応する配色")
    p.add_argument("--label", required=True, help="ピルのラベル（例: PowerPoint 時短Tips）")
    p.add_argument("--no", required=True, help="テーマ番号（例: #01）")
    p.add_argument("--key", required=True, help="キー・機能名（例: F4）")
    p.add_argument("--headline1", required=True, help="見出し1行目")
    p.add_argument("--headline2", default="", help="見出し2行目（アクセント色になる）")
    p.add_argument("--before-name", required=True, help="Before の操作名")
    p.add_argument("--before-sec", required=True, type=float, help="Before の実測秒数")
    p.add_argument("--after-name", required=True, help="After の操作名")
    p.add_argument("--after-sec", required=True, type=float, help="After の実測秒数")
    p.add_argument("--note", required=True, help="計測条件（例: 図形10個の色を変える場合）")
    p.add_argument("--account", default="@your_account", help="アカウント名")
    p.add_argument("--out", default="card.png", help="出力先PNG")
    p.add_argument("--scale", type=int, default=1, choices=[1, 2],
                   help="2 で 2400×1350 の高解像度")
    a = p.parse_args()

    ensure_fonts()
    out = Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    render(build_html(a), out, a.scale)

    bw, aw = bar_widths(a.before_sec, a.after_sec)
    ratio = a.before_sec / a.after_sec if a.after_sec else 0
    print(f"生成: {out}")
    print(f"  柱     : {a.pillar}（{PILLARS[a.pillar]}）")
    print(f"  バー幅 : before {bw}px / after {aw}px（比 {ratio:.1f}:1）")


if __name__ == "__main__":
    main()

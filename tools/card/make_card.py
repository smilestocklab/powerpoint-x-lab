#!/usr/bin/env python3
"""投稿カード画像（1200×675）をテンプレートから生成する。

2種類のレイアウトがある。使い方は同ディレクトリの README.md を参照。

  timing … Before/Afterの時短比較。柱①〜④向け（既定）
  quip   … ふきだし型。時短の数字が無い柱⑤「あるある・小ネタ」向け

timing の実測値（--before-sec / --after-sec）は必須。カードはワークフロー上、
実機検証を終えてから作るものなので、数値が無い状態では生成できない。
"""

import argparse
import html
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEMPLATES = {"timing": HERE / "template.html", "quip": HERE / "template-quip.html"}
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


def apply(src: str, subs: list[tuple[str, str]]) -> str:
    for old, new in subs:
        if old not in src:
            sys.exit(f"エラー: テンプレートに想定の記述が見つかりません:\n  {old}")
        src = src.replace(old, new, 1)
    return src


def build_timing(a: argparse.Namespace) -> str:
    e = html.escape
    bw, aw = bar_widths(a.before_sec, a.after_sec)
    head2 = f'<em>{e(a.headline2)}</em>' if a.headline2 else ""
    headline = e(a.headline1) + (f"<br>{head2}" if head2 else "")
    return apply(TEMPLATES["timing"].read_text(encoding="utf-8"), [
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
    ])


def build_quip(a: argparse.Namespace) -> str:
    e = html.escape
    lines = [l for l in (a.line1, a.line2, a.line3) if l]
    # 既定では最終行がアクセント色（オチの部分を目立たせる）
    idx = (a.accent_line or len(lines)) - 1
    if not 0 <= idx < len(lines):
        sys.exit(f"エラー: --accent-line は 1〜{len(lines)} で指定してください")
    body = "<br>\n    ".join(
        f"<em>{e(l)}</em>" if i == idx else e(l) for i, l in enumerate(lines)
    )
    return apply(TEMPLATES["quip"].read_text(encoding="utf-8"), [
        ('<body data-pillar="light">', f'<body data-pillar="{a.pillar}">'),
        ('<div class="pill">資料作成あるある</div>', f'<div class="pill">{e(a.label)}</div>'),
        ('<div class="no">#20</div>', f'<div class="no">{e(a.no)}</div>'),
        ("""自分のPCでは完璧だったのに、<br>
    先方のPCで開いた瞬間<br>
    <em>フォントが全部変わってる</em>""", body),
        ('<div class="punch">分かる方、そっと「いいね」を押していってください。</div>',
         f'<div class="punch">{e(a.punch)}</div>' if a.punch else '<div class="punch"></div>'),
        ('<div class="acct">@your_account</div>', f'<div class="acct">{e(a.account)}</div>'),
    ])


def render(html_src: str, out: Path, scale: int) -> None:
    if not CHROME.exists():
        sys.exit(f"エラー: Chromium が見つかりません: {CHROME}")
    # フォントの相対パスを保つため、テンプレートと同じ階層に書き出す
    tmp = HERE / "_build.html"
    tmp.write_text(html_src, encoding="utf-8")
    subprocess.run(
        [str(CHROME), "--headless", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
         f"--force-device-scale-factor={scale}", "--window-size=1200,675",
         f"--screenshot={out}", str(tmp)],
        capture_output=True, text=True, timeout=180,
    )
    if not out.exists():
        sys.exit("エラー: 画像の書き出しに失敗しました")


def main() -> None:
    p = argparse.ArgumentParser(description="投稿カード画像を生成する")
    p.add_argument("--layout", default="timing", choices=sorted(TEMPLATES),
                   help="timing=時短比較（既定） / quip=ふきだし型（あるある向け）")
    p.add_argument("--pillar", required=True, choices=sorted(PILLARS), help="柱に対応する配色")
    p.add_argument("--label", required=True, help="ピルのラベル")
    p.add_argument("--no", required=True, help="テーマ番号（例: #01）")
    p.add_argument("--account", default="@your_account", help="アカウント名")
    p.add_argument("--out", default="card.png", help="出力先PNG")
    p.add_argument("--scale", type=int, default=1, choices=[1, 2], help="2 で2400×1350")

    t = p.add_argument_group("timing レイアウト")
    t.add_argument("--key", help="キー・機能名（例: F4）")
    t.add_argument("--headline1", help="見出し1行目")
    t.add_argument("--headline2", default="", help="見出し2行目（アクセント色）")
    t.add_argument("--before-name", help="Before の操作名")
    t.add_argument("--before-sec", type=float, help="Before の実測秒数")
    t.add_argument("--after-name", help="After の操作名")
    t.add_argument("--after-sec", type=float, help="After の実測秒数")
    t.add_argument("--note", help="計測条件")

    q = p.add_argument_group("quip レイアウト")
    q.add_argument("--line1", help="ふきだし1行目")
    q.add_argument("--line2", default="", help="ふきだし2行目")
    q.add_argument("--line3", default="", help="ふきだし3行目")
    q.add_argument("--accent-line", type=int, help="アクセント色にする行（既定は最終行）")
    q.add_argument("--punch", default="", help="ふきだし下の一言")

    a = p.parse_args()

    required = {
        "timing": ["key", "headline1", "before_name", "before_sec", "after_name", "after_sec", "note"],
        "quip": ["line1"],
    }[a.layout]
    missing = [f"--{n.replace('_', '-')}" for n in required if getattr(a, n) in (None, "")]
    if missing:
        p.error(f"{a.layout} レイアウトには次が必要です: {', '.join(missing)}")

    ensure_fonts()
    out = Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    render(build_timing(a) if a.layout == "timing" else build_quip(a), out, a.scale)

    print(f"生成: {out}")
    print(f"  レイアウト: {a.layout}")
    print(f"  柱        : {a.pillar}（{PILLARS[a.pillar]}）")
    if a.layout == "timing":
        bw, aw = bar_widths(a.before_sec, a.after_sec)
        print(f"  バー幅    : before {bw}px / after {aw}px（比 {a.before_sec / a.after_sec:.1f}:1）")


if __name__ == "__main__":
    main()

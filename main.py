#!/usr/bin/env python3
"""SNS / Display banner ad generator powered by Claude + gpt-image-1."""

import os
import sys
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from agent import generate_banner_prompts
from image_gen import generate_image
from platforms import save_all_platforms, PLATFORMS


def _check_env():
    missing = [k for k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY") if not os.getenv(k)]
    if missing:
        print(f"エラー: 環境変数が未設定です: {', '.join(missing)}")
        print("  .env ファイルを作成して API キーを設定してください（.env.example 参照）")
        sys.exit(1)


def _ask(label: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    value = input(f"  {label}{hint}: ").strip()
    if not value and default:
        return default
    while not value:
        value = input(f"  {label} (必須): ").strip()
    return value


def main():
    _check_env()

    print("\n" + "=" * 55)
    print("  SNS Banner Ad Generator  |  Claude + gpt-image-1")
    print("=" * 55)
    print("\n【キャンペーン情報を入力してください】\n")

    brand_name      = _ask("ブランド名")
    product         = _ask("商品・サービス")
    message         = _ask("キャッチコピー / 訴求メッセージ")
    target_audience = _ask("ターゲット層", "20〜40代のビジネスパーソン")
    style           = _ask("ビジュアルスタイル", "モダン・プロフェッショナル")
    num_str         = _ask("A/Bバリエーション数", "3")

    try:
        num_variations = max(1, min(int(num_str), 5))
    except ValueError:
        num_variations = 3

    safe_brand = "".join(c if c.isalnum() or c in "-_" else "_" for c in brand_name)
    output_dir = f"output/{safe_brand}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    platform_list = ", ".join(f"{p.width}x{p.height}" for p in PLATFORMS)
    print(f"\n対象プラットフォーム: {platform_list}")
    print(f"バリエーション数: {num_variations}")
    print(f"出力先: {Path(output_dir).resolve()}\n")

    # ── Step 1: プロンプト生成 ──────────────────────────
    print("【Step 1/3】Claude がクリエイティブプロンプトを生成中...")
    variations = generate_banner_prompts(
        brand_name=brand_name,
        product=product,
        message=message,
        tonmana=style,
        target_audience=target_audience,
        num_variations=num_variations,
    )
    print(f"  ✓ {len(variations)} バリエーション生成完了\n")
    for v in variations:
        print(f"  [{v['variation']}] {v['label']}")
        print(f"      {v['rationale']}\n")

    # ── Step 2: 画像生成 ────────────────────────────────
    print("【Step 2/3】gpt-image-1 で画像を生成中...\n")
    results = []
    for i, v in enumerate(variations):
        label = f"variation_{v['variation']}_{v['label'].replace(' ', '_')}"
        print(f"  [{v['variation']}] {v['label']} ({i + 1}/{len(variations)})")
        img = generate_image(v["prompt"])
        files = save_all_platforms(img, label, output_dir)
        results.append((v, files))
        print(f"  ✓ {len(files)} サイズ保存完了\n")

    # ── Step 3: サマリー ────────────────────────────────
    print("【Step 3/3】完了！\n")
    print(f"出力先: {Path(output_dir).resolve()}\n")
    print("生成ファイル一覧:")
    for v, files in results:
        print(f"\n  [{v['variation']}] {v['label']}")
        for platform_name, fpath in files:
            print(f"    {platform_name:<25} {Path(fpath).name}")

    print(f"\n合計 {sum(len(f) for _, f in results)} ファイルを生成しました。")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n中断しました")
        sys.exit(0)
    except Exception as e:
        print(f"\nエラー: {e}")
        sys.exit(1)

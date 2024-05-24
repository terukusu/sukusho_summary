"""
sample.py - コマンドラインから SukushoSummary を利用するためのスクリプト

概要:
このスクリプトは、ウェブサイトのスクリーンショットを撮り、そのデータを AI モデルに送信するプロセスを
コマンドラインから実行できるようにするためのものです。
使用するためには環境変数 OPENAI_API_KEY に OpenAI API キーを設定する必要があります。

使用法:
以下のようにコマンドラインから実行します。

    python sample.py --url "https://example.com" --prompt "AIへのプロンプト" --finder-type "xpath" --finder-value "//div[@id='example']" --margin-top 10 --margin-left 10 --margin-right 10 --margin-bottom 10 --ocr-mode --window-width 1024 --window-height 768 --zoom 1.25 --device-emulation "iPhone X"

オプション:
    --url (str): スクリーンショットを撮るウェブサイトのURL (必須)
    --prompt (str): AIモデルに送信するプロンプト (デフォルト: 'デフォルトプロンプト')
    --finder-type (str): 特定の要素を見つけるためのファインダータイプ ('xpath', 'string', 'id', 'css' のいずれか)
    --finder-value (str): ファインダーに使用する値
    --margin-top (int): 要素の上側のマージン (デフォルト: 0)
    --margin-left (int): 要素の左側のマージン (デフォルト: 0)
    --margin-right (int): 要素の右側のマージン (デフォルト: 0)
    --margin-bottom (int): 要素の下側のマージン (デフォルト: 0)
    --ocr-mode (bool): OCRモードを使用するかどうか (デフォルト: False)
    --window-width (int): ウィンドウの幅 (デフォルト: 1280)
    --window-height (int): ウィンドウの高さ (デフォルト: 800)
    --zoom (float): ウェブページのズームレベル (デフォルト: 1.0)
    --device-emulation (str): デバイスエミュレーションの名前 (例: 'iPhone X')

例:
    python sample.py --url "https://example.com" --prompt "AIへのプロンプト" --finder-type "xpath" --finder-value "//div[@id='example']"
"""

import argparse
import logging
from sukusho_summary import SukushoSummary, XpathFinder, StringFinder, IdFinder, CssFinder, ElementNotFoundError


def main():
    parser = argparse.ArgumentParser(description='SukushoSummary CLI')
    parser.add_argument('--url', required=True, help='スクリーンショットを撮るウェブサイトのURL')
    parser.add_argument('--prompt', default='デフォルトプロンプト', help='AIモデルに送信するプロンプト')
    parser.add_argument('--finder-type', choices=['xpath', 'string', 'id', 'css'], help='特定の要素を見つけるためのファインダータイプ')
    parser.add_argument('--finder-value', help='ファインダーに使用する値')
    parser.add_argument('--margin-top', type=int, default=0, help='要素の上側のマージン')
    parser.add_argument('--margin-left', type=int, default=0, help='要素の左側のマージン')
    parser.add_argument('--margin-right', type=int, default=0, help='要素の右側のマージン')
    parser.add_argument('--margin-bottom', type=int, default=0, help='要素の下側のマージン')
    parser.add_argument('--ocr-mode', action='store_true', help='OCRモードを使用するかどうか')
    parser.add_argument('--window-width', type=int, default=1280, help='ウィンドウの幅')
    parser.add_argument('--window-height', type=int, default=800, help='ウィンドウの高さ')
    parser.add_argument('--zoom', type=float, default=1.0, help='ウェブページのズームレベル')
    parser.add_argument('--device-emulation', help='デバイスエミュレーションの名前')

    args = parser.parse_args()

    finder = None
    if args.finder_type and args.finder_value:
        if args.finder_type == 'xpath':
            finder = XpathFinder(args.finder_value, margin_top=args.margin_top, margin_left=args.margin_left, margin_right=args.margin_right, margin_bottom=args.margin_bottom)
        elif args.finder_type == 'string':
            finder = StringFinder(args.finder_value, margin_top=args.margin_top, margin_left=args.margin_left, margin_right=args.margin_right, margin_bottom=args.margin_bottom)
        elif args.finder_type == 'id':
            finder = IdFinder(args.finder_value, margin_top=args.margin_top, margin_left=args.margin_left, margin_right=args.margin_right, margin_bottom=args.margin_bottom)
        elif args.finder_type == 'css':
            finder = CssFinder(args.finder_value, margin_top=args.margin_top, margin_left=args.margin_left, margin_right=args.margin_right, margin_bottom=args.margin_bottom)

    window_size = (args.window_width, args.window_height)

    summary = SukushoSummary(
        url=args.url,
        prompt=args.prompt,
        finder=finder,
        ocr_mode=args.ocr_mode,
        window_size=window_size,
        zoom=args.zoom,
        device_emulation=args.device_emulation
    )

    try:
        result = summary.browse_site()
        print(result)
    except ElementNotFoundError as e:
        print(f'エラー: {e}')
    except Exception as e:
        print(f'予期しないエラー: {e}')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()

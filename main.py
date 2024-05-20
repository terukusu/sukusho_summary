"""
ECサイトをブラウズして商品の在庫をチェックするやつ。
"""

import logging
import os

from flask import Flask

import sukusho_summary

_TARGET_URL = '＜監視したいECサイトのURLに差し替え＞'
_TARGET_PRODUCT = '＜監視したい商品の名前など、ページ内の監視したい領域を特定するための文字列に差し替え＞'

logging.basicConfig(
    level=logging.INFO,
    encoding='utf-8',
    format='%(asctime)s %(name)s %(levelname)s %(message)s',
)

app = Flask(__name__)


@app.route('/', methods=['POST'])
def index():
    try:
        main()
    except Exception as e:
        logging.exception(e)
    finally:
        # Push型サブスクリプションの再送抑止のために200を返す
        return 'OK', 200


def main():
    print('OK')
    url = _TARGET_URL
    product = _TARGET_PRODUCT

    # サイトの内容に合わせてよしなにプロンプトを書く
    prompt = "在庫は有りますか？「かごへ入れる」は在庫ありと言う意味です。「在庫なし」は在庫なしという意味です。ただ一言、yes か no で答えてください。"

    # サイトの内容に合わせて、スクショを取りたいエリアをよしなに設定する
    f = sukusho_summary.StringFinder(product, margin_top=1, margin_bottom=120, margin_left=100, margin_right=450)

    s = sukusho_summary.SukushoSummary(url, prompt=prompt, finder=f)
    summary = s.browse_site()

    logging.debug(f'summary: {summary}')

    message = f'在庫があります！🙌🎉: {_TARGET_PRODUCT}'
    if 'YES' != summary.upper().strip():
        message = f'在庫がありません😢: {_TARGET_PRODUCT}'

    # 結果を通知(例: LINE通知など)
    send_notification(message)


def send_notification(message):
    # ここでは簡単のためログに出すだけ。LINEなど好きな通知方法によしなに変えればOK
    logging.info(f'message: {message}')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

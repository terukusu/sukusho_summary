"""
ECサイトをブラウズして商品の在庫をチェックするやつ。
"""

import logging
import os

from flask import Flask

import sukusho_summary

# 監視したいECサイトのURL
_TARGET_URL = 'https://github.com/terukusu/sukusho_summary/wiki/Sample-EC-Page'

# 監視したい商品の名前など、ページ内の監視したい領域を特定するための文字列。
# サンプルでは「購入」という項目に購入ボタンが配置されているのでその近辺をの領域を監視する。
_TARGET_ELEMENT = '購入'

# 商品名。通知メッセージに表示される。
_TARGET_PRODUCT = 'スーパーツレルンダー'

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
        # Pub/SubでのPush型サブスクリプションの場合の再送を抑止するために200を返す
        return 'OK', 200


def main():
    url = _TARGET_URL
    element = _TARGET_ELEMENT

    # サイトの内容に合わせてよしなにプロンプトを書く
    prompt = "在庫は有りますか？「かごへ入れる」は在庫ありと言う意味です。「在庫なし」は在庫なしという意味です。ただ一言、yes か no で答えてください。"

    # サイトの内容に合わせて、スクショを取りたいエリアをよしなに設定する

    # 目的の要素が表示されていさえすれば判定できる場合は、マージン等の細かい撮影領域の指定は不要
    # f = sukusho_summary.StringFinder(element)

    # 撮影領域を細かく指定したい場合は、margin_top, margin_bottom, margin_left, margin_rightを指定する
    f = sukusho_summary.StringFinder(element, margin_top=1, margin_bottom=120, margin_left=20, margin_right=20)

    s = sukusho_summary.SukushoSummary(url, prompt=prompt, finder=f)
    summary = s.browse_site()

    logging.debug(f'summary: {summary}')

    message = f'在庫があります！！ヽ(=´▽`=)ﾉ: {_TARGET_PRODUCT}'
    if 'YES' != summary.upper().strip():
        message = f'在庫がありません(T_T): {_TARGET_PRODUCT}'

    # 結果を通知(例: LINE通知など)
    send_notification(message)


def send_notification(message):
    # ここでは簡単のためログに出すだけ。LINEなど好きな通知方法によしなに変えればOK
    logging.info(f'message: {message}')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

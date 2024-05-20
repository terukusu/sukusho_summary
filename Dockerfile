# 基本イメージの選択
FROM python:3.11-slim

# 作業ディレクトリの設定
WORKDIR /app

# 必要なパッケージのインストール
RUN apt-get update && apt-get install -y \
    wget gnupg unzip jq curl \
    libglib2.0-0 libx11-6 libnss3 \
    fonts-ipafont fonts-ipaexfont \
    && rm -rf /var/lib/apt/lists/*


# Chromeのインストール
RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
RUN apt-get update && apt-get install -y -f \
    ./google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

# ChromeDriverの適切なバージョンを取得してインストール
# https://googlechromelabs.github.io/chrome-for-testing/#stable から ↑でインストールされる 「chrome」 のバージョンに合った「chromedriver」を選ぶ
RUN wget -q "https://storage.googleapis.com/chrome-for-testing-public/125.0.6422.60/linux64/chromedriver-linux64.zip" \
    && unzip chromedriver-linux64.zip \
    && mv chromedriver-linux64/chromedriver /usr/bin/chromedriver \
    && chmod +x /usr/bin/chromedriver

# Pythonの依存関係をインストール
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードのコピー
COPY main.py sukusho_summary.py /app/

EXPOSE 8080

# コンテナ起動時に実行されるコマンド
CMD ["python", "main.py"]

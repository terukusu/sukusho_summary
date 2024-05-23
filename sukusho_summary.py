import base64
import logging
import tempfile
import os

from typing import Optional, Callable

from abc import ABC, abstractmethod
from openai import OpenAI
from PIL import Image
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement

_OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
_OPENAI_MODEL_NAME = 'gpt-4-vision-preview'
_DEFAULT_PROMPT = "このWebサイトのスクリーンショットについて詳しく日本語で解説してください。"
_DEFAULT_WINDOW_SIZE = (1920, 1080)
_DEFAULT_IMPLICITLY_WAIT = 10
_DEFAULT_ZOOM = 1.0


class BaseFinder(ABC):
    """
    Represents a screenshot capture area.
    Margins are relative to the top-left coordinates of the found element.
    """

    def __init__(self, *, margin_top: int = 0, margin_left: int = 0,
                 margin_right: int = 0, margin_bottom: int = 0):

        if any(margin < 0 for margin in [margin_top, margin_left, margin_right, margin_bottom]):
            raise ValueError('Margins must be non-negative')

        self.margin_top = margin_top
        self.margin_left = margin_left
        self.margin_right = margin_right
        self.margin_bottom = margin_bottom

    def __repr__(self):
        kws = [f"{key}={value!r}" for key, value in self.__dict__.items()]
        return "{}({})".format(type(self).__name__, ", ".join(kws))

    @abstractmethod
    def find_element(self, driver: WebDriver) -> WebElement:
        pass


class XpathFinder(BaseFinder):
    xpath: str

    def __init__(self, xpath: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.xpath = xpath

    def find_element(self, driver: WebDriver) -> WebElement:
        return driver.find_element(By.XPATH, self.xpath)


class StringFinder(BaseFinder):
    search_string: str

    def __init__(self, search_string: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.search_string = search_string

    def find_element(self, driver: WebDriver) -> WebElement:
        return driver.find_element(By.XPATH, f"//*[contains(text(), '{self.search_string}')]")


class IdFinder(BaseFinder):
    id_: str

    def __init__(self, id_: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.id = id_

    def find_element(self, driver: WebDriver) -> WebElement:
        return driver.find_element(By.ID, self.id)


class CssFinder(BaseFinder):
    selector: str

    def __init__(self, selector: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selector = selector

    def find_element(self, driver: WebDriver) -> WebElement:
        return driver.find_element(By.CSS_SELECTOR, self.selector)


class ElementNotFoundError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class SukushoSummary:
    """
    ウェブサイトをブラウズし、スクリーンショットを撮り、そのデータをAIモデルに送信するプロセスを管理するクラスです。
    """
    listener: Optional[Callable[[str], None]] = None

    def __init__(self, url: str, *, prompt: str = _DEFAULT_PROMPT,
                 finder: BaseFinder = None, ocr_mode: bool = False, window_size: tuple[int, int] = _DEFAULT_WINDOW_SIZE,
                 zoom: float = _DEFAULT_ZOOM, device_emulation: str = None):
        """
        SukushoSummaryクラスのコンストラクタ。

        Args:
            url (str): スクリーンショットを撮るウェブサイトのURL。
            prompt (str, optional): AIモデルに送信するプロンプト。デフォルトは _DEFAULT_PROMPT。
            finder (BaseFinder, optional): 特定の要素を見つけるためのファインダークラス。デフォルトは None。
            ocr_mode (bool, optional): OCRモードを使用するかどうか。デフォルトは False。
            window_size (tuple[int, int], optional): ウィンドウサイズ（幅、高さ）。デフォルトは _DEFAULT_WINDOW_SIZE。
            zoom (float, optional): ウェブページのズームレベル。デフォルトは _DEFAULT_ZOOM。
            device_emulation (str, optional): デバイスエミュレーションの名前。各種スマホやタブレットなど、Chromeが偽装できるデバイスなら何でも指定可能。デフォルトは None。
        """
        self.url = url
        self.prompt = prompt
        self.finder = finder
        self.ocr_mode = ocr_mode
        self.window_size = window_size
        self.zoom = zoom
        self.device_emulation = device_emulation
        self.driver = self._init_webdriver()

    def on_progress(self, listener: Callable[[str], None]):
        if callable(listener):
            self.listener = listener
        else:
            raise ValueError("Provided argument is not a callable function")

    def trigger_progress(self, message: str):
        if self.listener is not None:
            self.listener(message)
        else:
            logging.debug("Listener is not set or message is not a string")

    def browse_site(self) -> str:
        screenshot_path = None

        try:
            self.trigger_progress('サイトをブラウズします...')
            self.driver.get(self.url)
            self.driver.execute_script(f"document.body.style.zoom = '{self.zoom}'")

            self.trigger_progress('サイトを解析します...')
            element = self._scroll_to_element()

            self.trigger_progress('撮影領域を検出します...')
            crop_area = self._determine_crop_area(element)

            self.trigger_progress('スクリーンショットを撮影します...')
            screenshot_path = self._take_screenshot(crop_area)

            logging.info(f'screenshot_path: {screenshot_path}')

            self.trigger_progress('スクリーンショットをAIで処理します...')
            result = self._process_screenshot(screenshot_path)
            return result
        finally:
            self.driver.quit()

            # 掃除する場合はここをアンコメント
            # if screenshot_path and os.path.exists(screenshot_path):
            #     os.remove(screenshot_path)

    def _init_webdriver(self) -> WebDriver:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--hide-scrollbars")
        chrome_options.add_argument("--single-process")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--mute-audio")
        chrome_options.add_argument("--lang=ja")

        if self.device_emulation:
            chrome_options.add_experimental_option("mobileEmulation", {"deviceName": self.device_emulation})

        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(_DEFAULT_IMPLICITLY_WAIT)

        if self.device_emulation:
            # window_size = driver.get_window_size()
            width = driver.execute_script("return window.innerWidth;")
            height = driver.execute_script("return window.innerHeight;")
            self.window_size = (width, height)
        else:
            driver.set_window_size(*self.window_size)

        return driver

    def _find_element(self) -> WebElement | None:
        try:
            return self.finder.find_element(self.driver)
        except NoSuchElementException:
            raise ElementNotFoundError(f"指定された要素は見つかりませんでした。: finder={self.finder}")

    def _scroll_to_element(self) -> WebElement | None:
        if not self.finder:
            return None

        element = self._find_element()

        logging.info(f'window_size: {self.window_size}')
        logging.info(f'element.location: {element.location}')
        logging.info(f'element.size: {element.size}')

        y_offset = self.driver.execute_script("return window.pageYOffset;")
        x_offset = self.driver.execute_script("return window.pageXOffset;")
        dpr = self.driver.execute_script("return window.devicePixelRatio;")

        logging.info(f'dpr: {dpr}')

        scroll_x = max(0, (element.location['x'] - x_offset - self.finder.margin_left) * self.zoom)
        scroll_y = max(0, (element.location['y'] - y_offset - self.finder.margin_top) * self.zoom)

        logging.info(f'scroll_x: {scroll_x}, scroll_y: {scroll_y}')

        self.driver.execute_script(f"window.scrollBy({scroll_x}, {scroll_y});")

        return element

    def _determine_crop_area(self, element: WebElement) -> tuple[int, int, int, int] | None:
        if not element or not (
                self.finder.margin_top or self.finder.margin_left
                or self.finder.margin_right or self.finder.margin_bottom):

            return None

        y_offset = self.driver.execute_script("return window.pageYOffset;")
        x_offset = self.driver.execute_script("return window.pageXOffset;")
        dpr = self.driver.execute_script("return window.devicePixelRatio;")

        if self.finder.margin_top:
            top = max(0, (element.location['y'] - y_offset - self.finder.margin_top) * self.zoom * dpr)
        else:
            top = 0

        if self.finder.margin_left:
            left = max(0, (element.location['x'] - x_offset - self.finder.margin_left) * self.zoom * dpr)
        else:
            left = 0

        if self.finder.margin_right:
            right = (element.location['x'] - x_offset + element.size['width'] + self.finder.margin_right) * self.zoom * dpr
        else:
            # 未指定扱い
            right = 0

        if self.finder.margin_bottom:
            bottom = (element.location['y'] - y_offset + element.size['height'] + self.finder.margin_bottom) * self.zoom * dpr
        else:
            # 未指定扱い
            bottom = 0

        return left, top, right, bottom

    def _take_screenshot(self, crop_area: tuple[int, int, int, int]) -> str:
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmpfile:
            self.driver.save_screenshot(tmpfile.name)
            if crop_area:
                with Image.open(tmpfile.name) as img:
                    right = crop_area[2] or img.width
                    bottom = crop_area[3] or img.height
                    new_crop = (crop_area[0], crop_area[1], right, bottom)

                    cropped_img = img.crop(new_crop)
                    cropped_img.save(tmpfile.name)

            return tmpfile.name

    def _process_screenshot(self, screenshot_path: str) -> str:
        with open(screenshot_path, 'rb') as f:
            screenshot_data = f.read()

        result = openai_chat(self.prompt, images=[('image/png', screenshot_data)])

        return result


def get_openai_client() -> OpenAI:
    client = OpenAI(
        api_key=_OPENAI_API_KEY,
    )

    return client


def openai_chat(prompt: str, *args, images: list[(str, bytes)] = None):
    """
    OpenAI APIを使用してテキスト生成を行う関数。

    Args:
        prompt (str): ユーザーからのプロンプト。
        *args: その他の引数（現在使用されていない）。
        images (list[(str, bytes)], optional): MIMEタイプと画像のバイナリデータのタプルからなるリスト。

    Returns:
        str: OpenAI APIからの生成されたテキスト。
    """

    client = get_openai_client()

    messages = [
        {
            'role': 'user',
            'content': [
                {
                    'type': 'text',
                    'text': prompt
                }
            ]
        }
    ]

    if images is not None:
        for image in images:
            mime_type, image_bin = image
            image_b64 = base64.b64encode(image_bin).decode('ascii')
            messages[0]['content'].append({
                'type': 'image_url',
                'image_url': {
                    'url': f'data:{mime_type};base64,{image_b64}'
                }
            })

    kwargs = {
        'model': _OPENAI_MODEL_NAME,
        'messages': messages
    }

    # OpenAI APIで文書生成
    result = client.chat.completions.create(**kwargs)
    return_result = result.choices[0].message.content

    return return_result

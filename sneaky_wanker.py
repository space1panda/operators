from typing import Literal, Tuple
from helium import start_firefox, get_driver
from helium import scroll_down, press, click, ENTER, write
from openai import OpenAI
from selenium.webdriver.common.by import By
from time import sleep


class GoogleMapsScrapper:
    """
    Get Google Maps reviews of the place of interest using Maps API (lol no)
    """

    PANE_ELEMENT = ".m6QErb.DxyBCb.kA9KIf.dS8AEf.XiKgde"

    def __init__(
            self, vllm_endpoint: str = "http://localhost:8000/v1",
            vlm_name: str = "Qwen/Qwen2-VL-2B-Instruct-GPTQ-Int4",
            webdriver: Literal['firefox', 'chrome'] = 'firefox',
            crawler_start: str = "google.com/maps?hl=en",
            window_size: Tuple[int] = (800, 1400),
            num_scrolls: int = 30,
            scroll_step_px: int = 500
            ):
        self._init_crawler(crawler_start, window_size)
        self._vlm_name = vlm_name
        self._num_scrolls = num_scrolls
        self._scroll_step = scroll_step_px
        self._init_vlm_client(vllm_endpoint)

    def _init_crawler(self, start: str, window_size: Tuple[str]):
        start_firefox(start, headless=False)
        sleep(1)
        driver = get_driver()
        driver.set_window_size(*window_size)
        self._driver = driver
        self.pass_cookies()

    def _init_vlm_client(self, endpoint: str):
        client = OpenAI(
            api_key='empty',
            base_url=endpoint
            )
        self._vlm_client = client

    def pass_cookies(self):
        scroll_down(500)
        button = self._driver.find_element(
            By.CSS_SELECTOR, "button[aria-label*='Accept']")
        button.click()
        sleep(1)

    def get_ocr_prompt(self, base64_image: str):
        messages = [
            {
                "role": "system", "content": "You are a helpful OCR assistant."
            },
            {
                "role": "user", "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": base64_image
                            },
                    },

                    {
                        "type": "text", "text": "Extract and return the text illustrated in the review section"
                    },
                    ],
            }
        ]
        return messages

    def get_reviews(self, query_location: str):
        write(query_location)
        press(ENTER)
        click('Reviews')
        sleep(1)
        click('Sort')
        click('Lowest Rating')
        target_div = self._driver.find_element(
            By.CSS_SELECTOR, self.PANE_ELEMENT)

        for i in range(self._num_scrolls):
            try:
                click('See more')
            except LookupError:
                pass
            screenshot_base64 = self._driver.get_screenshot_as_base64()
            base64_qwen = f"data:image;base64,{screenshot_base64}"
            chat_response = self._vlm_client.chat.completions.create(
                model=self._vlm_name,
                messages=self.get_ocr_prompt(base64_qwen),
                temperature=0.1
            )
            print(chat_response.choices[0].message.content)
            self._driver.execute_script(
                f"arguments[0].scrollTop += {self._scroll_step};",
                target_div)


if __name__ == '__main__':
    crawler = GoogleMapsScrapper(scroll_step_px=1000)
    crawler.get_reviews('Empire State Building')
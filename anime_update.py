import logging
import time

from settings import CONFIG
from base import Crawler
from helper import helper

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


UPDATE = Crawler()

if __name__ == "__main__":
    while True:
        try:
            UPDATE.crawl_page(CONFIG.KISSANIME_LATEST_PAGE)
        except Exception as e:
            helper.error_log(
                msg=f"anime update failed\n{e}", log_file="anime_update.log"
            )

        time.sleep(CONFIG.WAIT_BETWEEN_LATEST)

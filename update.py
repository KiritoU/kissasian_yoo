import logging
import time

from settings import CONFIG
from base import Crawler
from helper import helper

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


crawler = Crawler()

if __name__ == "__main__":
    while True:
        try:
            crawler.crawl_page(CONFIG.KISSASIAN_LATEST_PAGE)
        except Exception as e:
            helper.error_log(
                msg=f"kissasian update failed\n{e}", log_file="kissasian_update.log"
            )

        time.sleep(CONFIG.WAIT_BETWEEN_LATEST)

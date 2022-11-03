import logging
import time

from settings import CONFIG
from base import Crawler
from helper import helper

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)

crawler = Crawler()

if __name__ == "__main__":
    pages = CONFIG.KISSASIAN_NEW_AND_HOST_PAGE_LAST_PAGE
    while True:
        for i in range(pages, 1, -1):
            try:
                crawler.crawl_page(f"{CONFIG.KISSASIAN_NEW_AND_HOST_PAGE}?page={i}")
            except Exception as e:
                helper.error_log(
                    msg=f"kissasian crawl failed\n{e}", log_file="kissasian_crawl.log"
                )
            time.sleep(CONFIG.WAIT_BETWEEN_ALL)

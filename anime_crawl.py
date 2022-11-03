import logging
import time

from settings import CONFIG
from base import Crawler
from helper import helper

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)

UPDATE = Crawler()

if __name__ == "__main__":
    pages = CONFIG.KISSANIME_NEW_AND_HOST_PAGE_LAST_PAGE
    while True:
        for i in range(pages, 1, -1):
            try:
                UPDATE.crawl_page(f"{CONFIG.KISSANIME_NEW_AND_HOST_PAGE}?page={i}")
            except Exception as e:
                helper.error_log(
                    msg=f"anime crawl failed\n{e}", log_file="anime_crawl.log"
                )
            time.sleep(CONFIG.WAIT_BETWEEN_ALL)

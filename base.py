import json
import logging

from bs4 import BeautifulSoup
from time import sleep

from settings import CONFIG
from helper import helper
from _db import database

logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


class Crawler:
    def crawl_soup(self, url):
        logging.info(f"Crawling {url}")
        html = helper.download_url(url)
        if html.status_code == 404:
            return 404

        soup = BeautifulSoup(html.content, "html.parser")

        return soup

    def get_episode_details(self, href, title, genres) -> list:
        if "http" not in href:
            href = CONFIG.KISSASIAN_HOMEPAGE + href

        res = {
            "title": title,
            "slug": helper.get_slug(href),
            "genre": genres,
            "trailer": "",
            "description": "",
        }
        try:
            soup = self.crawl_soup(href)

            res["links"] = helper.get_links_from(soup)

            res["released"] = [helper.get_released_from(soup)]

            try:
                # description = (
                #     soup.find("article", class_="description")
                #     .text.strip()
                #     .strip("\n")
                #     .strip()
                # )
                # for replaceText in CONFIG.DESCRIPTION_REPLACE_TEXTS:
                #     description = description.replace(
                #         replaceText, CONFIG.DESCRIPTION_REPLACE_TO
                #     )
                res["description"] = CONFIG.EPISODE_DEFAULT_DESCRIPTION.format(
                    title, title
                )

            except Exception as e:
                helper.error_log(
                    msg=f"Error getting description\n{href}\n{e}",
                    log_file="base.get_episode_details.description.log",
                )

        except Exception as e:
            helper.error_log(
                f"Failed to get episode player link\n{href}\n{e}",
                log_file="episode_link.log",
            )
            return {}

        return res

    def crawl_anime(self, href: str):
        soup = self.crawl_soup(href)

        if soup == 404:
            return

        barContentInfo = soup.find("div", class_="barContentInfo")

        if not barContentInfo:
            helper.error_log(
                f"No bar content info was found in {href}",
                log_file="base.crawl_anime.barContentInfo.log",
            )

        title = helper.get_title_from(barContentInfo)

        poster_url = helper.get_poster_url(barContentInfo)
        poster_url = helper.add_https_to(poster_url)

        genres = helper.get_genres_from(barContentInfo)
        status = helper.get_status_from(barContentInfo)
        country = helper.get_country_from(barContentInfo)

        description = helper.get_description_from(barContentInfo=barContentInfo)
        othername = helper.get_othername_from(barContentInfo=barContentInfo)

        if not title:
            return

        serie_details = {
            "title": title,
            "slug": helper.get_slug(href),
            "description": description,
            "othername": othername,
            "genre": genres,
            "status": status,
            "country": country,
            "released": "",
            "trailer": "",
            "picture": poster_url,
            "links": [],
            "child_episode": [],
        }

        barContentEpisode = soup.find("div", class_="barContentEpisode")
        if not barContentEpisode:
            return

        listing = barContentEpisode.find("ul", class_="listing")
        if not listing:
            return

        items = listing.find_all("li")
        for item in items:
            try:
                a_element = item.find("a")
                episodeTitle = helper.format_text(a_element.get("title"))
                try:
                    isRaw = a_element.find("span")
                    if "raw" in str(isRaw).lower():
                        episodeTitle = episodeTitle + " - RAW"
                    else:
                        episodeTitle = episodeTitle + " - EngSub"
                except Exception as e:
                    print(e)
                episodeHref = a_element.get("href")

                serie_details["child_episode"].append(
                    self.get_episode_details(episodeHref, episodeTitle, genres)
                )
            except Exception as e:
                helper.error_log(
                    msg=f"Failed to get child episode\n{item}\n{e}",
                    log_file="base.crawl_anime.barContentEpisode.log",
                )
        if serie_details["child_episode"] and serie_details["child_episode"][0]:
            first_child = serie_details["child_episode"][0]
            serie_details["released"] = first_child["released"]

        return serie_details

    def crawl_page(self, url):
        soup = self.crawl_soup(url)

        if soup == 404:
            return

        list_drama = soup.find("div", class_="list-drama")
        if not list_drama:
            return

        items = list_drama.find_all("div", class_="item")
        if not items:
            return

        for item in items:
            try:
                href = item.find("a").get("href")

                if "http" not in href:
                    href = CONFIG.KISSASIAN_HOMEPAGE + href

                serie_details = self.crawl_anime(href=href)
                helper.insert_serie(serie_details)

            except Exception as e:
                helper.error_log(
                    f"Failed to get href\n{item}\n{e}", "base.crawl_page.log"
                )

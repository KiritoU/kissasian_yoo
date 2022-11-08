from time import sleep
import requests


from pathlib import Path
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from slugify import slugify


from _db import database
from notifications import Notification


from settings import CONFIG


class Helper:
    def get_header(self):
        header = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E150",  # noqa: E501
            "Accept-Encoding": "gzip, deflate",
            # "Cookie": CONFIG.COOKIE,
            "Cache-Control": "max-age=0",
            "Accept-Language": "vi-VN",
            "Referer": "https://mangabuddy.com/",
        }
        return header

    def error_log(self, msg: str, log_file: str = "failed.log"):
        datetime_msg = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        Path("log").mkdir(parents=True, exist_ok=True)
        with open(f"log{CONFIG.OS_SLASH}{log_file}", "a") as f:
            print(f"{datetime_msg} LOG:  {msg}\n{'-' * 80}", file=f)

    def download_url(self, url):
        return requests.get(url, headers=self.get_header())

    def format_text(self, text: str) -> str:
        return text.strip().strip("\n").replace("\\", "")

    def get_timeupdate(self) -> str:
        # TODO: later
        timeupdate = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        return timeupdate

    def get_slug(self, href: str) -> str:
        try:
            return href.split("/")[-1]
        except Exception as e:
            self.error_log(
                f"Failed to get slug: {href}\n{e}", log_file="helper.get_slug.log"
            )
            return ""

    def get_description_from_1(self, detail: BeautifulSoup) -> str:
        try:
            description = detail.find("div", class_="des").text
            return description
        except Exception as e:
            self.error_log(
                f"Failed to get description from{detail}\n{e}",
                log_file="get_description1.log",
            )
            return ""

    def get_links_from(self, soup: BeautifulSoup) -> str:
        try:
            selectServer = soup.find("select", id="selectServer")
            options = selectServer.find_all("option")

            return [option.get("value") for option in options]
        except Exception as e:
            self.error_log(
                msg=f"Failed to get links from {soup}\n{e}",
                log_file="helper.get_links_from.log",
            )
            return []

    def get_info_value(self, item: BeautifulSoup) -> str:
        res = []
        try:
            for a in item.find_all("a"):
                res.append(a.get("title"))
        except Exception as e:
            self.error_log(
                f"Failed to get info value\n{item}\n{e}",
                log_file="helper_get_info_value.log",
            )

        return ", ".join(res)

    def get_trailer_src(self, soup: BeautifulSoup) -> str:
        res = ""

        scripts = soup.find_all("script")
        for script in scripts:
            if "iframe-trailer" in str(script):
                lines = str(script).split(";")
                for line in lines:
                    if "iframe-trailer" in line:
                        line_splitted = line.split('"')
                        for splitted in line_splitted:
                            if "http" in splitted:
                                res = splitted
        return res

    def get_info_movies(self, soup: BeautifulSoup) -> dict:
        detail = soup.find("div", class_="detail")

        res = {"genre": "", "country": "", "released": "", "trailer": ""}

        try:
            res["trailer"] = self.get_trailer_src(soup)

            info_movies = detail.find("div", {"id": "info_movies"})

            right = info_movies.find("div", class_="right")
            li_items = right.find_all("li")
            for item in li_items:
                key = item.find("span").text
                if "release" in key.lower():
                    value = self.format_text(
                        item.text.replace(key, "").replace('"', "")
                    )
                else:
                    value = self.get_info_value(item)

                key = CONFIG.POSTMETA_MAPPING[key.replace(":", "").strip()]
                res[key] = value

        except Exception as e:
            self.error_log(
                f"Failed to get info_movies {detail}\n{e}",
                log_file="get_info_movies.log",
            )

        return res

    def save_thumb(
        self,
        imageUrl: str,
        imageName: str = "0.jpg",
    ) -> str:
        Path(CONFIG.THUMB_SAVE_PATH).mkdir(parents=True, exist_ok=True)
        saveImage = f"{CONFIG.THUMB_SAVE_PATH}/{imageName}"

        isNotSaved = not Path(saveImage).is_file()
        if isNotSaved:
            image = self.download_url(imageUrl)
            with open(saveImage, "wb") as f:
                f.write(image.content)
            isNotSaved = True

        return [saveImage, isNotSaved]

    def insert_thumb(self, post_name: str, thumbUrl: str) -> int:
        thumbExtension = thumbUrl.split("/")[-1].split(".")[-1]
        if not thumbExtension:
            return 0

        thumbName = f"{slugify(post_name)}.{thumbExtension}"

        self.save_thumb(thumbUrl, thumbName)
        timeupdate = self.get_timeupdate()
        thumbPostData = (
            0,
            timeupdate,
            timeupdate,
            "",
            thumbName,
            "",
            "inherit",
            "open",
            "closed",
            "",
            thumbName,
            "",
            "",
            timeupdate,
            timeupdate,
            "",
            0,
            "",
            0,
            "attachment",
            "image/png",
            0,
        )

        thumbId = database.insert_into(table="posts", data=thumbPostData)
        database.insert_into(
            table="postmeta",
            data=(thumbId, "_wp_attached_file", f"covers/{thumbName}"),
        )

        return thumbId

    def insert_taxonomy(self, post_id: int, taxonomies: list, taxonomy_kind: str):
        # taxonomies = taxonomies.split(",")
        for taxonomy in taxonomies:
            try:
                termName = self.format_text(taxonomy)
                cols = "tt.term_taxonomy_id"
                table = f"{CONFIG.TABLE_PREFIX}term_taxonomy tt, {CONFIG.TABLE_PREFIX}terms t"
                condition = f't.name = "{termName}" AND tt.term_id=t.term_id AND tt.taxonomy="{taxonomy_kind}"'

                query = f"SELECT {cols} FROM {table} WHERE {condition}"
                beTaxonomyId = database.select_with(query)

                if not beTaxonomyId:
                    taxonomyTermId = database.insert_into(
                        table="terms",
                        data=(termName.capitalize(), slugify(termName), 0),
                    )
                    taxonomyTermTaxonomyId = database.insert_into(
                        table="term_taxonomy",
                        data=(taxonomyTermId, taxonomy_kind, "", 0, 0),
                    )
                else:
                    taxonomyTermTaxonomyId = beTaxonomyId[0][0]

                database.insert_into(
                    table="term_relationships",
                    data=(post_id, taxonomyTermTaxonomyId, 0),
                )
            except Exception as e:
                self.error_log(
                    msg=f"Error inserting taxonomy: {taxonomy}\n{e}",
                    log_file="helper.insert_taxonomy.log",
                )

    def insert_movie(self, movie_details: dict, post_type: str = "post"):
        movie_name = movie_details["name"].replace("'", "''")
        isMovieExists = database.select_all_from(
            table="posts", condition=f"post_title='{movie_name}'"
        )
        if isMovieExists:
            return

        thumbId = self.insert_thumb(movie_details["name"], movie_details["picture"])
        timeupdate = self.get_timeupdate()
        data = (
            0,
            timeupdate,
            timeupdate,
            movie_details["description"],
            movie_details["name"],
            "",
            "publish",
            "open",
            "closed",
            "",
            slugify(movie_details["name"]),
            "",
            "",
            timeupdate,
            timeupdate,
            "",
            0,
            "",
            0,
            post_type,
            "",
            0,
        )
        postId = database.insert_into(table=f"posts", data=data)

        postmetas = [
            (postId, "tw_multi_chap", "0"),
            (postId, "tw_status", "Đang cập nhật"),
            (postId, "post_question_1", ""),
            (postId, "_post_question_1", "field_60092d86e0981"),
            (
                postId,
                "video_link",
                movie_details["links"][0],
            ),
            (postId, "_video_link", "field_601d685ea50eb"),
            (postId, "chat_luong_video", movie_details["season"]),
            (postId, "_chat_luong_video", "field_5ff2f401eac3f"),
            (postId, "country", movie_details["country"]),
            (postId, "_country", "field_60187b7c9c230"),
            (postId, "released", movie_details["released"]),
            (postId, "_released", "field_62e7989914215"),
            (postId, "trailer", movie_details["trailer"]),
            (postId, "_trailer", "field_62e798d4938b0"),
            (postId, "genre", movie_details["genre"]),
            (postId, "_genre", "field_62eb4674d417d"),
            (postId, "film_type", ""),
            (postId, "_film_type", "field_630ecf331b56c"),
            (postId, "_", "field_630ecf4b1b56d"),
            (postId, "post_views_count", "0"),
        ]
        if thumbId:
            postmetas.append((postId, "_thumbnail_id", thumbId))
        for i in range(1, len(movie_details["links"])):
            postmetas.append(
                (
                    postId,
                    f"video_link_{i}",
                    movie_details["links"][i],
                )
            )
        for pmeta in postmetas:
            database.insert_into(
                table="postmeta",
                data=pmeta,
            )

        database.insert_into(table="term_relationships", data=(postId, 13853, 0))
        self.insert_taxonomy(postId, movie_details["country"], "country")
        self.insert_taxonomy(postId, movie_details["released"], "release")
        self.insert_taxonomy(postId, movie_details["genre"], "genres")

        return postId

    def insert_root_serie(self, serie_details: dict) -> int:
        serie_name = serie_details["title"].replace("'", "''")
        backendSerie = database.select_all_from(
            table="posts", condition=f"post_title='{serie_name}'", cols="ID"
        )
        if backendSerie:
            try:
                postId = backendSerie[0][0]
                thumb = database.select_all_from(
                    table="postmeta",
                    condition=f"post_id={postId} AND meta_key='_thumbnail_id'",
                    cols="meta_value",
                )
                thumbId = 0
                if thumb and thumb[0] and thumb[0][0]:
                    thumbId = thumb[0][0]
                return [postId, thumbId]
            except Exception as e:
                self.error_log(
                    f"Serie: {serie_name} - Something went wrong!!!\n{e}",
                    log_file="exitst_post_and_postmeta.log",
                )
                return [0, 0]

        thumbId = self.insert_thumb(
            slugify(serie_details["title"]), serie_details["picture"]
        )
        timeupdate = self.get_timeupdate()
        data = (
            0,
            timeupdate,
            timeupdate,
            f'Other name: {", ".join(serie_details["othername"])}\nDescription: {serie_details["description"]}'
            if serie_details["othername"]
            else serie_details["description"],
            serie_details["title"],
            "",
            "publish",
            "open",
            "closed",
            "",
            slugify(serie_details["title"]),
            "",
            "",
            timeupdate,
            timeupdate,
            "",
            0,
            "",
            0,
            "post",
            "",
            0,
        )

        postId = database.insert_into(table=f"posts", data=data)

        postmetas = [
            (postId, "show_tien_to", "0"),
            (postId, "show_trangthai", "0"),
            (postId, "tw_multi_chap", "1"),
            (postId, "chat_luong_video", "HD"),
            # (postId, "country", serie_details["country"]),
            # (postId, "released", serie_details["released"]),
            (postId, "trailer", serie_details["trailer"]),
            # (postId, "genre", serie_details["genre"]),
            (postId, "tw_parent", postId),
            (postId, "film_type", "TV SHOW"),
            (postId, "post_views_count", "0"),
        ]
        if thumbId:
            postmetas.append((postId, "_thumbnail_id", thumbId))
        for pmeta in postmetas:
            database.insert_into(
                table="postmeta",
                data=pmeta,
            )

        # if serie_details["status"].lower() == "ongoing":
        #     database.insert_into(
        #         table="term_relationships", data=(postId, CONFIG.ONGOING_TAXONOMY_ID, 0)
        #     )

        # if serie_details["status"].lower() == "completed":
        #     database.insert_into(
        #         table="term_relationships",
        #         data=(postId, CONFIG.COMPLETED_TAXONOMY_ID, 0),
        #     )

        database.insert_into(table="term_relationships", data=(postId, 1, 0))

        self.insert_taxonomy(postId, serie_details["country"], "country")
        self.insert_taxonomy(postId, serie_details["released"], "release")
        self.insert_taxonomy(postId, serie_details["genre"], "genres")
        self.insert_taxonomy(postId, [serie_details["status"]], "status")
        # self.insert_taxonomy(postId, serie_details["othername"], "othername")

        return [postId, thumbId]

    def check_duplicate_serie(self, serieEpisodeName: str):
        nameSplitted = serieEpisodeName.split("-")
        if len(nameSplitted) < 2:
            return

        checkName = nameSplitted[0].strip() + "%" + nameSplitted[1].strip()
        backendSerieEpisode = database.select_all_from(
            table="posts", condition=f"post_title LIKE '{checkName}'"
        )
        if backendSerieEpisode:
            Notification(f"{serieEpisodeName} might be duplicated!").send()

    def insert_serie_episode(self, episode: dict, serieId: int, thumbId: int):
        serieEpisodeName = episode["title"].replace("'", "''")

        backendSerieEpisode = database.select_all_from(
            table="posts", condition=f"post_title='{serieEpisodeName}'"
        )
        if backendSerieEpisode:
            return

        # self.check_duplicate_serie(serieEpisodeName)

        timeupdate = self.get_timeupdate()
        data = (
            0,
            timeupdate,
            timeupdate,
            episode["description"],
            episode["title"],
            "",
            "publish",
            "open",
            "closed",
            "",
            slugify(episode["title"]),
            "",
            "",
            timeupdate,
            timeupdate,
            "",
            serieId,
            "",
            0,
            "chap",
            "",
            0,
        )

        postId = database.insert_into(table=f"posts", data=data)

        postmetas = [
            (postId, "show_tien_to", "0"),
            (postId, "show_trangthai", "0"),
            (postId, "chat_luong_video", "HD"),
            (
                postId,
                "video_link",
                episode["links"][0],
            ),
            # (postId, "country", episode["country"]),
            # (postId, "released", episode["released"]),
            (postId, "trailer", episode["trailer"]),
            # (postId, "genre", episode["genre"]),
            (postId, "post_views_count", "0"),
        ]

        if thumbId:
            postmetas.append((postId, "_thumbnail_id", thumbId))

        for i in range(1, len(episode["links"])):
            postmetas.append(
                (
                    postId,
                    f"video_link_{i}",
                    episode["links"][i],
                )
            )

        for pmeta in postmetas:
            database.insert_into(
                table="postmeta",
                data=pmeta,
            )

        # if episode["status"].lower() == "ongoing":
        #     database.insert_into(
        #         table="term_relationships", data=(postId, CONFIG.ONGOING_TAXONOMY_ID, 0)
        #     )

        # if episode["status"].lower() == "completed":
        #     database.insert_into(
        #         table="term_relationships",
        #         data=(postId, CONFIG.COMPLETED_TAXONOMY_ID, 0),
        #     )

        database.insert_into(table="term_relationships", data=(postId, 1, 0))
        self.insert_taxonomy(postId, episode["country"], "country")
        self.insert_taxonomy(postId, episode["released"], "release")
        self.insert_taxonomy(postId, episode["genre"], "genres")
        self.insert_taxonomy(postId, [episode["status"]], "status")

    def insert_serie(self, serie_details: dict):
        try:
            serieId, thumbId = self.insert_root_serie(serie_details)
        except Exception as e:
            self.error_log(
                msg=f"Error inserting root serie\n{serie_details}\n{e}",
                log_file="insert_root_serie.log",
            )
            return

        for episode in serie_details["child_episode"]:
            episode["status"] = serie_details["status"]
            episode["country"] = serie_details["country"]
            try:
                self.insert_serie_episode(episode, serieId, thumbId)
                sleep(0.1)

            except Exception as e:
                self.error_log(
                    msg=f"Error inserting serie\n{episode}\n{e}",
                    log_file="insert_serie_episode.log",
                )

    def get_released_from(self, soup: BeautifulSoup) -> str:
        try:
            release = soup.find("div", class_="Releasew")
            replaceText = release.find("span").text

            res = release.text.replace(replaceText, "").strip().strip("\n").strip()

            return res

        except Exception as e:
            self.error_log(
                msg=f"Failed get_released_from\n{soup}\n{e}",
                log_file="helper.get_released_from.log",
            )
            return ""

    def add_https_to(self, url: str) -> str:
        if not url:
            return ""

        if "http" not in url:
            url = "https:" + url

        return url

    def get_title_from(self, barContentInfo: BeautifulSoup) -> str:
        try:
            title = barContentInfo.find("a", class_="bigChar").text

            return self.format_text(title)

        except Exception as e:
            self.error_log(
                msg=f"Failed to find title\n{str(barContentInfo)}\n{e}",
                log_file="helper.get_title_from.log",
            )
            return ""

    def get_poster_url(self, barContentInfo: BeautifulSoup) -> str:
        try:
            img_picture_mb = barContentInfo.find("div", class_="img_picture_mb")
            poster_url = img_picture_mb.find("img").get("src")
            return poster_url

        except Exception as e:
            self.error_log(
                msg=f"Failed to get poster URL\n{str(barContentInfo)}\n{e}",
                log_file="helper.get_poster_url.log",
            )
            return ""

    def get_genres_from(self, barContentInfo: BeautifulSoup) -> list:
        res = []

        try:
            for p in barContentInfo.find_all("p"):
                if p.find("span"):
                    key = p.find("span").text.replace(":", "").strip()
                    if "genres" in key.lower():
                        a_elements = p.find_all("a")
                        for a in a_elements:
                            a_title = a.get("title")
                            res.append(self.format_text(a_title))

        except Exception as e:
            self.error_log(
                msg=f"Failed to get genres\n{str(barContentInfo)}\n{e}",
                log_file="genres.log",
            )

        return res

    def get_status_from(self, barContentInfo: BeautifulSoup) -> str:
        res = "Ongoing"

        try:
            for p in barContentInfo.find_all("p"):
                if p.find("span"):
                    key = p.find("span").text.replace(":", "").strip()
                    if "status" in key.lower():
                        value = p.text.replace("Status:", "")
                        value = self.format_text(value)

                        return value

        except Exception as e:
            self.error_log(
                msg=f"Failed to get status\n{str(barContentInfo)}\n{e}",
                log_file="helper.get_status_from.log",
            )

        return res

    def get_country_from(self, barContentInfo: BeautifulSoup) -> str:
        res = ""

        try:
            for p in barContentInfo.find_all("p"):
                if p.find("span"):
                    key = p.find("span").text.replace(":", "").strip()
                    if "country" in key.lower():
                        value = p.text.replace("Country:", "")
                        value = self.format_text(value)

                        return [value]

        except Exception as e:
            self.error_log(
                msg=f"Failed to get_country_from\n{str(barContentInfo)}\n{e}",
                log_file="helper.get_country_from.log",
            )

        return res

    def get_description_from(self, barContentInfo: BeautifulSoup) -> str:
        res = ""
        try:
            des = barContentInfo.find("p", class_="des")
            res = f"{self.format_text(des.text)}"
        except Exception as e:
            self.error_log(
                msg=f"Failed to get description\n{str(barContentInfo)}\n{e}",
                log_file="helper.get_description_from.log",
            )

        return res

    def get_othername_from(self, barContentInfo: BeautifulSoup) -> str:
        res = []

        try:
            for p in barContentInfo.find_all("p"):
                if p.find("span"):
                    key = p.find("span").text.replace(":", "").strip()
                    if "also" in key.lower():
                        othernames = p.find_all("a")
                        for othername in othernames:
                            res.append(othername.text)

        except Exception as e:
            self.error_log(
                msg=f"Failed to get othername\n{str(barContentInfo)}\n{e}",
                log_file="helper.get_othername_from.log",
            )

        return res


helper = Helper()

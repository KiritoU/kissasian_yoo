import os
import shutil
import logging

from time import sleep

from _db import Database
from settings import CONFIG

database = Database()
logging.basicConfig(format="%(asctime)s %(levelname)s:%(message)s", level=logging.INFO)


def delete_saved_thumbs():
    logging.info("Deleting saved thumbs")
    files = os.listdir(CONFIG.THUMB_SAVE_PATH)
    for file in files:
        path = f"{CONFIG.THUMB_SAVE_PATH}/{file}"
        if os.path.isfile(path):
            os.remove(path)


def main():
    delete_saved_thumbs()

    # query = "SELECT p.ID FROM `ODJiM2_term_relationships` tr, ODJiM2_posts p WHERE p.ID=tr.object_id AND p.post_type='post' AND tr.term_taxonomy_id=13853"
    post_ids = database.select_all_from(
        table="posts", condition="post_type='post' OR post_type='chap'"
    )
    post_ids = [x[0] for x in post_ids]

    for post_id in post_ids:
        logging.info(f"Deleting post: {post_id}")
        _thumbnail_id = database.select_all_from(
            table="postmeta",
            condition=f'post_id={post_id} AND meta_key="_thumbnail_id"',
        )
        if _thumbnail_id:
            database.delete_from(
                table="posts",
                condition=f"ID={_thumbnail_id[0][-1]}",
            )

        database.delete_from(
            table="postmeta",
            condition=f'post_id="{post_id}"',
        )

        database.delete_from(
            table="term_relationships",
            condition=f'object_id="{post_id}"',
        )

        database.delete_from(
            table="posts",
            condition=f'ID="{post_id}"',
        )

        sleep(0.1)


if __name__ == "__main__":
    main()

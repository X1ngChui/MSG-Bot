import random

import pixivpy3
from message import Message
from os.path import abspath, exists, isfile
from os import remove
from pathlib import Path
from fifo_cache import FifoCache


class PixivImage:
    def __init__(self, path: str, r18: bool = False, artist: str = None, artwork_id: str | int = None,
                 title: str = None, is_origin: bool = False):
        assert isfile(path)
        self.path = abspath(path)
        self.r18 = r18
        self.artist = artist
        self.artwork_id = artwork_id
        self.title = title
        self.message_id = None
        self.is_origin = is_origin

    def __del__(self):
        if exists(self.path) and isfile(self.path):
            remove(self.path)

    def as_uri(self):
        return Path(self.path).as_uri()


class PixivDownloader:
    def __init__(self):
        self.refresh_token = None
        self.api = pixivpy3.AppPixivAPI()
        self.image_cache = FifoCache(256)
        self.id_cache = FifoCache(256)
        self.tag_cache = FifoCache(256)

    def login(self, refresh_token: str):
        self.refresh_token = refresh_token
        self.api.auth(refresh_token=refresh_token)

    def check_connection(self):
        if not self.api.auth():
            self.api.auth(refresh_token=self.refresh_token)

    def get_illust_by_id(self, illust_id: int, origin: bool = False) -> PixivImage:
        self.check_connection()

        if illust_id in self.id_cache and self.id_cache[illust_id].is_origin == origin:
            return self.id_cache[illust_id]

        json_result = self.api.illust_detail(illust_id=illust_id)
        illust_info = json_result["illust"]
        image_url = illust_info["meta_single_page"]["original_image_url"] if origin \
            else illust_info["image_urls"]["medium"]
        image_name = image_url.split("/")[-1]

        if image_name in self.image_cache and self.image_cache[image_name].is_origin == origin:
            return self.image_cache[image_name]

        image_path = abspath("assets/img/" + image_name)
        self.api.download(url=image_url, path="assets/img/")
        image = PixivImage(image_path,
                           r18=illust_info["tags"][0]["name"] == "R-18",
                           artist=illust_info["user"]["name"],
                           artwork_id=illust_info["id"],
                           title=illust_info["title"],
                           is_origin=origin
                           )
        self.image_cache[image_name] = image
        self.id_cache[illust_id] = image

        return image

    def get_illust_by_id_impl(self, args: list, kwargs: dict) -> Message:
        try:
            illust_id = int(args[0])
            image = self.get_illust_by_id(illust_id, "-ogn" in kwargs or "-origin" in kwargs)
            return Message(group_id=kwargs["group_id"],
                           message=[
                               {
                                   "type": "reply",
                                   "data": {"id": kwargs["message_id"]}
                               },
                               {
                                   "type": "image",
                                   "data": {"file": image.as_uri(), "is_origin": 1}
                               }
                           ],
                           attached=image)
        except (ValueError, KeyError):
            return Message(group_id=kwargs["group_id"],
                           message=[
                               {
                                   "type": "reply",
                                   "data": {"id": kwargs["message_id"]}
                               },
                               {
                                   "type": "text",
                                   "data": {"text": "No illustrations found"}
                               }
                           ])

    def get_illust_by_tags(self, tags: str, origin: bool = False, exact: bool = False,
                           offset: int = -1, safe: bool = True) -> PixivImage:
        self.check_connection()

        if tags in self.tag_cache:
            illusts = self.tag_cache[tags]
        else:
            json_result = self.api.search_illust(tags,
                                                 search_target="exact_match_for_tags" if exact else "partial_match_for_tags",
                                                 sort="popular_desc")
            illusts = json_result["illusts"]
            self.tag_cache[tags] = illusts
        if safe:
            illusts = [illust for illust in illusts if illust["tags"][0]["name"] != "R-18"]
        else:
            illusts = [illust for illust in illusts if illust["tags"][0]["name"] == "R-18"]

        if offset == -1:
            offset = random.randint(0, len(illusts)-1)
        else:
            offset %= len(illusts)

        illust_id = illusts[offset]["id"]
        if illust_id in self.id_cache and self.id_cache[illust_id].is_origin == origin:
            return self.id_cache[illust_id]

        illust_url = illusts[offset]["meta_single_page"]["original_image_url"] if origin \
            else illusts[offset]["image_urls"]["medium"]

        image_name = illust_url.split("/")[-1]

        if image_name in self.image_cache and self.image_cache[image_name].is_origin == origin:
            return self.image_cache[image_name]

        image_path = abspath("assets/img/" + image_name)
        self.api.download(url=illust_url, path="assets/img/")
        image = PixivImage(image_path,
                           r18=not safe,
                           artist=illusts[offset]["user"]["name"],
                           artwork_id=illusts[offset]["id"],
                           title=illusts[offset]["title"],
                           is_origin=origin
                           )
        self.image_cache[image_name] = image
        self.id_cache[illust_id] = image

        return image

    def get_illust_by_tags_impl(self, args: list, kwargs: dict) -> Message:
        try:
            tags = " ".join(args)
            image = self.get_illust_by_tags(tags,
                                            origin="-ogn" in kwargs or "-origin" in kwargs,
                                            exact="-ex" in kwargs or "-exact" in kwargs,
                                            offset=max(int(kwargs.get("-o", -1)), int(kwargs.get("-offset", -1))),
                                            safe="-us" not in kwargs and "-unsafe" not in kwargs)
            return Message(group_id=kwargs["group_id"],
                           message=[
                               {
                                   "type": "reply",
                                   "data": {"id": kwargs["message_id"]}
                               },
                               {
                                   "type": "image",
                                   "data": {"file": image.as_uri(), "is_origin": 1}
                               }
                           ],
                           attached=image)
        except (ValueError, KeyError):
            return Message(group_id=kwargs["group_id"],
                           message=[
                               {
                                   "type": "reply",
                                   "data": {"id": kwargs["message_id"]}
                               },
                               {
                                   "type": "text",
                                   "data": {"text": "No illustrations found"}
                               }
                           ])

    def get_illust_info_impl(self, args: list, kwargs: dict) -> Message:
        for image in self.image_cache.values():
            if image.message_id == kwargs["earlier_text"]:
                return Message(group_id=kwargs["group_id"],
                               message=[
                                   {
                                       "type": "reply",
                                       "data": {"id": kwargs["message_id"]}
                                   },
                                   {
                                       "type": "text",
                                       "data": {"text": "Title: {}\nArtist: {}\nArtwork ID: {}".format(
                                           image.title, image.artist, image.artwork_id)}
                                   }
                               ])
        else:
            return Message(group_id=kwargs["group_id"],
                           message=[
                               {
                                   "type": "reply",
                                   "data": {"id": kwargs["message_id"]}
                               },
                               {
                                   "type": "text",
                                   "data": {"text": "Unable to locate relevant information"}
                               }
                           ])

    def get_origin_illust_impl(self, args: list, kwargs: dict):
        for image in self.image_cache.values():
            if image.message_id == kwargs["earlier_text"]:
                image = image if image.is_origin else self.get_illust_by_id(image.artwork_id, True)
                return Message(group_id=kwargs["group_id"],
                               message=[
                                   {
                                       "type": "reply",
                                       "data": {"id": kwargs["message_id"]}
                                   },
                                   {
                                       "type": "image",
                                       "data": {"file": image.as_uri()}
                                   }
                               ],
                               attached=image
                               )
        else:
            return Message(group_id=kwargs["group_id"],
                           message=[
                               {
                                   "type": "reply",
                                   "data": {"id": kwargs["message_id"]}
                               },
                               {
                                   "type": "text",
                                   "data": {"text": "No original images found"}
                               }
                           ])


pixiv_downloader = PixivDownloader()
pixiv_downloader.login(refresh_token="YR8l5NWKoZQ5jOuoJmslrXUdKDkdn-LYdQEPQhTeF0Q")

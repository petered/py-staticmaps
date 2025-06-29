# py-staticmaps
# Copyright (c) 2020 Florian Pigorsch; see /LICENSE for licensing information

import os
import pathlib
import typing
from typing import Optional

import requests
import slugify  # type: ignore

from .meta import GITHUB_URL, LIB_NAME, VERSION
from .tile_provider import TileProvider

from PIL import Image, ImageDraw, ImageFont
import io

# Global variable to store the image bytes
NO_CONNECTION_IMAGE_BYTES: Optional[bytes] = None


def textsize(text: str, font: Optional[str] = None):  # https://stackoverflow.com/a/77749307
    im = Image.new(mode="P", size=(0, 0))
    draw = ImageDraw.Draw(im)
    _, _, width, height = draw.textbbox((0, 0), text=text, font=font)
    return width, height


def get_no_connection_image_data() -> bytes:
    global NO_CONNECTION_IMAGE_BYTES
    # Check if the image data has already been generated
    if NO_CONNECTION_IMAGE_BYTES is not None:
        return NO_CONNECTION_IMAGE_BYTES

    # Create a new white image
    img = Image.new('RGB', (256, 256), color='white')
    # Get a drawing context
    d = ImageDraw.Draw(img)
    # Define the font
    try:
        font = ImageFont.load_default()
    except IOError:
        font = ImageFont.load_default()

    # Position the text in the center
    text = "Could not download\nmap tiles"
    text_width, text_height = textsize(text, font=font)
    x = (img.width - text_width) / 2
    y = (img.height - text_height) / 2

    # Draw the text
    d.text((x, y), text, font=font, fill=(225, 225, 225))

    # Save image to a bytes object to simulate file I/O
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_bytes.seek(0)  # rewind the file

    # Save the bytes data to the global variable
    NO_CONNECTION_IMAGE_BYTES = img_bytes.read()
    return NO_CONNECTION_IMAGE_BYTES


class TileDownloader:
    """A tile downloader class"""

    def __init__(self, connection_timeout: Optional[float] = None) -> None:
        self._user_agent = f"Mozilla/5.0+(compatible; {LIB_NAME}/{VERSION}; {GITHUB_URL})"
        self._sanitized_name_cache: typing.Dict[str, str] = {}
        self._connection_timeout = connection_timeout

    def set_user_agent(self, user_agent: str) -> None:
        """Set the user agent for the downloader

        :param user_agent: user agent
        :type user_agent: str
        """
        self._user_agent = user_agent

    def get(self, provider: TileProvider, cache_dir: str, zoom: int, x: int, y: int) -> typing.Optional[bytes]:
        """Get tiles

        :param provider: tile provider
        :type provider: TileProvider
        :param cache_dir: cache directory for tiles
        :type cache_dir: str
        :param zoom: zoom for static map
        :type zoom: int
        :param x: x value of center for the static map
        :type x: int
        :param y: y value of center for the static map
        :type y: int
        :return: tiles
        :rtype: typing.Optional[bytes]
        :raises RuntimeError: raises a runtime error if the the server response status is not 200
        """
        file_name = None
        if cache_dir is not None:
            file_name = self.cache_file_name(provider, cache_dir, zoom, x, y)
            if os.path.isfile(file_name):
                with open(file_name, "rb") as f:
                    return f.read()

        url = provider.url(zoom, x, y)
        if url is None:
            return None
        try:
            res = requests.get(url, headers={"user-agent": self._user_agent}, timeout=self._connection_timeout)
        except Exception as err:
            print(f"Error connecting.  Returning 'No Connection' tile: {err}")
            return get_no_connection_image_data()

        if res.status_code == 200:
            data = res.content
        else:
            raise RuntimeError(f"fetch {url} yields {res.status_code}")

        if file_name is not None:
            pathlib.Path(os.path.dirname(file_name)).mkdir(parents=True, exist_ok=True)
            with open(file_name, "wb") as f:
                f.write(data)
        return data

    def sanitized_name(self, name: str) -> str:
        """Return sanitized name

        :param name: name to sanitize
        :type name: str
        :return: sanitized name
        :rtype: str
        """
        if name in self._sanitized_name_cache:
            return self._sanitized_name_cache[name]
        sanitized = slugify.slugify(name)
        if sanitized is None:
            sanitized = "_"
        self._sanitized_name_cache[name] = sanitized
        return sanitized

    def cache_file_name(self, provider: TileProvider, cache_dir: str, zoom: int, x: int, y: int) -> str:
        """Return a cache file name

        :param provider: tile provider
        :type provider: TileProvider
        :param cache_dir: cache directory for tiles
        :type cache_dir: str
        :param zoom: zoom for static map
        :type zoom: int
        :param x: x value of center for the static map
        :type x: int
        :param y: y value of center for the static map
        :type y: int
        :return: cache file name
        :rtype: str
        """
        return os.path.join(cache_dir, self.sanitized_name(provider.name()), str(zoom), str(x), f"{y}.png")

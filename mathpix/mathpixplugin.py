import aiohttp
import json

from typing import Type

from maubot import Plugin
from maubot.handlers import event
from maubot.matrix import MaubotMessageEvent
from mautrix.crypto.attachments import decrypt_attachment
from mautrix.types import EventType, MessageType, EncryptedFile
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper

def _build_json_response(response: dict) -> str:
    html_output = '<ul>\n'
    for key, value in response.items():
        v = str(value) if key != "text" else "..."
        html_output += f'  <li><strong>{key}:</strong> {v[:40]}</li>\n'
    html_output += '</ul>'
    return html_output

def _parse_response(response: str) -> str:
    return f"<pre><code>{response}</code></pre>"


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("app_id")
        helper.copy("app_key")
        helper.copy("endpoint")


class MathpixPlugin(Plugin):

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    async def start(self) -> None:
        self.config.load_and_update()
        self.options = {
            "math_inline_delimiters": ["$", "$"],
            "math_display_delimiters": ["$$", "$$"],
            "rm_spaces": True
        }

        self.app_id = self.config["app_id"]
        self.app_key = self.config["app_key"]
        self.endpoint = self.config["endpoint"]
        self.log.info("Mathpix ocr bot started!")

    @event.on(EventType.ROOM_MESSAGE)
    async def start_ocr(self, evt: MaubotMessageEvent):
        self.log.debug("Mathpix ocr bot detect message!")
        if evt.content.msgtype != MessageType.IMAGE:
            return
        self.log.info("Mathpix ocr bot detect image message!")

        file = evt.content.file  # type: EncryptedFile
        self.log.debug(f"Mathpix ocr bot received file meta: {file}")

        await evt.react("👌")
        await evt.mark_read()

        enc_image_bytes = await self.client.download_media(file.url)

        image_bytes = decrypt_attachment(
            enc_image_bytes,
            key=file.key.key, hash=file.hashes["sha256"], iv=file.iv
        )

        try:
            response = await self.post_image(image_bytes)
            response1 = _build_json_response(response)
            response2 = _parse_response(response["text"])
            await evt.respond(response1, allow_html=True)
            await evt.respond(response2, allow_html=True)

        except Exception:
            await evt.respond("Mathpix ocr bot encountered an internal error.")

    async def post_image(self, image_bytes) -> dict:
        headers = {
            'app_id': self.app_id,
            'app_key': self.app_key
        }

        data = aiohttp.FormData()
        data.add_field('file', value=image_bytes, content_type='application/octet-stream')

        options_json = json.dumps(self.options)
        data.add_field('options_json', options_json, content_type='application/json')
        async with self.http.post(self.endpoint, headers=headers, data=data) as response:
            return await response.json()

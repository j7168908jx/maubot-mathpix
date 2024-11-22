import aiohttp
import json

from typing import Type

from maubot import Plugin
from maubot.handlers import event
from maubot.matrix import MaubotMessageEvent
from mautrix.crypto.attachments import decrypt_attachment
from mautrix.types import EventType, MessageType, EncryptedFile
from mautrix.types.event.message import MediaMessageEventContent
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper

def _build_json_response(response: dict) -> str:
    assert "text" in response, "No text in ocr server response"

    html_output = '<p><strong>Meta:</strong></p>\n<pre><code>'
    for key, value in response.items():
        v = str(value) if key != "text" else "..."
        html_output += f'  {key}: {v[:40]}\n'
    html_output += '</code></pre>\n<p><strong>Text:</strong></p>\n'
    html_output += f"<pre><code>{response['text']}</code></pre>\n"
    return html_output


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("app_id")
        helper.copy("app_key")
        helper.copy("endpoint")


class MathpixPlugin(Plugin):
    config: BaseProxyConfig

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
        if evt.content.msgtype != MessageType.IMAGE:
            self.log.debug(f"Mathpix ocr bot detect message: type: {evt.content.msgtype}")
            return
        self.log.info("Mathpix ocr bot detect image message!")

        content = evt.content
        assert isinstance(content, MediaMessageEventContent), f"Unexpected content type: {content}"

        file = content.file  # type: EncryptedFile | None
        self.log.debug(f"Mathpix ocr bot received file meta: {file}")

        await evt.mark_read()
        if file is None:
            # this is the case for unencrypted room message
            # retrieve image from content mcx url
            assert content.url is not None, "No url in content"
            image_bytes = await self.client.download_media(content.url)
            await evt.respond("Note: You are sending message in an unencrypted room. Please consider enabling end-to-end encryption in this room.")
        else:
            # encrypted room message, retreive image from encrypted file
            assert file.url is not None, "No url in encrypted file"
            enc_image_bytes = await self.client.download_media(file.url)
            image_bytes = decrypt_attachment(
                enc_image_bytes,
                key=file.key.key, hash=file.hashes["sha256"], iv=file.iv
            )
        await evt.react("👌")
        self.log.debug(f"Mathpix ocr bot received image: size {len(image_bytes)} bytes")

        try:
            response = await self.post_image(image_bytes)
            response1 = _build_json_response(response)
            await evt.respond(response1, allow_html=True)

        except Exception:
            await evt.respond("Mathpix ocr bot encountered an internal error when querying ocr server.")

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

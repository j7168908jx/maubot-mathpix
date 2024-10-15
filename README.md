# maubot-mathpix

A simple matrix plugin for [maubot](https://github.com/maubot/maubot), which calls the [Mathpix text(LaTex) OCR API](https://mathpix.com/ocr) to convert images to latex.

## Installation

Simply drag the plugin into the plugin folder, or upload it via maubot's user interface. You can download the plugin from the releases.

## Usage

Set up the `app_id` and `app_key` to your Mathpix API credentials and save it.
Directly send images to the bot, and it will respond with the latex code.

## Sample bot return

- Send read receipt
- React with emoji 👌
- Reply metadata:
    ```
    request_id: ...
    version: ...
    image_width: ...
    image_height: ...
    is_printed: ...
    is_handwritten: ...
    auto_rotate_confidence: ...
    auto_rotate_degrees: ...
    confidence: ...
    confidence_rate: ...
    text: ...
    ```
- Reply OCR result:
    ```
    My latex text:
    $$
    my equation text.
    $$
    ```

## Known Issues

- The plugin does not store the session keys and will possibly fail if manually restarted.
  - From the backend log one will see `...Failed to decrypt megolm event: no session with given ID...` as a warning.
  - It is likely caused by the lost of key for previous chat decryption. (a guess)
  - In this case, restart the bot, and users should leave the room and rejoin to get the bot to work again.

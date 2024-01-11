from googletrans import Translator, LANGUAGES
import logging

def translate_to_spanish(text):
    if not text:
        logging.warning("Received empty text for translation.")
        return ""

    translator = Translator()
    try:
        translation = translator.translate(text, src='en', dest='es')
        return translation.text
    except Exception as e:
        logging.error(f"Error during translation: {e}")
        return ""

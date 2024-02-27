import openai
from .dependencies import openai_api_key
import os

openai_api_key = os.getenv("OPENAI_API_KEY")

def summarize_with_openai_chat(text, model="gpt-3.5-turbo"):
    """
    Summarizes a given text using OpenAI's Chat Completion API.

    :param text: The text to summarize.
    :param model: The OpenAI model to use for summarization.
    :return: A summary of the provided text.
    """
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are going to generate a 1-3 sentence response summarizing each page of a bill passed in the Florida senate. You will receive the raw text of each page."},
            {"role": "user", "content": text}
        ]
    )
    content = response['choices'][0]['message']['content']
    return content


def full_summarize_with_openai_chat(full_text, model="gpt-3.5-turbo"):
    """
    Summarizes a given text using OpenAI's Chat Completion API.

    :param text: The text to summarize.
    :param model: The OpenAI model to use for summarization.
    :return: A summary of the provided text.
    """
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are going to generate a 3-4 sentence response summarizing each page of a bill passed in the florida senate. You will recieve the raw text of each page. Do not include the title of the bills in the summary or the reference numbers. do not mention bill number either. dont include HB "},
            {"role": "user", "content": f"Please summarize the following text:\n\n{full_text}"}
        ]
    )
    summary = response['choices'][0]['message']['content']
    return summary

def full_summarize_with_openai_chat_spanish(full_text, model="gpt-3.5-turbo"):
    """
    Summarizes a given text using OpenAI's Chat Completion API.

    :param text: The text to summarize.
    :param model: The OpenAI model to use for summarization.
    :return: A summary of the provided text.
    """
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "Vas a generar una respuesta de 3 a 4 oraciones que resuma cada página de un proyecto de ley aprobado en el Senado de Florida. Recibirá el texto sin formato de cada página. No incluir el título de los proyectos de ley en el resumen ni los números de referencia. Tampoco menciones el número de factura. "},
            {"role": "user", "content": f"Por favor resuma el siguiente texto:\n\n{full_text}"}
        ]
    )
    summary = response['choices'][0]['message']['content']
    return summary
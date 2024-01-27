import fitz  # PyMuPDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import openai
from .summarization import summarize_with_openai_chat
from .summarization import full_summarize_with_openai_chat
from .summarization import full_summarize_with_openai_chat_spanish
from .dependencies import openai_api_key
from .translation import translate_to_spanish
import os
import logging

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import fitz  # PyMuPDF
import os



openai.api_key = openai_api_key

def generate_pros_and_cons(full_text):
    # Generate pros
    pros_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant designed to generate pros for supporting a bill based on its summary. You must specifically have 3 Pros, seperated by numbers--no exceptions. Numbers seperated as 1) 2) 3)"},
            {"role": "user", "content": f"What are the pros of supporting this bill? make it no more than 2 sentences \n\n{full_text}"}
        ]
    )
    pros = pros_response['choices'][0]['message']['content']

    # Generate cons
    cons_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant designed to generate cons against supporting a bill based on its summary. You must have specifically 3 Cons, seperated by numbers--no excpetions. Numbers seperated as 1) 2) 3)"},
            {"role": "user", "content": f"What are the cons of supporting this bill? Make it no more than 2 sentences \n\n{full_text}"}
        ]
    )
    cons = cons_response['choices'][0]['message']['content']

    return pros, cons

def generate_pros_and_cons_spanish(full_text):
    # Generate pros
    pros_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Eres un asistente útil diseñado para generar ventajas para respaldar una factura en función de su resumen. Debes tener específicamente 3 profesionales, separados por números, sin excepciones. Números separados como 1) 2) 3)"},
            {"role": "user", "content": f"¿Cuáles son las ventajas de apoyar este proyecto de ley? que no sean más de 2 oraciones \n\n{full_text}"}
        ]
    )
    pros = pros_response['choices'][0]['message']['content']

    # Generate cons
    cons_response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Usted es un asistente útil diseñado para generar desventajas contra el respaldo de un proyecto de ley en función de su resumen. Debes tener específicamente 3 desventajas, separadas por números, sin excepciones. Números separados como 1) 2) 3)"},
            {"role": "user", "content": f"¿Cuáles son las desventajas de apoyar este proyecto de ley? Que no tenga más de 2 oraciones. \n\n{full_text}"}
        ]
    )
    cons = cons_response['choices'][0]['message']['content']

    return pros, cons


def create_summary_pdf(input_pdf_path, output_pdf_path, title):
    width, height = letter
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
    story = []

    # Add the title to the document
    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 12))

    # Extract full text from the PDF
    full_text = ""
    with fitz.open(input_pdf_path) as pdf:
        for page_num in range(len(pdf)):
            page = pdf[page_num]
            text = page.get_text()
            full_text += text + " "

    # Generate the summary, pros, and cons
    summary = full_summarize_with_openai_chat(full_text)
    pros, cons = generate_pros_and_cons(full_text)

    # Add summary, pros, and cons to the document
    story.append(Paragraph(f"<b>Summary:</b><br/>{summary}", styles['Normal']))
    story.append(Spacer(1, 12))

    # Creating a table for pros and cons
    data = [['Cons', 'Pros'], [Paragraph(cons, styles['Normal']), Paragraph(pros, styles['Normal'])]]
    col_widths = [width * 0.45, width * 0.45]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
    ]))
    story.append(t)

    # Build the PDF document
    doc.build(story)

    return os.path.abspath(output_pdf_path), summary, pros, cons

def create_summary_pdf_spanish(input_pdf_path, output_pdf_path, title):
    width, height = letter
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(output_pdf_path, pagesize=letter)
    story = []

    # Add the title to the document
    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 12))

    # Extract full text from the PDF
    full_text = ""
    with fitz.open(input_pdf_path) as pdf:
        for page_num in range(len(pdf)):
            page = pdf[page_num]
            text = page.get_text()
            full_text += text + " "

    if not full_text.strip():
        logging.error("No text extracted from PDF for translation.")
        return None

    # Generate the summary, pros, and cons in Spanish
    summary = full_summarize_with_openai_chat(full_text)
    summary_es = translate_to_spanish(summary)
    pros, cons = generate_pros_and_cons(full_text)
    pros_es = translate_to_spanish(pros)
    cons_es = translate_to_spanish(cons)

    # Add the Spanish summary, pros, and cons to the document
    story.append(Paragraph(f"<b>Summary:</b><br/>{summary_es}", styles['Normal']))
    story.append(Spacer(1, 12))

    # Define the column widths for the table
    col_widths = [width * 0.45, width * 0.45]

    # Creating a table for Spanish pros and cons
    data_es = [['Cons', 'Pros'], [Paragraph(cons_es, styles['Normal']), Paragraph(pros_es, styles['Normal'])]]
    t_es = Table(data_es, colWidths=col_widths)
    t_es.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
    ]))

    # Append the table to the story
    story.append(t_es)

    # Build the PDF document
    doc.build(story)

    return os.path.abspath(output_pdf_path), summary_es, pros_es, cons_es

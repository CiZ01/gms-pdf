from flask import Flask, request, send_file, jsonify, render_template
import os
import zipfile
from flask_cors import CORS
import shutil
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import pdf2image
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

UPLOAD_FOLDER = "/tmp/uploads"
OUTPUT_FOLDER = "/tmp/output"
ZIP_FOLDER = "/tmp/zipped"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(ZIP_FOLDER, exist_ok=True)

# Configuration
DPI = 96  # Reduced from 300 to improve speed
THREAD_COUNT = 4  # Number of parallel threads for PDF conversion


def cleanup():
    for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER, ZIP_FOLDER]:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")


def draw_notes(c, page_size, placement, style, spacing):
    # Calculate note area dimensions based on placement
    if placement in ["left", "right"]:
        slide_width = page_size[0] / 2
        notes_width = slide_width
        notes_height = page_size[1]

        if placement == "left":
            notes_x = slide_width
            slide_x = 0
        else:  # right
            notes_x = 0
            slide_x = slide_width

        notes_y = 0
        slide_y = 0
    else:
        slide_height = page_size[1] / 2
        notes_height = slide_height
        notes_width = page_size[0]

        if placement == "top":
            notes_y = 0
            slide_y = slide_height
        else:  # bottom
            notes_y = slide_height
            slide_y = 0

        notes_x = 0
        slide_x = 0

    # Draw notes background
    c.setFillColorRGB(1, 1, 1)  # White background
    c.rect(notes_x, notes_y, notes_width, notes_height, fill=1)

    # Draw grid patterns
    c.setFillColorRGB(0, 0, 0)  # Black patterns
    if style == "lines":
        y = notes_y + 40
        while y < notes_y + notes_height - 20:
            c.line(notes_x + 20, y, notes_x + notes_width - 20, y)
            y += spacing
    elif style == "dots":
        for y in range(int(notes_y + 40), int(notes_y + notes_height - 20), spacing):
            for x in range(int(notes_x + 20), int(notes_x + notes_width - 20), spacing):
                c.circle(x, y, 0.5, fill=1)
    elif style == "squares":
        size = spacing // 2
        for y in range(
            int(notes_y + 40), int(notes_y + notes_height - 20 - size), spacing
        ):
            for x in range(
                int(notes_x + 20), int(notes_x + notes_width - 20 - size), spacing
            ):
                c.rect(x, y, size, size)

    return (
        slide_x,
        slide_y,
        slide_width if placement in ["left", "right"] else page_size[0],
        slide_height if placement in ["top", "bottom"] else page_size[1],
    )


def process_page(args):
    img, page_size, placement, style, spacing = args
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=page_size)

    # First draw the notes area
    draw_notes(c, page_size, placement, style, spacing)

    # Then draw the slide image on top
    slide_rect = draw_notes(c, page_size, placement, style, spacing)
    img_reader = ImageReader(img)
    c.drawImage(
        img_reader,
        slide_rect[0],
        slide_rect[1],
        width=slide_rect[2],
        height=slide_rect[3],
        preserveAspectRatio=True,
        mask="auto",
    )

    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer


def generate_notebook_pdf(
    input_pdf, output_pdf, placement="left", style="lines", spacing=20
):
    # Read PDF metadata
    reader = PdfReader(input_pdf)
    num_pages = len(reader.pages)
    if num_pages == 0:
        raise ValueError("Empty PDF file")

    # Get page dimensions from first page
    first_page = reader.pages[0]
    orig_width = first_page.mediabox.width
    orig_height = first_page.mediabox.height

    # Calculate new page size
    if placement in ["left", "right"]:
        page_size = (orig_width * 2, orig_height)
    else:
        page_size = (orig_width, orig_height * 2)

    # Convert all pages to images in parallel
    with BytesIO() as pdf_buffer:
        with open(input_pdf, "rb") as f:
            pdf_buffer.write(f.read())

        images = pdf2image.convert_from_bytes(
            pdf_buffer.getvalue(),
            dpi=DPI,
            thread_count=THREAD_COUNT,
            fmt="jpeg",  # Faster than PNG
        )

    # Process pages in parallel
    with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
        args = [(img, page_size, placement, style, spacing) for img in images]
        page_buffers = list(executor.map(process_page, args))

    # Merge all pages into final PDF
    with open(output_pdf, "wb") as f:
        writer = PdfWriter()
        for buffer in page_buffers:
            reader = PdfReader(buffer)
            writer.add_page(reader.pages[0])
        writer.write(f)


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "pdf" not in request.files:
        return jsonify({"error": "No PDF uploaded"}), 400

    placement = request.form.get("placement", "left")
    style = request.form.get("style", "lines")
    spacing = int(request.form.get("spacing", 20))

    files = request.files.getlist("pdf")
    outputs = []

    with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
        futures = []
        for file in files:
            input_path = os.path.join(UPLOAD_FOLDER, file.filename)
            output_path = os.path.join(OUTPUT_FOLDER, file.filename)
            file.save(input_path)
            futures.append(
                executor.submit(
                    generate_notebook_pdf,
                    input_path,
                    output_path,
                    placement,
                    style,
                    spacing,
                )
            )

        for future in futures:
            future.result()
            outputs.append(output_path)

    if len(outputs) == 1:
        return send_file(outputs[0], as_attachment=True, mimetype="application/pdf")

    zip_path = os.path.join(ZIP_FOLDER, "notebooks.zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for f in outputs:
            zipf.write(f, os.path.basename(f))

    cleanup()
    return send_file(zip_path, as_attachment=True, mimetype="application/zip")


@app.route("/health")
def health_check():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

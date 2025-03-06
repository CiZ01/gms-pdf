from flask import Flask, request, send_file, jsonify, render_template
import fitz  # PyMuPDF
import os
import zipfile
from flask_cors import CORS
import os
import shutil


app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)  # Allow CORS for API

UPLOAD_FOLDER = "/tmp/uploads"
OUTPUT_FOLDER = "/tmp/output"
ZIP_FOLDER = "/tmp/zipped"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(ZIP_FOLDER, exist_ok=True)


def cleanup():
    """Deletes all files inside upload, output, and zip folders."""
    folders = ["uploads", "output", "zipped"]  # Adjust folder names if needed

    for folder in folders:
        folder_path = os.path.join(os.getcwd(), folder)
        if os.path.exists(folder_path):
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)  # Remove file
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)  # Remove directory
                except Exception as e:
                    print(f"❌ Error deleting {file_path}: {str(e)}")


def generate_notebook_pdf(
    input_pdf, output_pdf, placement="left", style="lines", spacing=20
):
    doc = fitz.open(input_pdf)
    new_doc = fitz.open()

    for page in doc:
        width, height = page.rect.width, page.rect.height

        if placement in ["left", "right"]:
            new_width = width * 2
            new_height = height
        else:
            new_width = width
            new_height = height * 2

        new_page = new_doc.new_page(width=new_width, height=new_height)

        if placement == "left":
            slide_rect = fitz.Rect(width, 0, width * 2, height)
            note_area = fitz.Rect(0, 0, width, height)
        elif placement == "right":
            slide_rect = fitz.Rect(0, 0, width, height)
            note_area = fitz.Rect(width, 0, width * 2, height)
        elif placement == "top":
            slide_rect = fitz.Rect(0, 0, width, height)
            note_area = fitz.Rect(0, height, width, height * 2)
        elif placement == "bottom":
            slide_rect = fitz.Rect(0, height, width, height * 2)
            note_area = fitz.Rect(0, 0, width, height)
        else:
            raise ValueError(
                "Invalid placement, must be one of ['left', 'right', 'top', 'bottom']"
            )
        new_page.show_pdf_page(slide_rect, doc, page.number)

        if style == "lines":
            for y in range(int(note_area.y0) + 40, int(note_area.y1) - 20, spacing):
                new_page.draw_line((note_area.x0 + 20, y), (note_area.x1 - 20, y))
        elif style == "dots":
            for y in range(int(note_area.y0) + 40, int(note_area.y1) - 20, spacing):
                for x in range(int(note_area.x0) + 20, int(note_area.x1) - 20, spacing):
                    new_page.draw_rect(fitz.Rect(x, y, x + 1, y + 1), fill=(0, 0, 0))
        elif style == "squares":
            for y in range(int(note_area.y0) + 40, int(note_area.y1) - 20, spacing):
                for x in range(int(note_area.x0) + 20, int(note_area.x1) - 20, spacing):
                    new_page.draw_rect(
                        fitz.Rect(x, y, x + spacing, y + spacing), color=(0, 0, 0)
                    )
        else:
            raise ValueError(
                "Invalid style, must be one of ['lines', 'dots', 'squares']"
            )

    new_doc.save(output_pdf)
    new_doc.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/upload", methods=["POST"])
def upload_pdf():
    if "pdf" not in request.files:
        return jsonify({"error": "No PDF file uploaded"}), 400

    placement = request.form.get("placement", "left")
    style = request.form.get("style", "lines")
    spacing = int(request.form.get("spacing", 20))

    files = request.files.getlist("pdf")
    output_files = []

    for file in files:
        input_pdf_path = os.path.join(UPLOAD_FOLDER, file.filename)
        output_pdf_path = os.path.join(OUTPUT_FOLDER, file.filename)

        file.save(input_pdf_path)
        generate_notebook_pdf(
            input_pdf_path, output_pdf_path, placement, style, spacing
        )
        output_files.append(output_pdf_path)

    if len(output_files) == 1:
        return send_file(
            output_files[0], as_attachment=True, mimetype="application/pdf"
        )

    zip_path = os.path.join(ZIP_FOLDER, "notebooks.zip")
    with zipfile.ZipFile(zip_path, "w") as zipf:
        for file_path in output_files:
            zipf.write(file_path, os.path.basename(file_path))

    send_file(zip_path, as_attachment=True, mimetype="application/zip")
    cleanup()
    return


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)

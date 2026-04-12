import fitz  # PyMuPDF
import base64
import os
import io
from flask import Flask, render_template, request, send_file, jsonify
from PIL import Image, ImageOps

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
TEMP_PDF = os.path.join(UPLOAD_FOLDER, "temp.pdf")


def make_transparent(image_bytes):
    img = Image.open(io.BytesIO(image_bytes))
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGBA")
    datas = img.getdata()
    new_data = []
    for item in datas:
        if item[0] > 220 and item[1] > 220 and item[2] > 220:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
    img.putdata(new_data)
    output = io.BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()


def normalize_pdf_rotation(pdf_path):
    """
    Remove /Rotate flags from every page by baking the rotation into the
    page content via show_pdf_page.  After this, all pages have rotation=0,
    and visual coordinates map 1-to-1 to insert_image/insert_text coordinates.

    This is a no-op for PDFs that have no rotated pages.
    """
    src = fitz.open(pdf_path)

    # Check if any page has a non-zero rotation
    needs_normalization = any(page.rotation != 0 for page in src)
    if not needs_normalization:
        src.close()
        return

    print(f"[INFO] Normalizing PDF rotation for {pdf_path}")
    for page in src:
        if page.rotation != 0:
            print(f"  Page {page.number}: rotation={page.rotation}")

    # Build a new PDF with all rotations baked into the content stream.
    # show_pdf_page renders the source page (including its /Rotate) as a
    # Form XObject on the destination page, which has rotation=0.
    # This is vector-based — no rasterisation, no quality loss.
    dst = fitz.open()
    for page in src:
        r = page.rect  # visual (post-rotation) rect
        new_page = dst.new_page(width=r.width, height=r.height)
        new_page.show_pdf_page(new_page.rect, src, page.number)

    # Write back to the same path
    normalized_bytes = dst.tobytes()
    dst.close()
    src.close()

    with open(pdf_path, 'wb') as f:
        f.write(normalized_bytes)

    print(f"[INFO] Normalization complete — all pages now rotation=0")


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    file = request.files['pdf']
    file.save(TEMP_PDF)

    # ── Normalise rotations BEFORE rendering previews ──────────────────────
    # After this call every page in TEMP_PDF has rotation=0, so the visual
    # coordinate space and the raw content-stream space are identical.
    # This makes insert_image / insert_text completely straightforward.
    normalize_pdf_rotation(TEMP_PDF)

    doc = fitz.open(TEMP_PDF)
    pages = []

    for i in range(len(doc)):
        page = doc.load_page(i)
        pix = page.get_pixmap()
        img_data = base64.b64encode(pix.tobytes("png")).decode('utf-8')

        rect = page.rect

        pages.append({
            "index":      i,
            "image":      f"data:image/png;base64,{img_data}",
            "width":      pix.width,
            "height":     pix.height,
            "pdf_width":  rect.width,
            "pdf_height": rect.height,
        })

    return jsonify({"pages": pages})


@app.route('/process_sig', methods=['POST'])
def process_sig():
    file = request.files['signature']
    transparent_img = make_transparent(file.read())
    base64_img = base64.b64encode(transparent_img).decode('utf-8')
    return jsonify({"image": f"data:image/png;base64,{base64_img}"})


@app.route('/save_pdf', methods=['POST'])
def save_pdf():
    data = request.json
    doc = fitz.open(TEMP_PDF)

    for obj in data['elements']:
        page = doc[obj['page']]

        # ── Normalise the page content stream ─────────────────────────────
        #
        # Some PDFs (especially from Google Docs) embed a coordinate
        # transformation matrix at the start of their content stream, e.g.:
        #
        #     1 0 0 -1 0 792 cm      ← flips Y-axis (bottom-up to top-down)
        #
        # PyMuPDF's insert_image / insert_text append a NEW content stream
        # to the page, but the existing CTM leaks into it, causing inserted
        # content to appear upside-down and at the wrong position.
        #
        # clean_contents() wraps the existing content in a q…Q (save/restore)
        # block so the CTM is scoped and cannot affect subsequently inserted
        # content.  This call is lightweight and safe on all PDFs.
        # ──────────────────────────────────────────────────────────────────
        page.clean_contents()
        #
        # Because normalize_pdf_rotation() has already removed all /Rotate
        # flags, page.rotation is guaranteed to be 0 for every page.
        # The visual coordinate space (what the user sees on the canvas)
        # maps 1-to-1 to the raw PDF content-stream space.
        #
        # The frontend has already scaled canvas-pixel values to PDF-point
        # values via (pdf_width / canvas_width).  We just use them directly.
        # ───────────────────────────────────────────────────────────────────

        if obj['type'] == 'image':
            rect = fitz.Rect(
                float(obj['x']),
                float(obj['y']),
                float(obj['x'] + obj['w']),
                float(obj['y'] + obj['h'])
            )

            print(f"[DEBUG] image page={obj['page']} rect={rect}")

            img_bytes = base64.b64decode(obj['data'].split(',')[1])
            page.insert_image(rect, stream=img_bytes)

        elif obj['type'] == 'text':
            point = fitz.Point(
                float(obj['x']),
                float(obj['y']) + float(obj['size'])
            )

            print(f"[DEBUG] text page={obj['page']} point={point}")

            page.insert_text(
                point,
                obj['data'],
                fontsize=obj['size'],
                color=(0, 0, 0)
            )

    out_path = os.path.join(UPLOAD_FOLDER, "signed.pdf")
    doc.save(out_path)
    doc.close()

    return jsonify({"url": "/download"})


@app.route('/download')
def download():
    return send_file(os.path.join(UPLOAD_FOLDER, "signed.pdf"), as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True)
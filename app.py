import fitz  # PyMuPDF
import base64
import os
import io
from flask import Flask, render_template, request, send_file, jsonify
from PIL import Image

app = Flask(__name__)
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
TEMP_PDF = os.path.join(UPLOAD_FOLDER, "temp.pdf")

def make_transparent(image_bytes):
    """Removes white backgrounds from signatures."""
    img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    datas = img.getdata()
    new_data = []
    for item in datas:
        # If pixel is white/near-white, make it transparent
        if item[0] > 220 and item[1] > 220 and item[2] > 220:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
    img.putdata(new_data)
    output = io.BytesIO()
    img.save(output, format="PNG")
    return output.getvalue()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload_pdf', methods=['POST'])
def upload_pdf():
    file = request.files['pdf']
    file.save(TEMP_PDF)
    doc = fitz.open(TEMP_PDF)
    pages = []
    for i in range(len(doc)):
        page = doc.load_page(i)
        pix = page.get_pixmap()
        img_data = base64.b64encode(pix.tobytes("png")).decode('utf-8')
        pages.append({
            "index": i, 
            "image": f"data:image/png;base64,{img_data}", 
            "width": pix.width, 
            "height": pix.height
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
        if obj['type'] == 'image':
            rect = fitz.Rect(obj['x'], obj['y'], obj['x'] + obj['w'], obj['y'] + obj['h'])
            img_bytes = base64.b64decode(obj['data'].split(',')[1])
            page.insert_image(rect, stream=img_bytes)
        elif obj['type'] == 'text':
            # PDF coordinates start from bottom-left for text, adjust with h
            point = fitz.Point(obj['x'], obj['y'] + (obj['h'] * 0.8))
            page.insert_text(point, obj['data'], fontsize=obj['size'], color=(0, 0, 0))
    
    out_path = os.path.join(UPLOAD_FOLDER, "signed.pdf")
    doc.save(out_path)
    doc.close()
    return jsonify({"url": "/download"})

@app.route('/download')
def download():
    return send_file(os.path.join(UPLOAD_FOLDER, "signed.pdf"), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
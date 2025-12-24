# Signify - Python PDF Signer

A lightweight, web-based PDF signing application built with **Python (Flask)** and **Fabric.js**. This tool allows users to upload PDFs, add transparent signatures, insert text, and manage signatures across multiple pages with ease.



## Features
- **PDF Upload & Rendering:** View multi-page PDFs directly in your browser.
- **Transparent Signatures:** Automatically removes white backgrounds from uploaded signature images.
- **Draggable & Resizable:** Precisely position and scale your signature or text.
- **Cross-Page Copy/Paste:** Copy a signature on one page and paste it onto any other page (Ctrl+C / Ctrl+V).
- **Text Tool:** Add names, dates, or custom annotations to any page.
- **Secure Processing:** PDF manipulation is handled on the server using `PyMuPDF`.

---

## Getting Started

### 1. Prerequisites
- Python 3.8 or higher
- Pip (Python package manager)

### 2. Installation
Clone the repository and install the dependencies:
```bash
git clone [https://github.com/manjoor8/signify.git](https://github.com/manjoor8/signify.git)
cd signify
pip install -r requirements.txt
```
### 3. Create a Virtual Environment (Recommended)
```bash
# Windows
python -m venv venv
venv\Scripts\activate
```

# Mac/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```


### 5. Run the Application
```bash
python app.py
Visit http://127.0.0.1:5000 in your web browser.
```


const canvas = new fabric.Canvas('pdf-canvas');

let pdfPages = [];
let currentPage = 0;
let elementStore = {};
let clipboard = null;

// Upload PDF
document.getElementById('pdf-file').onchange = async (e) => {
    const formData = new FormData();
    formData.append('pdf', e.target.files[0]);

    const res = await fetch('/upload_pdf', { method: 'POST', body: formData });
    const data = await res.json();

    pdfPages = data.pages;
    elementStore = {};

    document.getElementById('page-nav').classList.remove('d-none');

    renderPage(0);
};

// Upload Signature
document.getElementById('sig-file').onchange = async (e) => {
    const formData = new FormData();
    formData.append('signature', e.target.files[0]);

    const res = await fetch('/process_sig', { method: 'POST', body: formData });
    const data = await res.json();

    fabric.Image.fromURL(data.image, (img) => {
        img.scaleToWidth(150);
        img.set({
            left: 50,
            top: 50,
            originX: 'left',
            originY: 'top',
            cornerColor: '#0d6efd'
        });
        canvas.add(img);
        canvas.setActiveObject(img);
    });
};

// Add text
function addText() {
    const val = document.getElementById('text-input').value;
    if (!val) return;

    const text = new fabric.IText(val, {
        left: 100,
        top: 100,
        fontSize: 20,
        originX: 'left',
        originY: 'top'
    });

    canvas.add(text);
    document.getElementById('text-input').value = '';
}

// Render page
function renderPage(idx) {
    saveState();

    currentPage = idx;
    const page = pdfPages[idx];

    canvas.clear();
    canvas.setDimensions({ width: page.width, height: page.height });

    fabric.Image.fromURL(page.image, (img) => {
        canvas.setBackgroundImage(img, canvas.renderAll.bind(canvas));

        if (elementStore[idx]) {
            elementStore[idx].forEach(obj => {
                if (obj.type === 'image') {
                    fabric.Image.fromURL(obj.data, (s) => {
                        s.set({
                            left: obj.x,
                            top: obj.y,
                            scaleX: obj.sw,
                            scaleY: obj.sh,
                            originX: 'left',
                            originY: 'top'
                        });
                        canvas.add(s);
                    });
                } else {
                    const t = new fabric.IText(obj.data, {
                        left: obj.x,
                        top: obj.y,
                        fontSize: obj.size,
                        originX: 'left',
                        originY: 'top'
                    });
                    canvas.add(t);
                }
            });
        }
    });

    document.getElementById('page-num').innerText =
        `Page ${idx + 1} / ${pdfPages.length}`;
}

// Save state (FIXED)
function saveState() {
    if (pdfPages.length === 0) return;

    const objects = canvas.getObjects().filter(o => o !== canvas.backgroundImage);

    elementStore[currentPage] = objects.map(o => {

        o.setCoords();
        const bounds = o.getBoundingRect(true);

        return {
            type: o.type === 'image' ? 'image' : 'text',
            x: bounds.left,
            y: bounds.top,
            w: bounds.width,
            h: bounds.height,
            sw: o.scaleX || 1,
            sh: o.scaleY || 1,
            data: o.type === 'image' ? o._element.src : o.text,
            size: o.fontSize || 20
        };
    });
}

// Navigation
function changePage(dir) {
    let n = currentPage + dir;
    if (n >= 0 && n < pdfPages.length) {
        renderPage(n);
    }
}

// Delete
function deleteSelected() {
    canvas.getActiveObjects().forEach(obj => canvas.remove(obj));
    canvas.discardActiveObject().renderAll();
}

// Copy / Paste
window.addEventListener('keydown', (e) => {
    if (document.activeElement.tagName === 'INPUT') return;

    if (e.ctrlKey && e.key === 'c') {
        const active = canvas.getActiveObject();
        if (active) active.clone(cloned => clipboard = cloned);
    }

    if (e.ctrlKey && e.key === 'v' && clipboard) {
        clipboard.clone(cloned => {
            cloned.set({
                left: cloned.left + 15,
                top: cloned.top + 15
            });
            canvas.add(cloned);
            canvas.setActiveObject(cloned);
        });
    }

    if (e.key === "Delete" || e.key === "Backspace") deleteSelected();
});

// Download
async function downloadSigned() {
    saveState();

    let allElements = [];

    for (let p in elementStore) {
        const page = pdfPages[p];

        // Scale canvas pixels → PDF points.
        // After upload, the backend normalises all pages to rotation=0,
        // so visual space = raw PDF space.  Simple linear scaling is all
        // that's needed.
        const scaleX = page.pdf_width  / page.width;
        const scaleY = page.pdf_height / page.height;

        elementStore[p].forEach(el => {
            const pdfX = el.x * scaleX;
            const pdfY = el.y * scaleY;
            const pdfW = el.w * scaleX;
            const pdfH = el.h * scaleY;

            console.log(`[DEBUG] p=${p} ` +
                        `canvas(${el.x.toFixed(1)},${el.y.toFixed(1)}) → ` +
                        `pdf(${pdfX.toFixed(1)},${pdfY.toFixed(1)}) ` +
                        `size(${pdfW.toFixed(1)}×${pdfH.toFixed(1)})`);

            allElements.push({
                ...el,
                page: parseInt(p),
                x: pdfX,
                y: pdfY,
                w: pdfW,
                h: pdfH,
                // Font size must account for both fabric scaling (user resize)
                // and canvas→PDF coordinate scaling
                size: el.size * (el.sh || 1) * scaleY
            });
        });
    }

    const res = await fetch('/save_pdf', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ elements: allElements })
    });

    const data = await res.json();
    window.location.href = data.url;
}
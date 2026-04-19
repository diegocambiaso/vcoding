#!/usr/bin/env python3
import http.server
import socketserver
import os
import io
import json
import cgi
import uuid
from pathlib import Path
from PIL import Image

PORT = 8080
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
CONVERTED_DIR = BASE_DIR / "converted"

UPLOAD_DIR.mkdir(exist_ok=True)
CONVERTED_DIR.mkdir(exist_ok=True)

SUPPORTED_FORMATS = {"jpg": "JPEG", "jpeg": "JPEG", "png": "PNG", "gif": "GIF", "webp": "WEBP"}

HTML = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Conversor de Imágenes</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',sans-serif;background:#0f172a;color:#e2e8f0;min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px}
    .card{background:#1e293b;border-radius:16px;padding:40px;max-width:600px;width:100%;box-shadow:0 25px 50px rgba(0,0,0,.5)}
    h1{font-size:1.8rem;font-weight:700;color:#f8fafc;margin-bottom:6px}
    .subtitle{color:#94a3b8;font-size:.9rem;margin-bottom:32px}
    .drop-zone{border:2px dashed #334155;border-radius:12px;padding:40px;text-align:center;cursor:pointer;transition:all .2s;position:relative;background:#0f172a}
    .drop-zone:hover,.drop-zone.dragover{border-color:#6366f1;background:#1e1b4b}
    .drop-zone input[type=file]{position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%}
    .drop-icon{font-size:3rem;margin-bottom:12px}
    .drop-text{color:#94a3b8;font-size:.95rem}
    .drop-text strong{color:#e2e8f0}
    .preview-area{margin-top:24px;display:none}
    .preview-img{max-width:100%;max-height:200px;border-radius:8px;object-fit:contain;display:block;margin:0 auto}
    .file-info{text-align:center;margin-top:10px;font-size:.85rem;color:#64748b}
    .format-section{margin-top:24px}
    label.section-label{display:block;font-size:.85rem;font-weight:600;color:#94a3b8;text-transform:uppercase;letter-spacing:.05em;margin-bottom:12px}
    .formats{display:flex;gap:10px;flex-wrap:wrap}
    .format-btn{flex:1;min-width:80px;padding:12px;border:2px solid #334155;background:transparent;color:#94a3b8;border-radius:10px;cursor:pointer;font-size:.9rem;font-weight:600;transition:all .2s;text-transform:uppercase}
    .format-btn:hover{border-color:#6366f1;color:#a5b4fc}
    .format-btn.selected{border-color:#6366f1;background:#4f46e5;color:#fff}
    .convert-btn{margin-top:28px;width:100%;padding:14px;background:#4f46e5;color:#fff;border:none;border-radius:10px;font-size:1rem;font-weight:700;cursor:pointer;transition:background .2s;letter-spacing:.02em}
    .convert-btn:hover{background:#4338ca}
    .convert-btn:disabled{background:#334155;color:#64748b;cursor:not-allowed}
    .result{margin-top:24px;display:none}
    .result-success{background:#064e3b;border:1px solid #065f46;border-radius:10px;padding:16px;display:flex;align-items:center;gap:12px}
    .result-error{background:#450a0a;border:1px solid #7f1d1d;border-radius:10px;padding:16px;display:flex;align-items:center;gap:12px}
    .result-icon{font-size:1.5rem}
    .result-text{flex:1;font-size:.9rem}
    .download-btn{display:inline-block;margin-top:10px;padding:8px 16px;background:#10b981;color:#fff;border-radius:8px;text-decoration:none;font-weight:600;font-size:.85rem}
    .download-btn:hover{background:#059669}
    .spinner{display:none;width:20px;height:20px;border:3px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .8s linear infinite;margin:0 auto}
    @keyframes spin{to{transform:rotate(360deg)}}
  </style>
</head>
<body>
<div class="card">
  <h1>Conversor de Imágenes</h1>
  <p class="subtitle">Convierte entre JPG, PNG, GIF y WEBP fácilmente</p>

  <div class="drop-zone" id="dropZone">
    <input type="file" id="fileInput" accept=".jpg,.jpeg,.png,.gif,.webp" />
    <div class="drop-icon">🖼️</div>
    <div class="drop-text"><strong>Arrastra una imagen aquí</strong><br/>o haz clic para seleccionar</div>
  </div>

  <div class="preview-area" id="previewArea">
    <img id="previewImg" class="preview-img" src="" alt="Vista previa"/>
    <p class="file-info" id="fileInfo"></p>
  </div>

  <div class="format-section">
    <label class="section-label">Formato de salida</label>
    <div class="formats">
      <button class="format-btn" data-fmt="jpg">JPG</button>
      <button class="format-btn" data-fmt="png">PNG</button>
      <button class="format-btn" data-fmt="gif">GIF</button>
      <button class="format-btn" data-fmt="webp">WEBP</button>
    </div>
  </div>

  <button class="convert-btn" id="convertBtn" disabled>Selecciona una imagen y un formato</button>

  <div class="result" id="result"></div>
</div>

<script>
  let selectedFile = null;
  let selectedFormat = null;

  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  const previewArea = document.getElementById('previewArea');
  const previewImg = document.getElementById('previewImg');
  const fileInfo = document.getElementById('fileInfo');
  const convertBtn = document.getElementById('convertBtn');
  const resultDiv = document.getElementById('result');

  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('dragover'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('dragover'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault();
    dropZone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  });
  fileInput.addEventListener('change', () => { if (fileInput.files[0]) handleFile(fileInput.files[0]); });

  function handleFile(file) {
    const validTypes = ['image/jpeg','image/png','image/gif','image/webp'];
    if (!validTypes.includes(file.type)) {
      showResult('error', '❌ Formato no soportado. Usa JPG, PNG, GIF o WEBP.');
      return;
    }
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = e => {
      previewImg.src = e.target.result;
      previewArea.style.display = 'block';
      const sizeMB = (file.size / 1024 / 1024).toFixed(2);
      fileInfo.textContent = `${file.name} · ${sizeMB} MB`;
    };
    reader.readAsDataURL(file);
    resultDiv.style.display = 'none';
    updateBtn();
  }

  document.querySelectorAll('.format-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.format-btn').forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
      selectedFormat = btn.dataset.fmt;
      updateBtn();
    });
  });

  function updateBtn() {
    if (selectedFile && selectedFormat) {
      convertBtn.disabled = false;
      convertBtn.textContent = `Convertir a ${selectedFormat.toUpperCase()}`;
    } else if (!selectedFile) {
      convertBtn.disabled = true;
      convertBtn.textContent = 'Selecciona una imagen y un formato';
    } else {
      convertBtn.disabled = true;
      convertBtn.textContent = 'Selecciona el formato de salida';
    }
  }

  convertBtn.addEventListener('click', async () => {
    if (!selectedFile || !selectedFormat) return;
    convertBtn.disabled = true;
    convertBtn.innerHTML = '<div class="spinner" style="display:inline-block"></div>';

    const formData = new FormData();
    formData.append('file', selectedFile);
    formData.append('format', selectedFormat);

    try {
      const res = await fetch('/convert', { method: 'POST', body: formData });
      const data = await res.json();
      if (data.success) {
        showResult('success', `✅ Conversión exitosa: <strong>${data.filename}</strong>
          <br/><a class="download-btn" href="/download/${data.filename}" download>⬇️ Descargar</a>`);
      } else {
        showResult('error', `❌ Error: ${data.error}`);
      }
    } catch(e) {
      showResult('error', '❌ Error de conexión con el servidor.');
    }

    convertBtn.disabled = false;
    updateBtn();
  });

  function showResult(type, html) {
    resultDiv.style.display = 'block';
    const cls = type === 'success' ? 'result-success' : 'result-error';
    resultDiv.innerHTML = `<div class="${cls}"><div class="result-text">${html}</div></div>`;
  }
</script>
</body>
</html>"""


class ImageConverterHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {format % args}")

    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode("utf-8"))

        elif self.path.startswith("/download/"):
            filename = self.path[len("/download/"):]
            filepath = CONVERTED_DIR / filename
            if not filepath.exists() or not filepath.is_file():
                self._send_json(404, {"error": "Archivo no encontrado"})
                return
            ext = filepath.suffix.lower().lstrip(".")
            mime_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                        "gif": "image/gif", "webp": "image/webp"}
            mime = mime_map.get(ext, "application/octet-stream")
            data = filepath.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            self._send_json(404, {"error": "No encontrado"})

    def do_POST(self):
        if self.path != "/convert":
            self._send_json(404, {"error": "Ruta no encontrada"})
            return

        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self._send_json(400, {"error": "Se requiere multipart/form-data"})
            return

        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": content_type},
            )

            file_item = form["file"]
            target_fmt = form.getvalue("format", "").lower().strip()

            if target_fmt not in SUPPORTED_FORMATS:
                self._send_json(400, {"error": f"Formato '{target_fmt}' no soportado"})
                return

            image_data = file_item.file.read()
            img = Image.open(io.BytesIO(image_data))

            pil_format = SUPPORTED_FORMATS[target_fmt]
            out_ext = "jpg" if target_fmt == "jpeg" else target_fmt
            out_name = f"{uuid.uuid4().hex}.{out_ext}"
            out_path = CONVERTED_DIR / out_name

            save_kwargs = {}
            if pil_format == "JPEG":
                if img.mode in ("RGBA", "LA", "P"):
                    img = img.convert("RGB")
                save_kwargs["quality"] = 92
                save_kwargs["optimize"] = True
            elif pil_format == "PNG":
                save_kwargs["optimize"] = True
            elif pil_format == "GIF":
                if img.mode != "P":
                    img = img.convert("P", palette=Image.ADAPTIVE)
            elif pil_format == "WEBP":
                save_kwargs["quality"] = 90

            img.save(out_path, format=pil_format, **save_kwargs)
            self._send_json(200, {"success": True, "filename": out_name})

        except KeyError:
            self._send_json(400, {"error": "No se recibió ningún archivo"})
        except Exception as e:
            self._send_json(500, {"error": str(e)})

    def _send_json(self, code, data):
        body = json.dumps(data).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), ImageConverterHandler) as httpd:
        httpd.allow_reuse_address = True
        print(f"Conversor de imágenes corriendo en http://localhost:{PORT}")
        print("Presiona Ctrl+C para detener.")
        httpd.serve_forever()

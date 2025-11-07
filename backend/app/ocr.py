import easyocr
import tempfile
import os

# instantiate reader once
# English only for prototype; add languages as needed
reader = easyocr.Reader(['en'], gpu=False)

def extract_text_from_image_bytes(file_bytes: bytes):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(file_bytes)
        tmp.flush()
        tmp_path = tmp.name
    try:
        result = reader.readtext(tmp_path, detail=1)
        # result entries: (bbox, text, conf)
        text = "\n".join([r[1] for r in result])
        return text, result
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

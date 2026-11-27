"""Offline localhost UI and optional installed Tesseract image OCR."""
from __future__ import annotations
import base64
import binascii
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import json
import os
from pathlib import Path
import subprocess
import tempfile
from urllib.parse import urlsplit
from engine import analyze

ROOT=Path(__file__).resolve().parent
MAX_REQUEST=13_000_000
MAX_IMAGE=8_000_000

def extract_picture(data_url:str)->str:
    if not isinstance(data_url,str) or "," not in data_url:
        raise ValueError("تصویر معتبر دریافت نشد")
    header,encoded=data_url.split(",",1)
    types={"data:image/png;base64":".png","data:image/jpeg;base64":".jpg","data:image/webp;base64":".webp"}
    if header not in types:raise ValueError("فقط PNG، JPEG و WEBP مجاز است")
    if len(encoded)>MAX_IMAGE*4//3+8:raise ValueError("حجم تصویر بیش از حد مجاز است")
    try:raw=base64.b64decode(encoded,validate=True)
    except (binascii.Error,ValueError):raise ValueError("کدگذاری تصویر نامعتبر است")
    if not raw or len(raw)>MAX_IMAGE:raise ValueError("تصویر بیش از حد بزرگ یا خالی است")
    magic={".png":raw.startswith(b"\x89PNG\r\n\x1a\n"),".jpg":raw.startswith(b"\xff\xd8\xff"),
           ".webp":raw.startswith(b"RIFF") and raw[8:12]==b"WEBP"}
    if not magic[types[header]]:raise ValueError("نوع فایل با محتوای تصویر یکسان نیست")
    with tempfile.TemporaryDirectory(prefix="agrinest_lab_") as d:
        path=Path(d)/("sample"+types[header]);path.write_bytes(raw)
        try:
            p=subprocess.run([os.environ.get("TESSERACT_CMD","tesseract"),str(path),"stdout","-l",
                              os.environ.get("TESSERACT_LANG","fas+eng"),"--psm","6"],
                             capture_output=True,text=True,timeout=75,check=False)
        except FileNotFoundError:raise ValueError("Tesseract روی دستگاه نصب نشده است؛ از ورودی متن استفاده کنید")
        except subprocess.TimeoutExpired:raise ValueError("زمان تشخیص تصویر به پایان رسید")
        if p.returncode:raise ValueError("مدل OCR اجرا نشد؛ زبان فارسی/انگلیسی و نصب Tesseract را بررسی کنید")
        return p.stdout[:100_000]

class Handler(BaseHTTPRequestHandler):
    def respond(self,code:int,obj:dict)->None:
        payload=json.dumps(obj,ensure_ascii=False).encode("utf-8")
        self.send_response(code);self.send_header("Content-Type","application/json; charset=utf-8")
        self.send_header("Cache-Control","no-store");self.send_header("Content-Length",str(len(payload)))
        self.end_headers();self.wfile.write(payload)
    def do_GET(self)->None:
        if urlsplit(self.path).path not in ("/","/index.html"):return self.respond(404,{"error":"یافت نشد"})
        contents=(ROOT/"web"/"index.html").read_bytes()
        self.send_response(200);self.send_header("Content-Type","text/html; charset=utf-8")
        self.send_header("Content-Length",str(len(contents)));self.end_headers();self.wfile.write(contents)
    def do_POST(self)->None:
        if urlsplit(self.path).path!="/api/analyze":return self.respond(404,{"error":"یافت نشد"})
        try:
            n=int(self.headers.get("Content-Length","0"))
            if n<1 or n>MAX_REQUEST:raise ValueError("درخواست خالی یا بیش از حد بزرگ است")
            payload=json.loads(self.rfile.read(n))
            if not isinstance(payload,dict):raise ValueError("فرمت درخواست نادرست است")
            source="manual"
            if payload.get("image"):
                ocr=extract_picture(payload["image"]); source="tesseract-local"
                text=ocr
            else:text=payload.get("text","")
            result=analyze(text,payload.get("kind","water"),source)
            result["transcription"]=text
            self.respond(200,result)
        except (ValueError,TypeError,json.JSONDecodeError) as err:self.respond(400,{"error":str(err)})
        except Exception:
            self.respond(500,{"error":"خطای غیرمنتظره؛ فایل را بررسی کنید"})
    def log_message(self,format,*args):pass

if __name__=="__main__":
    host="127.0.0.1";port=int(os.environ.get("AGRINEST_PORT","8765"))
    print(f"Agrinest Ultra local-only: http://{host}:{port}",flush=True)
    ThreadingHTTPServer((host,port),Handler).serve_forever()

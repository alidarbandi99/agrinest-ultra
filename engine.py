"""Agrinest Ultra: conservative Persian/English laboratory row interpreter.
No model weights, no guessed OCR data, no automatic fertilizer prescription.
"""
from __future__ import annotations
import re
import unicodedata
from typing import Any

NUM_TRANS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
CHAR_TRANS = str.maketrans({"ي":"ی","ك":"ک","٫":".","−":"-","–":"-","‌":" ","₃":"3","₄":"4","₂":"2","₅":"5","µ":"u","μ":"u"})
ALIASES: dict[str,tuple[str,...]] = {
"Ca":("Ca","calcium","کلسیم"),"Mg":("Mg","magnesium","منیزیم","منیزیوم"),
"Na":("Na","sodium","سدیم"),"K":("K","potassium","پتاسیم"),
"P":("P","phosphorus","فسفر"),"S":("S","sulfur","sulphur","گوگرد"),
"Fe":("Fe","iron","آهن"),"Mn":("Mn","manganese","منگنز"),
"Zn":("Zn","zinc","روی"),"Cu":("Cu","copper","مس"),
"B":("B","boron","بور","بر"),"Mo":("Mo","molybdenum","مولیبدن"),
"NO3-N":("NO3-N","nitrate-n","نیتروژن نیتراتی","ازت نیتراتی"),
"NO3":("NO3","nitrate","نیترات"),"NH4-N":("NH4-N","ammonium-n","نیتروژن آمونیومی"),
"NH4":("NH4","ammonium","آمونیوم"),"SO4":("SO4","sulfate","sulphate","سولفات"),
"SO4-S":("SO4-S","sulfate-s","گوگرد سولفاتی"),
"Cl":("Cl","chloride","کلرید","کلراید"),
"HCO3":("HCO3","bicarbonate","بی کربنات","بی‌کربنات"),
"CO3":("CO3","carbonate","کربنات"),"PO4":("PO4","phosphate","فسفات"),
"P2O5":("P2O5",), "K2O":("K2O",),
"EC":("EC","electrical conductivity","هدایت الکتریکی"),
"pH":("pH","پی اچ","اسیدیته"),"TDS":("TDS","جامدات محلول"),
"SAR":("SAR","نسبت جذب سدیم"),"CEC":("CEC","ظرفیت تبادل کاتیونی"),
"OM":("OM","organic matter","ماده آلی"),"OC":("OC","organic carbon","کربن آلی"),"N":("N","nitrogen","ازت","نیتروژن")
}
FA = {"Ca":"کلسیم","Mg":"منیزیم","Na":"سدیم","K":"پتاسیم","P":"فسفر","S":"گوگرد","Fe":"آهن","Mn":"منگنز","Zn":"روی","Cu":"مس","B":"بور","Mo":"مولیبدن","NO3-N":"نیتروژن نیتراتی","NO3":"نیترات","NH4-N":"نیتروژن آمونیومی","NH4":"آمونیوم","SO4":"سولفات","SO4-S":"گوگرد سولفاتی","Cl":"کلرید","HCO3":"بی‌کربنات","CO3":"کربنات","PO4":"فسفات","P2O5":"اکسید فسفر","K2O":"اکسید پتاسیم","EC":"هدایت الکتریکی","pH":"اسیدیته","TDS":"جامدات محلول","SAR":"نسبت جذب سدیم","CEC":"ظرفیت تبادل کاتیونی","OM":"ماده آلی","OC":"کربن آلی","N":"نیتروژن"}
def normalize(s:str)->str:
    return unicodedata.normalize("NFKC",s).translate(NUM_TRANS).translate(CHAR_TRANS).strip()
def canon_key(s:str)->str:
    return re.sub(r"\s+"," ",normalize(s)).casefold()
LOOKUP:dict[str,str]={}
for key,aliases in ALIASES.items():
    for alias in aliases:
        k=canon_key(alias)
        if k in LOOKUP and LOOKUP[k]!=key: raise RuntimeError("Ambiguous alias: "+alias)
        LOOKUP[k]=key
UNITS = r"(?:mg\s*/\s*(?:L|kg)|ug\s*/\s*L|mmol\s*/\s*L|meq\s*/\s*L|g\s*/\s*kg|dS\s*/\s*m|mS\s*/\s*cm|uS\s*/\s*cm|ppm|ppb|%)"
VALUE = r"(?P<qual><=|>=|[<>≤≥])?\s*(?P<value>\d+(?:[.,]\d+)?)"
ROW=re.compile(r"^(?P<label>.+?)\s*(?:[:=|؛\t]|\s)\s*"+VALUE+r"\s*(?P<unit>"+UNITS+r")\s*$",re.I)
PH=re.compile(r"^(?P<label>pH|پی اچ|اسیدیته)\s*[:=|\t ]+\s*(?P<value>\d+(?:[.,]\d+)?)\s*$",re.I)
SPECIAL=re.compile(r"^(?P<label>.+?)\s*(?:[:=|؛\t]|\s)\s*(?P<word>trace|nd|n\.d\.|not detected|ردی|جزئی|کمتر از حد تشخیص)(?:\s+(?P<unit>"+UNITS+r"))?\s*$",re.I)
UNIT_MAP={"mg/l":"mg/L","mg/kg":"mg/kg","ug/l":"ug/L","mmol/l":"mmol/L","meq/l":"meq/L","g/kg":"g/kg","ds/m":"dS/m","ms/cm":"mS/cm","us/cm":"uS/cm","ppm":"ppm","ppb":"ppb","%":"%"}
def unit_clean(s:str)->str:
    return UNIT_MAP.get(re.sub(r"\s+","",s).casefold(),s)
def analyze(text:str,kind:str="water",source:str="manual")->dict[str,Any]:
    if kind not in ("water","soil"): raise ValueError("نوع آزمایش نامعتبر است")
    if not isinstance(text,str) or len(text)>100_000: raise ValueError("متن نامعتبر یا بیش از حد بزرگ")
    rows=[]; review=[]; ignored=0
    for idx,line in enumerate(text.splitlines(),1):
        raw=line.strip()
        if not raw: continue
        s=normalize(raw)
        m=ROW.fullmatch(s); p=None if m else PH.fullmatch(s); sp=None if m or p else SPECIAL.fullmatch(s)
        if not (m or p or sp):
            if re.search(r"\d|trace|ردی",s,re.I): review.append({"line":idx,"raw":raw,"reason":"ساختار یا واحد این سطر قابل استخراج نبود"})
            else: ignored+=1
            continue
        hit=m or p or sp
        key=LOOKUP.get(canon_key(hit.group("label")))
        if not key:
            review.append({"line":idx,"raw":raw,"reason":"نام عنصر ناشناخته یا مبهم است"});continue
        if p: unit="بدون واحد"
        else: unit=unit_clean((m or sp).group("unit") or "")
        if m or p:
            number=hit.group("value")
            if "," in number:
                review.append({"line":idx,"raw":raw,"reason":"کاما می‌تواند اعشار یا جداکننده هزارگان باشد"});continue
            amount=float(number)
            qual=(m.group("qual") or "=") if m else "="
        else:
            amount=None;qual=sp.group("word")
        warnings=[]
        if key=="pH" and amount is not None and not (0<=amount<=14): warnings.append("مقدار pH خارج از دامنه است")
        if key=="EC" and unit not in ("dS/m","mS/cm","uS/cm"): warnings.append("واحد هدایت الکتریکی نامعتبر است")
        if kind=="soil" and unit in ("mg/kg","g/kg","ppm"): warnings.append("غلظت خاک به‌صورت مستقیم از هدف محلول غذایی کم نمی‌شود")
        if kind=="water" and unit in ("mg/kg","g/kg"): warnings.append("واحد خاک برای نمونه آب ثبت شده است")
        if key in ("NO3","NO3-N","NH4","NH4-N","SO4","SO4-S","PO4","P2O5","K2O"): warnings.append("مبنای شیمیایی عنصر و یون باید حفظ شود")
        if qual!="=":warnings.append("عدد قطعی نیست؛ وضعیت یا حد تشخیص گزارش شده است")
        if unit=="":warnings.append("واحد اندازه‌گیری مشخص نشده است")
        rows.append({"line":idx,"key":key,"name_fa":FA[key],"value":amount,"qualifier":qual,"unit":unit,"raw":raw,"warnings":warnings,"verified":False})
    duplicates={}
    for row in rows: duplicates[row["key"]]=duplicates.get(row["key"],0)+1
    for row in rows:
        if duplicates[row["key"]]>1: row["warnings"].append("این پارامتر چند بار گزارش شده؛ نمونه و روش را بررسی کنید")
    return {"sample_type":kind,"source":source,"rows":rows,"needs_review":review,"ignored_lines":ignored,
            "row_count":len(rows),"status":"needs_human_review","use_in_calculation_allowed":False,
            "disclaimer":"خروجی استخراج ماشینی است؛ برای تغذیه و محاسبات نیاز به تأیید کارشناس دارد."}

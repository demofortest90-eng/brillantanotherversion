import os
import random
import string
import datetime
import re
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, Response
from flask_pymongo import PyMongo
from werkzeug.utils import secure_filename
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from datetime import datetime
import base64
import requests
from bson import ObjectId
import csv
import io
import bleach

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "brillant2026_secret_key")

# Fix: Use database name in URI
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://kayimartbd_db_user:a2FG5pl2Z3qcaLcc@kayimartbd.kn6htnp.mongodb.net/brillant2026")
# Ensure database name is in URI
if "brillant2026" not in MONGO_URI:
    if "?" in MONGO_URI:
        MONGO_URI = MONGO_URI.replace("?", "/brillant2026?")
    elif MONGO_URI.endswith("/"):
        MONGO_URI = MONGO_URI + "brillant2026"
    else:
        MONGO_URI = MONGO_URI + "/brillant2026"

app.config["MONGO_URI"] = MONGO_URI
app.config['UPLOAD_FOLDER'] = os.getenv("UPLOAD_FOLDER", "static/uploads")

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

mongo = PyMongo(app)

@app.template_filter('notice_content')
def notice_content_filter(text):
    """Sanitize notice content but allow admin-provided <a> links to render
    as styled, clickable buttons. All other HTML is stripped/escaped."""
    if not text:
        return ""
    allowed_tags = ['a']
    allowed_attrs = {'a': ['href', 'target', 'rel']}
    cleaned = bleach.clean(text, tags=allowed_tags, attributes=allowed_attrs,
                            protocols=['http', 'https', 'mailto', 'tel'], strip=True)

    # Style every <a> tag as a notice link-button and force safe target/rel
    def style_links(html):
        import re
        def repl(m):
            attrs = m.group(1)
            href_match = re.search(r'href=["\']([^"\']*)["\']', attrs)
            href = href_match.group(1) if href_match else '#'
            return ('<a href="{0}" target="_blank" rel="noopener noreferrer" '
                    'class="notice-link-btn"><i class="fas fa-link"></i> '
                    'লিঙ্ক দেখুন</a>').format(href)
        return re.sub(r'<a\s+([^>]*)>.*?</a>', repl, html, flags=re.IGNORECASE | re.DOTALL)

    return style_links(cleaned)


_BN_DIGIT_MAP = str.maketrans('0123456789', '০১২৩৪৫৬৭৮৯')

@app.template_filter('bn_num')
def bn_num_filter(value):
    """Convert any English digits found in the value to Bengali numerals
    (used on the printable Bengali prospectus/album pages)."""
    if value is None:
        return ''
    return str(value).translate(_BN_DIGIT_MAP)


def generate_numbers():
    reg = ''.join(random.choices(string.digits, k=8))
    roll = ''.join(random.choices(string.digits, k=5))
    return reg, roll

DEFAULT_LEADERS = [
    {
        "name": "মোঃ নজরুল ইসলাম",
        "designation": "চেয়ারম্যান",
        "photo_url": "https://i.postimg.cc/SsLDX6WZ/Screenshot_2026_01_20_020601_removebg_preview.png",
        "speech": "মেধাবীদের সঠিক মূল্যায়ন এবং তাদের উচ্চশিক্ষার পথ সুগম করাই আমাদের প্রধান লক্ষ্য। আমরা বিশ্বাস করি বগুড়ার শিক্ষার্থীরা আগামীতে দেশের মুখ উজ্জ্বল করবে।"
    },
    {
        "name": "ড. আবু সাঈদ",
        "designation": "পরিচালক (শিক্ষা)",
        "photo_url": "https://i.postimg.cc/SsLDX6WZ/Screenshot_2026_01_20_020601_removebg_preview.png",
        "speech": "স্বচ্ছতা এবং আধুনিক পরীক্ষা পদ্ধতির মাধ্যমে আমরা একটি বিশ্বস্ত মেধা যাচাই প্রক্রিয়া গড়ে তুলেছি। আমরা শিক্ষার্থীদের গুণগত মান বৃদ্ধিতে প্রতিশ্রুতিবদ্ধ।"
    },
    {
        "name": "জনাব আহসান হাবীব",
        "designation": "সমন্বয়কারী",
        "photo_url": "https://i.postimg.cc/SsLDX6WZ/Screenshot_2026_01_20_020601_removebg_preview.png",
        "speech": "টিবিএফ একটি পরিবারের মতো। গত এক দশক ধরে আমরা বগুড়ার প্রতিটি শিক্ষা প্রতিষ্ঠানের সাথে সমন্বয় করে মেধাবীদের জন্য কাজ করে যাচ্ছি।"
    }
]

@app.route('/')
def landing():
    try:
        leaders = list(mongo.db.leaders.find().sort("order", 1))
    except Exception:
        leaders = []
    if not leaders:
        leaders = DEFAULT_LEADERS

    # Dynamic homepage settings
    try:
        home_settings = mongo.db.home_settings.find_one({"key": "home"}) or {}
    except Exception:
        home_settings = {}

    # Hero slides (cover images)
    default_slides = [
        "https://i.postimg.cc/V6dkdwcw/550584227_1306561844591582_7461480228133852539_n.jpg",
        "https://i.postimg.cc/XYzp0LhM/Whats_App_Image_2026_01_31_at_1_57_28_AM1.jpg",
        "https://i.postimg.cc/YCshwRPV/Whats_App_Image_2026_01_31_at_1_57_28_AM.jpg"
    ]
    hero_slides = home_settings.get("hero_slides", default_slides)

    # Hero text
    hero_title = home_settings.get("hero_title", "মেধার অন্বেষণে <br><span style=\"color: var(--gold);\">টিবিএফ ২০২৬</span>")
    hero_subtitle = home_settings.get("hero_subtitle", "বগুড়ার মেধাবী শিক্ষার্থীদের জন্য এক বিশ্বস্ত ও আধুনিক প্লাটফর্ম।")

    # Important dates
    default_dates = [
        {"day": "০১", "month": "ফেব্রু", "title": "আবেদন শুরু", "desc": "২০২৬ মেধা পরীক্ষার রেজিস্ট্রেশন শুরু।", "highlight": False},
        {"day": "২০", "month": "মার্চ", "title": "শেষ সময়", "desc": "আবেদন ফরম জমা দেওয়ার চূড়ান্ত তারিখ।", "highlight": True},
        {"day": "১৫", "month": "মে", "title": "পরীক্ষা", "desc": "সকাল ১০টায় নির্দিষ্ট কেন্দ্রে পরীক্ষা।", "highlight": False}
    ]
    important_dates = home_settings.get("important_dates", default_dates)

    # About/Impact section
    impact_image = home_settings.get("impact_image", "https://i.postimg.cc/63ypyKNx/550676924_1306637174584049_1345585347271334112_n.jpg")
    impact_title = home_settings.get("impact_title", "শ্রেষ্ঠত্বের এক দশক")
    impact_text = home_settings.get("impact_text", "২০১২ সাল থেকে আমরা কাজ করছি স্বচ্ছতা ও নিরপেক্ষতার সাথে। আমরা কেবল একটি পরীক্ষা নই, বরং মেধাবীদের আগামীর স্বপ্ন।")
    stats = home_settings.get("stats", [
        {"number": "৫০০০+", "label": "সফল শিক্ষার্থী"},
        {"number": "১০০%", "label": "ডিজিটাল রেজাল্ট"}
    ])

    # Gallery images
    default_gallery = [
        "https://i.postimg.cc/0Qbybvq5/549605784_1306562557924844_5824319049134876797_n.jpg",
        "https://i.postimg.cc/k4BgBCdd/549166921_1306562611258172_9183451457376780271_n.jpg",
        "https://i.postimg.cc/ZRC5Cmhb/549606794_1306562667924833_1638799538323628393_n.jpg",
        "https://i.postimg.cc/0QF2S481/550267765_1306562521258181_867733181360162386_n.jpg"
    ]
    gallery_images = home_settings.get("gallery_images", default_gallery)

    registration_open = is_registration_open()

    # Top 3 latest notices for the homepage notice board.
    try:
        latest_notices = list(mongo.db.notices.find().sort("_id", -1).limit(3))
    except Exception:
        latest_notices = []

    return render_template('landing.html',
        leaders=leaders,
        hero_slides=hero_slides,
        hero_title=hero_title,
        hero_subtitle=hero_subtitle,
        important_dates=important_dates,
        impact_image=impact_image,
        impact_title=impact_title,
        impact_text=impact_text,
        stats=stats,
        gallery_images=gallery_images,
        registration_open=registration_open,
        notices=latest_notices
    )

def upload_to_imgbb(file):
    api_key = "0bb1747f7045ccee9cc03c792b828a67"
    img_data = base64.b64encode(file.read()).decode('utf-8')
    try:
        response = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": api_key, "image": img_data}
        )
        res_json = response.json()
        if response.status_code == 200:
            return res_json['data']['url']
        else:
            print(f"ImgBB Error: {res_json}")
            return None
    except Exception as e:
        print(f"Upload Exception: {e}")
        return None

@app.route('/api/upload-photo', methods=['POST'])
def api_upload_photo():
    photo_file = request.files.get('photo')
    if not photo_file or not photo_file.filename:
        return jsonify({"success": False, "message": "No photo provided"}), 400
    photo_url = upload_to_imgbb(photo_file)
    if not photo_url:
        return jsonify({"success": False, "message": "Image upload failed. Please try again."}), 500
    return jsonify({"success": True, "url": photo_url})

# =====================================================================
# DYNAMIC CENTER HELPERS — single source of truth for center names so
# nothing in the project relies on a hardcoded center list anymore.
# =====================================================================

def center_code_filter(value):
    """Robust, case/space-tolerant match query for center_code. Some
    historical records may have inconsistent casing/whitespace, so every
    center filter in the project should use this instead of an exact
    string match."""
    v = str(value).strip()
    variants = {v, v.upper(), v.lower()}
    if v.isdigit():
        try:
            variants.add(int(v))
        except ValueError:
            pass
    return {"$in": list(variants)}

def get_center_name_map(lang='bn'):
    """Returns {center_code(str): display_name} built live from the
    'centers' collection. Replaces every hardcoded centers dict."""
    result = {}
    for c in mongo.db.centers.find():
        code = str(c.get('center_code', ''))
        if lang == 'en':
            result[code] = c.get('center_name_en') or c.get('center_name_bn') or code
        else:
            result[code] = c.get('center_name_bn') or c.get('center_name_en') or code
    return result

def get_grouped_center_name_map(lang='bn'):
    """Like get_center_name_map, but a center that belongs to a Center
    Group shows the group's own name instead of its individual name —
    used wherever a 'combined' center identity should appear. Each group
    has two separate names: group_name_en (shown on certificates) and
    group_name_bn (shown on the scholarship prospectus). Old groups saved
    before this split (single 'group_name') still work via fallback."""
    base = get_center_name_map(lang=lang)
    for g in mongo.db.center_groups.find():
        if lang == 'en':
            gname = g.get('group_name_en') or g.get('group_name') or g.get('group_name_bn', '')
        else:
            gname = g.get('group_name_bn') or g.get('group_name') or g.get('group_name_en', '')
        for code in g.get('member_codes', []):
            base[str(code)] = gname
    return base

def get_grouped_centers_set():
    """Set of all center_codes (as strings) that currently belong to any group."""
    codes = set()
    for g in mongo.db.center_groups.find():
        codes.update(str(c) for c in g.get('member_codes', []))
    return codes

SCHOLARSHIP_GRADES = ['Talentpool', 'General', 'Suveccha', 'Quata']
# Note: 'Quata' is the legacy internal/DB value for this grade (kept as-is so
# existing student records aren't affected). Its DISPLAYED label everywhere
# in the UI is "মেধাবৃত্তি" (Medha Britti), not "কোটা" (Quota).
GRADE_BN_LABELS = {
    'Talentpool': 'ট্যালেন্টপুল',
    'General': 'সাধারণ',
    'Suveccha': 'শুভেচ্ছা',
    'Quata': 'মেধাবৃত্তি',
}

# Labels used specifically on the printed prospectus booklet badges, matching
# the wording in the official printed book (e.g. "জেনারেল" rather than
# "সাধারণ"). Kept separate so the rest of the app's labels stay unchanged.
PROSPECTUS_GRADE_LABELS = {
    'Talentpool': 'ট্যালেন্টপুল',
    'General': 'জেনারেল',
    'Suveccha': 'শুভেচ্ছা',
    'Quata': 'মেধাবৃত্তি',
}

def get_prospecture_students(student_class, grade_filter='', center_filter=''):
    """Fetch scholarship-winning students for a class (optionally narrowed
    by grade/center), and also return them pre-grouped by scholarship grade
    in official order (Talentpool -> General -> Suveccha -> Quata) — used by
    both the Prospecture Photo Album admin view and its print/PDF version."""
    query = {
        "student_class": student_class,
        "scholarship_grade": {"$exists": True, "$nin": [None, "", "Nothing"]}
    }
    if grade_filter:
        query["scholarship_grade"] = grade_filter
    if center_filter:
        query["center_code"] = center_code_filter(center_filter)

    students = list(mongo.db.students.find(query).sort([("scholarship_grade", 1), ("marks.total", -1)]))
    grouped = {}
    for g in SCHOLARSHIP_GRADES:
        bucket = [s for s in students if s.get('scholarship_grade') == g]
        if bucket:
            grouped[g] = bucket
    return students, grouped

# =====================================================================
# ADMIT CARD SETTINGS — admin-editable signature & exam date/time
# =====================================================================

def get_admit_settings():
    s = mongo.db.admit_settings.find_one({"key": "admit"}) or {}
    return {
        "signature_image": s.get("signature_image") or "https://i.postimg.cc/sX21ngh3/rsz-screenshot-2026-01-23-185732.png",
        "signature_title": s.get("signature_title") or "পরীক্ষা নিয়ন্ত্রক",
        "exam_datetime": s.get("exam_datetime") or "20 Jan 2026, 10:00 AM",
    }

def get_cert_settings():
    """Admin-editable certificate signature + result-publication date. The
    signature image prints in the bottom-right corner (above the pre-printed
    'Controller of Examinations' label) and the date prints on the 'Date of
    Publication of Result' line. Managed from Admin → সার্টিফিকেট সেটিংস."""
    s = mongo.db.cert_settings.find_one({"key": "cert"}) or {}
    return {
        "signature_image": s.get("signature_image", ""),
        "signature_name": s.get("signature_name", ""),
        "publication_date": s.get("publication_date", ""),
    }

# =====================================================================
# CERTIFICATE FIELD LAYOUT (drag-and-drop editor)
# ---------------------------------------------------------------------
# Each field's position is stored as percentages of the 1123x794 (A4
# landscape) certificate container, plus a font-size in px. These are the
# canonical defaults (calibrated against static/img/certificate_original.jpg).
# Admins can drag every field in Admin -> সার্টিফিকেট লেআউট to override these,
# and the saved layout is applied to both single and bulk certificate prints.
# =====================================================================

# Ordered so the editor lists them in a sensible top-to-bottom order.
CERT_FIELD_LABELS = [
    ("sl-no",            "SI / Serial No"),
    ("reg-no",           "Registration No"),
    ("exam-year",        "Exam Year"),
    ("student-name",     "Student Name"),
    ("father-name",      "Father's Name"),
    ("student-class",    "Class"),
    ("institute",        "Institute"),
    ("roll-no",          "Roll No"),
    ("center-name",      "Center Name"),
    ("scholarship-grade","Scholarship Grade"),
    ("pub-date",         "Publication Date"),
    ("signature-block",  "Signature Block"),
]

# Sample values shown inside each field while editing.
CERT_FIELD_SAMPLES = {
    "sl-no": "4263",
    "reg-no": "1865593",
    "exam-year": "-2026",
    "student-name": "MD. SAMPLE STUDENT NAME",
    "father-name": "MD. SAMPLE FATHER NAME",
    "student-class": "8",
    "institute": "SAMPLE HIGH SCHOOL",
    "roll-no": "101",
    "center-name": "Brilliants Center",
    "scholarship-grade": "General",
    "pub-date": "30-03-2026",
    "signature-block": "স্বাক্ষর",
}

DEFAULT_CERT_LAYOUT = {
    "sl-no":             {"top": 14.5, "left": 21.5, "width": 6.2,   "font_size": 20},
    "reg-no":            {"top": 14.2, "left": 80.0, "width": 12.5,  "font_size": 20},
    "exam-year":         {"top": 32.5, "left": 62.5, "width": 12.0,  "font_size": 28},
    "student-name":      {"top": 49.3, "left": 26.0, "width": 63.0,  "font_size": 30},
    "father-name":       {"top": 56.0, "left": 24.0, "width": 64.0,  "font_size": 20},
    "student-class":     {"top": 61.6, "left": 24.0, "width": 8.9,   "font_size": 20},
    "institute":         {"top": 61.6, "left": 45.0, "width": 46.0,  "font_size": 20},
    "roll-no":           {"top": 67.0, "left": 17.0, "width": 10.7,  "font_size": 20},
    "center-name":       {"top": 67.0, "left": 31.5, "width": 18.7,  "font_size": 20},
    "scholarship-grade": {"top": 67.0, "left": 75.3, "width": 10.7,  "font_size": 20},
    "pub-date":          {"top": 83.0, "left": 18.0, "width": 14.25, "font_size": 20},
    "signature-block":   {"top": 70.0, "left": 63.5, "width": 22.0,  "font_size": 15},
}


def _coerce_layout_entry(default, raw):
    """Merge one saved field entry over its default, keeping only valid
    numeric values within sane bounds."""
    out = dict(default)
    if not isinstance(raw, dict):
        return out
    for key in ("top", "left", "width", "font_size"):
        if key in raw:
            try:
                val = float(raw[key])
            except (TypeError, ValueError):
                continue
            if key == "font_size":
                val = max(6.0, min(120.0, val))
            else:
                val = max(0.0, min(100.0, val))
            out[key] = round(val, 2)
    return out


def get_cert_layout():
    """Return the full field-layout map (saved values merged over defaults).
    Always contains every field key, so templates never KeyError."""
    s = mongo.db.cert_settings.find_one({"key": "cert"}) or {}
    saved = s.get("layout") or {}
    layout = {}
    for field, default in DEFAULT_CERT_LAYOUT.items():
        layout[field] = _coerce_layout_entry(default, saved.get(field))
    return layout


def build_cert_field_styles(layout=None):
    """Turn the layout map into inline CSS strings, one per field. These are
    injected onto each field element in the certificate templates and override
    the positions defined in the template's <style> block. `right:auto` is
    always set so fields originally anchored from the right snap to `left`."""
    if layout is None:
        layout = get_cert_layout()
    styles = {}
    for field, pos in layout.items():
        styles[field] = (
            "top:{top}%; left:{left}%; right:auto; "
            "width:{width}%; font-size:{fs}px;".format(
                top=pos["top"], left=pos["left"],
                width=pos["width"], fs=pos["font_size"],
            )
        )
    return styles

# =====================================================================
# PARTICIPANT SUMMARY REPORT HELPERS (gender x school/madrasha breakdown
# + manually recorded exam-day attendance, matching the official sheet)
# =====================================================================

def _blank_breakdown():
    return {"school": 0, "madrasha": 0, "total": 0}

# Bangla labels for each class; falls back to "শ্রেণি <n>" for anything else.
CLASS_LABELS_BN = {
    "5": "পঞ্চম শ্রেণি",
    "6": "ষষ্ঠ শ্রেণি",
    "7": "সপ্তম শ্রেণি",
    "8": "অষ্টম শ্রেণি",
    "9": "নবম শ্রেণি",
    "10": "দশম শ্রেণি",
}
# Classes always shown in the report (so the sheet is consistent even with 0 students).
DEFAULT_REPORT_CLASSES = ["5", "6", "7", "8", "9"]

def class_label_bn(cls):
    cls = str(cls).strip()
    return CLASS_LABELS_BN.get(cls, f"শ্রেণি {cls}")

def get_report_class_list():
    """Ordered list of class keys (as strings) to show in the participant
    report — the union of the default 5-9 set and any other classes that
    actually exist in the student data. Sorted numerically where possible."""
    found = [str(c).strip() for c in mongo.db.students.distinct("student_class") if str(c).strip()]
    keys = set(found) | set(DEFAULT_REPORT_CLASSES)

    def _sort_key(k):
        try:
            return (0, int(k))
        except (TypeError, ValueError):
            return (1, k)

    return sorted(keys, key=_sort_key)

def build_center_participation(center_code, class_keys, status_filter='Verified'):
    """Registered-student counts for one center, split by class x
    institute type. Returns { class_key: {school, madrasha, total} }."""
    match = {"center_code": center_code_filter(center_code)}
    if status_filter == 'Verified':
        match["status"] = "Verified"
    elif status_filter == 'Pending':
        match["status"] = {"$ne": "Verified"}

    pipeline = [
        {"$match": match},
        {"$group": {
            "_id": {"cls": "$student_class", "type": "$institute_type"},
            "count": {"$sum": 1}
        }}
    ]
    rows = list(mongo.db.students.aggregate(pipeline))

    counts = {str(k): _blank_breakdown() for k in class_keys}
    for r in rows:
        # student_class may be stored as int or str — normalise to str.
        ckey = str(r["_id"].get("cls") or "").strip()
        if not ckey:
            continue
        tid = (r["_id"].get("type") or "").strip().lower()
        tkey = "madrasha" if tid.startswith("madras") else "school"
        if ckey not in counts:
            counts[ckey] = _blank_breakdown()
        counts[ckey][tkey] += r["count"]

    for k in counts:
        counts[k]["total"] = counts[k]["school"] + counts[k]["madrasha"]
    return counts

def get_exam_attendance_raw(center_code, year):
    """Returns (stored_classes_dict, saved_bool) for one center/year.
    stored_classes_dict = { class_key: {school, madrasha} }."""
    doc = mongo.db.exam_attendance.find_one({"center_code": center_code, "year": year}) or {}
    return (doc.get("classes", {}) or {}), bool(doc)

def build_full_center_report(status_filter, year, center_code=None):
    """One row per center (or just the requested one) combining registered
    counts with the manually recorded exam-day attendance, broken down by
    class, plus a grand total. center_code of None/''/'ALL' means every
    center. Every center uses the same ordered class list so rows line up."""
    if center_code and center_code != 'ALL':
        centers = list(mongo.db.centers.find({"center_code": center_code}))
    else:
        centers = list(mongo.db.centers.find().sort("center_code", 1))

    class_keys = get_report_class_list()

    report_rows = []
    for c in centers:
        code = c.get('center_code')
        reg = build_center_participation(code, class_keys, status_filter)
        stored_att, saved = get_exam_attendance_raw(code, year)

        classes = []
        reg_total = _blank_breakdown()
        att_total = _blank_breakdown()
        for k in class_keys:
            r = reg.get(str(k), _blank_breakdown())
            a_raw = stored_att.get(str(k), {}) or {}
            a_school = int(a_raw.get("school", 0) or 0)
            a_madrasha = int(a_raw.get("madrasha", 0) or 0)
            a = {"school": a_school, "madrasha": a_madrasha, "total": a_school + a_madrasha}
            classes.append({
                "class_key": str(k),
                "class_name": class_label_bn(k),
                "registered": r,
                "attendance": a,
            })
            for fld in ("school", "madrasha", "total"):
                reg_total[fld] += r[fld]
                att_total[fld] += a[fld]

        report_rows.append({
            "center_code": code,
            "center_name_bn": c.get('center_name_bn'),
            "center_name_en": c.get('center_name_en'),
            "classes": classes,
            "registered_total": reg_total,
            "attendance_total": att_total,
            "attendance_saved": saved,
        })

    # Grand total — aligned class-by-class across all centers.
    grand_classes = []
    grand_reg_total = _blank_breakdown()
    grand_att_total = _blank_breakdown()
    for idx, k in enumerate(class_keys):
        g_reg = _blank_breakdown()
        g_att = _blank_breakdown()
        for row in report_rows:
            cls = row["classes"][idx]
            for fld in ("school", "madrasha", "total"):
                g_reg[fld] += cls["registered"][fld]
                g_att[fld] += cls["attendance"][fld]
        grand_classes.append({
            "class_key": str(k),
            "class_name": class_label_bn(k),
            "registered": g_reg,
            "attendance": g_att,
        })
        for fld in ("school", "madrasha", "total"):
            grand_reg_total[fld] += g_reg[fld]
            grand_att_total[fld] += g_att[fld]

    grand = {
        "classes": grand_classes,
        "registered_total": grand_reg_total,
        "attendance_total": grand_att_total,
    }
    return report_rows, grand

def is_registration_open():
    """Admin-controlled registration on/off switch. Open by default unless
    explicitly turned off from the admin panel."""
    setting = mongo.db.settings.find_one({"key": "registration_open"})
    return setting['value'] if setting else True


@app.route('/apply', methods=['GET', 'POST'])
def apply():
    registration_open = is_registration_open()

    if not registration_open:
        closed_message = mongo.db.settings.find_one({"key": "registration_closed_message"})
        closed_message = (closed_message['value'] if closed_message and closed_message.get('value')
                           else "এই মুহূর্তে নতুন আবেদন গ্রহণ বন্ধ রয়েছে। অনুগ্রহ করে পরে আবার চেষ্টা করুন অথবা কর্তৃপক্ষের সাথে যোগাযোগ করুন।")
        return render_template("registration_closed.html", closed_message=closed_message)

    if request.method == 'POST':
        try:
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            if not password or password != confirm_password:
                flash("পাসওয়ার্ড দুটি মিলছে না!", "danger")
                return redirect(request.url)

            mobile_number = request.form.get('mobile', '').strip()
            if not mobile_number:
                flash("মোবাইল নম্বর অবশ্যই দিতে হবে!", "danger")
                return redirect(request.url)

            # Note: multiple applications from the same mobile number are
            # intentionally allowed (e.g. one guardian applying for several
            # children), so there is no duplicate-mobile check here.

            photo_url = request.form.get('photo_url', '').strip()
            photo_file = request.files.get('photo')

            if not photo_url:
                if not photo_file or not photo_file.filename:
                    flash("শিক্ষার্থীর ছবি অবশ্যই দিতে হবে!", "danger")
                    return redirect(request.url)
                photo_url = upload_to_imgbb(photo_file)
                if not photo_url:
                    flash("ছবি আপলোড ব্যর্থ হয়েছে! অনুগ্রহ করে আবার চেষ্টা করুন।", "danger")
                    return redirect(request.url)

            reg_no, roll_no = generate_numbers()
            # Permanent login serial — never changed by admin serial allocation
            serial_no = roll_no

            center_info = mongo.db.centers.find_one({"center_code": request.form.get('center_code')})
            center_display_name = (center_info.get('center_name_bn') or center_info.get('center_name_en', 'N/A')) if center_info else 'N/A'

            student_data = {
                "roll_no": str(roll_no),
                "reg_no": str(reg_no),
                "serial_no": str(serial_no),
                "student_class": request.form.get('student_class'),
                "category": request.form.get('category', 'General'),
                "center_code": request.form.get('center_code'),
                "center_name": center_display_name,
                "gender": request.form.get('gender'),
                "name_en": request.form.get('name_en', '').upper().strip(),
                "name_bn": request.form.get('name_bn', '').strip(),
                "father_en": request.form.get('father_en', '').strip(),
                "father_bn": request.form.get('father_bn', '').strip(),
                "mother_en": request.form.get('mother_en', '').strip(),
                "mother_bn": request.form.get('mother_bn', '').strip(),
                "mobile": request.form.get('mobile', '').strip(),
                "dob": request.form.get('dob'),
                "institute_en": request.form.get('institute_en', '').strip(),
                "institute_bn": request.form.get('institute_bn', '').strip(),
                "institute_type": request.form.get('institute_type', 'School'),
                "password": generate_password_hash(password),
                "address_present": {
                    "village": request.form.get('pre_v', '').strip(),
                    "upazila": request.form.get('pre_t', '').strip(),
                    "district": request.form.get('pre_d', '').strip()
                },
                "address_permanent": {
                    "village": request.form.get('per_v', '').strip(),
                    "upazila": request.form.get('per_t', '').strip(),
                    "district": request.form.get('per_d', '').strip()
                },
                "photo_url": photo_url,
                "status": "Pending",
                "applied_at": datetime.utcnow()
            }

            mongo.db.students.insert_one(student_data)
            flash("আবেদন সফলভাবে জমা হয়েছে!", "success")
            return render_template("success.html", roll=roll_no, reg=reg_no, mobile=student_data["mobile"])

        except Exception as e:
            print(f"Submission Error: {e}")
            flash("একটি সমস্যা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।", "danger")
            return redirect(request.url)

    all_centers = list(mongo.db.centers.find().sort("center_code", 1))
    inst_docs = list(mongo.db.institutions.find().sort("name", 1))
    institutes_list = [{"name": doc.get("name"), "bn": doc.get("bn")} for doc in inst_docs]
    return render_template("apply.html", centers=all_centers, institutes=institutes_list)

@app.route('/notices')
def notices():
    all_notices = mongo.db.notices.find().sort("_id", -1)
    return render_template('notices.html', notices=all_notices)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        roll = (request.form.get('roll') or '').strip()
        pw = request.form.get('password') or ''

        if not roll or not pw:
            flash("রোল এবং পাসওয়ার্ড উভয়ই প্রদান করুন।", "danger")
            return redirect(url_for('login'))

        try:
            or_conditions = [{"serial_no": roll}, {"roll_no": roll}, {"reg_no": roll}]
            if roll.isdigit():
                or_conditions.append({"roll_no": int(roll)})
            user = mongo.db.students.find_one({"$or": or_conditions})

            if user:
                stored_pw = user.get('password')
                # Some legacy records may not have a password hash — avoid 500 crash
                if stored_pw and check_password_hash(stored_pw, pw):
                    if not user.get('serial_no'):
                        mongo.db.students.update_one({"_id": user['_id']}, {"$set": {"serial_no": str(user.get('roll_no', ''))}})
                    session.permanent = True
                    session['user_id'] = str(user['_id'])
                    session['student_roll'] = str(user.get('roll_no', ''))
                    flash("সফলভাবে লগইন হয়েছে!", "success")
                    return redirect(url_for('dashboard'))
                elif not stored_pw:
                    flash("এই একাউন্টে কোনো পাসওয়ার্ড সেট করা নেই। অনুগ্রহ করে এডমিনের সাথে যোগাযোগ করুন।", "danger")
                else:
                    flash("ভুল পাসওয়ার্ড, আবার চেষ্টা করুন।", "danger")
            else:
                flash("এই রোল নম্বরটি সিস্টেমে পাওয়া যায়নি।", "danger")
        except Exception as e:
            print(f"Login Error: {e}")
            flash("লগইন করতে সমস্যা হয়েছে। অনুগ্রহ করে আবার চেষ্টা করুন।", "danger")
        return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        student = mongo.db.students.find_one({"_id": ObjectId(session['user_id'])})
    except Exception:
        student = None
    if not student:
        session.clear()
        flash("একাউন্টে সমস্যা হয়েছে। অনুগ্রহ করে আবার লগইন করুন।", "danger")
        return redirect(url_for('login'))

    is_verified = student.get('verification', False)
    setting = mongo.db.settings.find_one({"key": "result_published"})
    is_published = setting['value'] if setting else False

    # Fetch center info for this student
    center_info = None
    center_code = student.get('center_code')
    if center_code:
        center_info = mongo.db.centers.find_one({"center_code": center_code})

    # Fetch payment numbers from settings
    bkash_setting = mongo.db.settings.find_one({"key": "bkash_number"})
    nagad_setting = mongo.db.settings.find_one({"key": "nagad_number"})
    bkash_number = bkash_setting['value'] if bkash_setting else ''
    nagad_number = nagad_setting['value'] if nagad_setting else ''

    if request.method == 'POST':
        tran_id = request.form.get('tran_id', '').strip()
        payment_method = request.form.get('payment_method', 'bKash').strip()
        if tran_id:
            mongo.db.students.update_one(
                {"_id": ObjectId(session['user_id'])},
                {"$set": {"tran_id": tran_id, "payment_method": payment_method}}
            )
            flash("ট্রানজেকশন আইডি জমা হয়েছে! অনুমোদনের জন্য অপেক্ষা করুন।", "info")
        return redirect(url_for('dashboard'))

    return render_template('dashboard.html',
                           student=student,
                           is_verified=is_verified,
                           is_published=is_published,
                           center_info=center_info,
                           bkash_number=bkash_number,
                           nagad_number=nagad_number)

@app.route('/download-slip')
def download_slip():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    student = mongo.db.students.find_one({"_id": ObjectId(session['user_id'])})
    if not student or not student.get('verification'):
        flash("দুঃখিত! আপনার একাউন্টটি এখনো ভেরিফাই করা হয়নি।", "danger")
        return redirect(url_for('dashboard'))
    return render_template('payment_slip.html', student=student, admit_settings=get_admit_settings())

@app.route('/download-admit', methods=['GET', 'POST'])
def download_admit():
    if request.method == 'POST':
        roll_query = request.form.get('roll_no', '').strip()
        mobile_query = request.form.get('mobile', '').strip()

        if not roll_query or not mobile_query:
            flash("অনুগ্রহ করে রোল নম্বর ও মোবাইল নম্বর উভয়ই লিখুন।", "warning")
            return redirect(url_for('download_admit'))

        student = mongo.db.students.find_one({"roll_no": roll_query, "mobile": mobile_query})

        if student:
            if not student.get('verification', False):
                flash("আপনার রেজিস্ট্রেশন এখনো ভেরিফাই হয়নি। অনুগ্রহ করে এডমিনের সাথে যোগাযোগ করুন।", "danger")
                return redirect(url_for('download_admit'))

            center_info = mongo.db.centers.find_one({"center_code": student.get('center_code')})
            center_display_name = center_info.get('center_name_bn') if center_info else student.get('center_code')
            return render_template('admit_card.html', student=student, center_name=center_display_name,
                                   admit_settings=get_admit_settings())
        else:
            flash("এই রোল ও মোবাইল নম্বরের মিল খুঁজে পাওয়া যায়নি। অনুগ্রহ করে সঠিক তথ্য দিন।", "danger")
            return redirect(url_for('download_admit'))

    return render_template('admit_search.html')

@app.route('/view-result')
def view_result():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    try:
        student = mongo.db.students.find_one({"_id": ObjectId(session['user_id'])})
    except Exception:
        student = None
    if not student:
        session.clear()
        return redirect(url_for('login'))
    setting = mongo.db.settings.find_one({"key": "result_published"})
    is_published = setting['value'] if setting else False
    if not is_published or not student.get('verification'):
        flash("ফলাফল এখনো প্রকাশিত হয়নি।", "warning")
        return redirect(url_for('dashboard'))
    center_info = mongo.db.centers.find_one({"center_code": student.get('center_code')})
    center_name = center_info.get('center_name_bn') if center_info else student.get('center_code')
    return render_template('result_card.html', student=student, center_name=center_name)


@app.route('/results/all')
def all_results():
    """Public merit list — all published results with class & center filters"""
    setting = mongo.db.settings.find_one({"key": "result_published"})
    is_published = setting['value'] if setting else False
    if not is_published:
        flash("ফলাফল এখনো প্রকাশিত হয়নি। অনুগ্রহ করে পরে আবার চেষ্টা করুন।", "warning")
        return redirect(url_for('public_result_search'))

    f_class = request.args.get('class', '').strip()
    f_center = request.args.get('center', '').strip()
    f_grade = request.args.get('grade', '').strip()

    query = {"marks": {"$exists": True}}
    if f_class:
        query["student_class"] = f_class
    if f_center:
        query["center_code"] = f_center
    if f_grade:
        query["scholarship_grade"] = f_grade

    students = list(mongo.db.students.find(query).sort([("student_class", 1), ("marks.total", -1)]))
    all_centers = sorted([c for c in mongo.db.students.distinct("center_code") if c], key=str)
    all_classes = sorted([c for c in mongo.db.students.distinct("student_class") if c], key=str)
    center_names = {c.get('center_code'): c.get('center_name_bn') or c.get('center_name_en')
                    for c in mongo.db.centers.find()}

    return render_template('all_results.html',
                           students=students,
                           all_centers=all_centers,
                           all_classes=all_classes,
                           center_names=center_names,
                           f_class=f_class, f_center=f_center, f_grade=f_grade)

@app.route('/results/download-csv')
def download_results_csv():
    """Public merit list CSV download with same filters as all_results"""
    setting = mongo.db.settings.find_one({"key": "result_published"})
    is_published = setting['value'] if setting else False
    if not is_published:
        flash("ফলাফল এখনো প্রকাশিত হয়নি।", "warning")
        return redirect(url_for('public_result_search'))

    f_class = request.args.get('class', '').strip()
    f_center = request.args.get('center', '').strip()
    f_grade = request.args.get('grade', '').strip()

    query = {"marks": {"$exists": True}}
    if f_class:
        query["student_class"] = f_class
    if f_center:
        query["center_code"] = f_center
    if f_grade:
        query["scholarship_grade"] = f_grade

    students = list(mongo.db.students.find(query).sort([("student_class", 1), ("marks.total", -1)]))
    center_names = {c.get('center_code'): c.get('center_name_bn') or c.get('center_name_en')
                    for c in mongo.db.centers.find()}

    output = io.StringIO()
    output.write(u'\ufeff')
    writer = csv.writer(output)
    writer.writerow(['ক্রম', 'নাম (বাংলা)', 'নাম (ইংরেজি)', 'শ্রেণি', 'প্রতিষ্ঠান', 'কেন্দ্র',
                     'বাংলা', 'ইংরেজি', 'গণিত', 'সাধারণ জ্ঞান', 'মোট', 'বৃত্তি গ্রেড'])
    for idx, s in enumerate(students, 1):
        marks = s.get('marks') or {}
        center_display = center_names.get(s.get('center_code'), s.get('center_code', ''))
        writer.writerow([
            idx,
            s.get('name_bn', ''),
            s.get('name_en', ''),
            s.get('student_class', ''),
            s.get('institute_bn') or s.get('institute_en', ''),
            center_display,
            marks.get('bangla', ''),
            marks.get('english', ''),
            marks.get('math', ''),
            marks.get('gk', ''),
            marks.get('total', ''),
            s.get('scholarship_grade', '')
        ])
    output.seek(0)
    file_parts = ['Results']
    if f_class:
        file_parts.append(f'Class{f_class}')
    if f_center:
        file_parts.append(f'Center{f_center}')
    if f_grade:
        file_parts.append(f_grade)
    filename = '_'.join(file_parts) + '.csv'
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-disposition": f"attachment; filename={filename}"})


@app.route('/download-scholarship-certificate')
def download_scholarship_certificate():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    student = mongo.db.students.find_one({"_id": ObjectId(session['user_id'])})
    if not student:
        return redirect(url_for('login'))
    setting = mongo.db.settings.find_one({"key": "result_published"})
    is_published = setting['value'] if setting else False
    grade = student.get('scholarship_grade')
    if not is_published or not student.get('verification'):
        flash("Result is not available yet.", "warning")
        return redirect(url_for('dashboard'))
    if not grade or grade == 'Nothing':
        flash("দুঃখিত, আপনি এই বছর বৃত্তির জন্য নির্বাচিত হননি, তাই সার্টিফিকেট ডাউনলোড করা সম্ভব নয়।", "warning")
        return redirect(url_for('view_result'))
    c_code = str(student.get('center_code', ''))
    center_name = get_grouped_center_name_map(lang="en").get(c_code, "Brilliants Foundation Center")
    student['certificate_sl_no'] = get_or_assign_certificate_serial(student)
    cert_date, cert_signature = get_certificate_date_and_signature(student)
    return render_template('certificate_design.html', student=student,
                           center_name=center_name, cert_date=cert_date,
                           cert_signature=cert_signature,
                           field_styles=build_cert_field_styles())

@app.route('/logout')
def logout():
    session.clear()
    flash('আপনি সফলভাবে লগআউট হয়েছেন।', 'info')
    return redirect(url_for('login'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    centers = list(mongo.db.centers.find().sort("center_code", 1))

    # Dynamic contact settings
    try:
        contact_settings = mongo.db.contact_settings.find_one({"key": "contact"}) or {}
    except Exception:
        contact_settings = {}

    contact_hero_image = contact_settings.get("hero_image", "https://i.postimg.cc/HLFyVYC6/476177903-914342390890559-7329175491287224542-n.jpg")
    office_address = contact_settings.get("office_address", "বিআরটিসি মার্কেট (২য় তলা), সাতমাথা রোড, বগুড়া সদর, বগুড়া-৫৮০০")
    phone_mobile = contact_settings.get("phone_mobile", "০১৭১২-২৮২১৬৫")
    phone_office = contact_settings.get("phone_office", "০১৭৩৭-১৯১১৩৬")
    email_addr = contact_settings.get("email", "tbfbogura@gmail.com")
    facebook_url = contact_settings.get("facebook_url", "https://www.facebook.com/thebrilliantsbogura")
    map_embed_url = contact_settings.get("map_embed_url", "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d3619.043681534407!2d89.3703663753719!3d24.845258577939762!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x39fc551608988631%3A0xc06e00192e1b6f0!2sBRTC%20Market!5e0!3m2!1sen!2sbd!4v1715600000000!5m2!1sen!2sbd")

    ctx = dict(
        centers=centers,
        contact_hero_image=contact_hero_image,
        office_address=office_address,
        phone_mobile=phone_mobile,
        phone_office=phone_office,
        email_addr=email_addr,
        facebook_url=facebook_url,
        map_embed_url=map_embed_url
    )

    if request.method == 'POST':
        return render_template('contact.html', success=True, **ctx)
    return render_template('contact.html', **ctx)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('error.html', code=404, message="পেজটি খুঁজে পাওয়া যায়নি",
        description="আপনি যে পেজটি খুঁজছেন সেটি সরিয়ে ফেলা হয়েছে, নাম পরিবর্তন করা হয়েছে অথবা সাময়িকভাবে অনুপলব্ধ।"), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error.html', code=500, message="সার্ভারে সমস্যা হয়েছে",
        description="দুঃখিত! আমাদের সার্ভারে একটি সমস্যা হয়েছে। অনুগ্রহ করে কিছুক্ষণ পরে আবার চেষ্টা করুন।"), 500

@app.errorhandler(403)
def forbidden(e):
    return render_template('error.html', code=403, message="প্রবেশাধিকার নেই",
        description="এই পেজে প্রবেশের অনুমতি আপনার নেই। অনুগ্রহ করে লগইন করেছেন কিনা নিশ্চিত করুন।"), 403

# --- ADMIN LOGIN (Bug Fixed: username check was broken) ---
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        user = request.form.get('username')
        pw = request.form.get('password')
        admin_user = os.getenv("ADMIN_USER", "1")
        admin_pass = os.getenv("ADMIN_PASS", "1")
        # Fixed: was checking os.getenv("ADMIN_USER") as truthy but not comparing to input
        if user == admin_user and pw == admin_pass:
            session['admin_logged_in'] = True
            flash("Welcome back, Admin!", "success")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid Admin Credentials", "danger")
    return render_template('admin_login.html')

# --- ADMIN DASHBOARD ---
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    search_query = request.args.get('search', '').strip()
    center_filter = request.args.get('center', '').strip()
    class_filter = request.args.get('class', '').strip()
    status_filter = request.args.get('status', '').strip()

    available_centers = sorted([c for c in mongo.db.students.distinct("center_code") if c], key=str)
    available_classes = sorted([c for c in mongo.db.students.distinct("student_class") if c], key=str)
    center_names = {c.get('center_code'): c.get('center_name_bn') or c.get('center_name_en')
                    for c in mongo.db.centers.find()}

    query = {}
    if search_query:
        query["$or"] = [
            {"name_en": {"$regex": search_query, "$options": "i"}},
            {"name_bn": {"$regex": search_query, "$options": "i"}},
            {"roll_no": {"$regex": search_query, "$options": "i"}},
            {"institute_bn": {"$regex": search_query, "$options": "i"}},
            {"mobile": {"$regex": search_query, "$options": "i"}}
        ]
    if center_filter:
        query["center_code"] = center_filter
    if class_filter:
        query["student_class"] = class_filter
    if status_filter == 'Verified':
        query["status"] = "Verified"
    elif status_filter == 'Pending':
        query["status"] = {"$ne": "Verified"}

    students = list(mongo.db.students.find(query).sort("roll_no", 1))
    stats = {
        "total": mongo.db.students.count_documents({}),
        "pending": mongo.db.students.count_documents({"status": {"$ne": "Verified"}}),
        "verified": mongo.db.students.count_documents({"status": "Verified"}),
        "filtered": len(students)
    }

    return render_template('admin_panel.html',
                           students=students,
                           stats=stats,
                           available_centers=available_centers,
                           available_classes=available_classes,
                           center_names=center_names,
                           current_search=search_query,
                           current_center=center_filter,
                           current_class=class_filter,
                           current_status=status_filter)

@app.route('/admin/participant-summary')
def participant_summary():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    view_by = request.args.get('view_by', 'center')
    status_filter = request.args.get('status', 'all')
    center_filter = request.args.get('center', '').strip()

    match_stage = {}
    if status_filter == 'Verified':
        match_stage["status"] = "Verified"
    elif status_filter == 'Pending':
        match_stage["status"] = {"$ne": "Verified"}
    if center_filter:
        match_stage["center_code"] = center_code_filter(center_filter)

    pipeline = []
    if match_stage:
        pipeline.append({"$match": match_stage})

    counters = {
        "total": {"$sum": 1},
        "verified": {"$sum": {"$cond": [{"$eq": ["$status", "Verified"]}, 1, 0]}},
        "pending": {"$sum": {"$cond": [{"$ne": ["$status", "Verified"]}, 1, 0]}},
    }

    if view_by == 'institute':
        group_dict = {"_id": "$institute_en", "display_name": {"$first": "$institute_bn"}}
        group_dict.update(counters)
        pipeline.append({"$group": group_dict})
    elif view_by == 'class':
        group_dict = {"_id": "$student_class"}
        group_dict.update(counters)
        pipeline.append({"$group": group_dict})
    else:
        # Center view: some historical records store center_code with
        # different casing/whitespace, which used to split one physical
        # center into several duplicate rows. Normalize before grouping,
        # then resolve the display name live from the centers collection
        # (rather than trusting a possibly-renamed embedded field).
        view_by = 'center'
        pipeline.append({"$addFields": {
            "_norm_center": {"$toUpper": {"$trim": {"input": {"$toString": {"$ifNull": ["$center_code", ""]}}}}}
        }})
        group_dict = {"_id": "$_norm_center"}
        group_dict.update(counters)
        pipeline.append({"$group": group_dict})

    pipeline.append({"$sort": {"_id": 1}})
    summary = list(mongo.db.students.aggregate(pipeline))

    if view_by == 'center':
        name_map_upper = {k.upper(): v for k, v in get_center_name_map(lang='bn').items()}
        for item in summary:
            code = str(item.get("_id") or '').upper()
            item["display_name"] = name_map_upper.get(code, item.get("_id") or 'Not Set')

    grand_total = sum(item.get("total", 0) for item in summary)
    centers = list(mongo.db.centers.find().sort("center_code", 1))

    return render_template('admin_participant_summary.html',
                           summary=summary,
                           view_by=view_by,
                           status_filter=status_filter,
                           center_filter=center_filter,
                           centers=centers,
                           grand_total=grand_total)

@app.route('/admin/participant-summary/report')
def participant_summary_report():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    centers = list(mongo.db.centers.find().sort("center_code", 1))
    selected_center = request.args.get('center', '').strip()
    status_filter = request.args.get('status', 'Verified')
    try:
        year = int(request.args.get('year', datetime.now().year))
    except (TypeError, ValueError):
        year = datetime.now().year

    report_rows, grand_total = [], None
    if selected_center:
        report_rows, grand_total = build_full_center_report(status_filter, year, selected_center)

    return render_template('admin_participant_report.html',
                           centers=centers,
                           selected_center=selected_center,
                           status_filter=status_filter,
                           year=year,
                           report_rows=report_rows,
                           grand_total=grand_total)

@app.route('/admin/participant-summary/save-attendance', methods=['POST'])
def save_exam_attendance():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    center_code = request.form.get('center_code', '').strip()
    try:
        year = int(request.form.get('year'))
    except (TypeError, ValueError):
        year = datetime.now().year

    def _to_int(v):
        try:
            return max(0, int(v))
        except (TypeError, ValueError):
            return 0

    class_keys = [k.strip() for k in request.form.get('class_keys', '').split(',') if k.strip()]
    classes = {}
    for k in class_keys:
        classes[k] = {
            "school": _to_int(request.form.get(f'school_{k}')),
            "madrasha": _to_int(request.form.get(f'madrasha_{k}')),
        }

    mongo.db.exam_attendance.update_one(
        {"center_code": center_code, "year": year},
        {"$set": {
            "center_code": center_code,
            "year": year,
            "classes": classes,
            "updated_at": datetime.utcnow()
        },
         # drop legacy gender-based fields if this doc was saved by the old version
         "$unset": {
            "school_boys": "", "madrasha_boys": "",
            "school_girls": "", "madrasha_girls": ""
        }},
        upsert=True
    )
    flash("পরীক্ষার দিনের উপস্থিতির সংখ্যা সংরক্ষণ করা হয়েছে।", "success")
    return redirect(url_for('participant_summary_report',
                            center=center_code,
                            status=request.form.get('status_filter', 'Verified'),
                            year=year))

@app.route('/admin/participant-summary/print')
def participant_summary_print():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    selected_center = request.args.get('center', 'ALL').strip()
    status_filter = request.args.get('status', 'Verified')
    try:
        year = int(request.args.get('year', datetime.now().year))
    except (TypeError, ValueError):
        year = datetime.now().year
    report_rows, grand_total = build_full_center_report(status_filter, year, selected_center)
    return render_template('participant_summary_print.html',
                           report_rows=report_rows, grand_total=grand_total,
                           status_filter=status_filter, year=year,
                           selected_center=selected_center, now=datetime.now())

@app.route('/admin/participant-summary/download-csv')
def participant_summary_download_csv():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    selected_center = request.args.get('center', 'ALL').strip()
    status_filter = request.args.get('status', 'Verified')
    try:
        year = int(request.args.get('year', datetime.now().year))
    except (TypeError, ValueError):
        year = datetime.now().year
    report_rows, grand_total = build_full_center_report(status_filter, year, selected_center)

    output = io.StringIO()
    output.write(u'\ufeff')
    writer = csv.writer(output)
    writer.writerow(['কেন্দ্র কোড', 'কেন্দ্রের নাম', 'শ্রেণি',
                     'স্কুল (নিবন্ধিত)', 'মাদ্রাসা (নিবন্ধিত)', 'মোট (নিবন্ধিত)',
                     'স্কুল (পরীক্ষায় উপস্থিত)', 'মাদ্রাসা (পরীক্ষায় উপস্থিত)', 'মোট (পরীক্ষায় উপস্থিত)'])
    for row in report_rows:
        cname = row["center_name_bn"] or row["center_name_en"]
        for cls in row["classes"]:
            reg = cls["registered"]
            att = cls["attendance"]
            writer.writerow([
                row["center_code"], cname, cls["class_name"],
                reg["school"], reg["madrasha"], reg["total"],
                att["school"], att["madrasha"], att["total"],
            ])
        rt = row["registered_total"]
        at = row["attendance_total"]
        writer.writerow([
            row["center_code"], cname, 'সর্বমোট',
            rt["school"], rt["madrasha"], rt["total"],
            at["school"], at["madrasha"], at["total"],
        ])
    if grand_total and len(report_rows) > 1:
        for cls in grand_total["classes"]:
            reg = cls["registered"]
            att = cls["attendance"]
            writer.writerow([
                'সকল কেন্দ্র', 'গ্র্যান্ড টোটাল', cls["class_name"],
                reg["school"], reg["madrasha"], reg["total"],
                att["school"], att["madrasha"], att["total"],
            ])
        rt = grand_total["registered_total"]
        at = grand_total["attendance_total"]
        writer.writerow([
            'সকল কেন্দ্র', 'গ্র্যান্ড টোটাল', 'সর্বমোট',
            rt["school"], rt["madrasha"], rt["total"],
            at["school"], at["madrasha"], at["total"],
        ])
    output.seek(0)
    fname = f"Participant_Summary_{selected_center}_{year}.csv"
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-disposition": f"attachment; filename={fname}"})


# ---------------------------------------------------------------------
# Institute -> Class (5 to 9) wise Participation Summary
# ---------------------------------------------------------------------
def build_institute_class_summary(status_filter='Verified', center_filter=''):
    """Builds an Institute-first, Class(5..9)-wise participation matrix:
    {institute_en, institute_bn, classes: {'5':n,...,'9':n}, other, total}"""
    classes_order = ['5', '6', '7', '8', '9']
    match_stage = {}
    if status_filter == 'Verified':
        match_stage["status"] = "Verified"
    elif status_filter == 'Pending':
        match_stage["status"] = {"$ne": "Verified"}
    if center_filter:
        match_stage["center_code"] = center_code_filter(center_filter)

    pipeline = []
    if match_stage:
        pipeline.append({"$match": match_stage})
    pipeline.append({"$group": {
        "_id": {"institute_en": "$institute_en", "student_class": "$student_class"},
        "institute_bn": {"$first": "$institute_bn"},
        "count": {"$sum": 1}
    }})
    rows = list(mongo.db.students.aggregate(pipeline))

    institute_map = {}
    for r in rows:
        inst_en = (r["_id"].get("institute_en") or '').strip() or 'Not Set'
        cls = str(r["_id"].get("student_class") or '').strip()
        if inst_en not in institute_map:
            institute_map[inst_en] = {
                "institute_en": inst_en,
                "institute_bn": r.get("institute_bn") or '',
                "classes": {c: 0 for c in classes_order},
                "other": 0,
                "total": 0,
            }
        if cls in institute_map[inst_en]["classes"]:
            institute_map[inst_en]["classes"][cls] += r["count"]
        else:
            institute_map[inst_en]["other"] += r["count"]
        institute_map[inst_en]["total"] += r["count"]

    institute_rows = sorted(institute_map.values(), key=lambda x: x["institute_en"].lower())
    grand_total = {
        "classes": {c: sum(row["classes"][c] for row in institute_rows) for c in classes_order},
        "other": sum(row["other"] for row in institute_rows),
        "total": sum(row["total"] for row in institute_rows),
    }
    return institute_rows, grand_total, classes_order


@app.route('/admin/participant-summary/institute-class')
def institute_class_summary():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    centers = list(mongo.db.centers.find().sort("center_code", 1))
    status_filter = request.args.get('status', 'Verified')
    center_filter = request.args.get('center', '').strip()
    institute_rows, grand_total, classes_order = build_institute_class_summary(status_filter, center_filter)
    return render_template('admin_institute_class_summary.html',
                           centers=centers, status_filter=status_filter,
                           center_filter=center_filter, institute_rows=institute_rows,
                           grand_total=grand_total, classes_order=classes_order)


@app.route('/admin/participant-summary/institute-class/print')
def institute_class_summary_print():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    status_filter = request.args.get('status', 'Verified')
    center_filter = request.args.get('center', '').strip()
    institute_rows, grand_total, classes_order = build_institute_class_summary(status_filter, center_filter)
    center_label = ''
    if center_filter:
        name_map_upper = {k.upper(): v for k, v in get_center_name_map(lang='bn').items()}
        center_label = name_map_upper.get(center_filter.upper(), center_filter)
    return render_template('institute_class_summary_print.html',
                           institute_rows=institute_rows, grand_total=grand_total,
                           classes_order=classes_order, status_filter=status_filter,
                           center_filter=center_filter, center_label=center_label, now=datetime.now())


@app.route('/admin/participant-summary/institute-class/download-csv')
def institute_class_summary_download_csv():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    status_filter = request.args.get('status', 'Verified')
    center_filter = request.args.get('center', '').strip()
    institute_rows, grand_total, classes_order = build_institute_class_summary(status_filter, center_filter)

    output = io.StringIO()
    output.write(u'\ufeff')
    writer = csv.writer(output)
    writer.writerow(['#', 'Institute (English)', 'প্রতিষ্ঠানের নাম (বাংলা)'] +
                    [f"Class {c}" for c in classes_order] + ['Other', 'Total'])
    for idx, row in enumerate(institute_rows, 1):
        writer.writerow([idx, row["institute_en"], row["institute_bn"]] +
                        [row["classes"][c] for c in classes_order] +
                        [row["other"], row["total"]])
    writer.writerow(['', 'সর্বমোট (Grand Total)', ''] +
                    [grand_total["classes"][c] for c in classes_order] +
                    [grand_total["other"], grand_total["total"]])
    output.seek(0)
    fname = f"Institute_Class_Summary_{status_filter}.csv"
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-disposition": f"attachment; filename={fname}"})

@app.route('/admin/api/update_status', methods=['POST'])
def update_status():
    if not session.get('admin_logged_in'):
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    roll = data.get('roll')
    new_status = data.get('status')
    verification = True if new_status == "Verified" else False
    mongo.db.students.update_one(
        {"roll_no": roll},
        {"$set": {"status": new_status, "verification": verification}}
    )
    return jsonify({"success": True})

@app.route('/admin/attendance-sheet')
def attendance_sheet():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    center_code = request.args.get('center', '')
    student_class = request.args.get('student_class', '')
    all_centers = mongo.db.students.distinct("center_code")
    query = {"status": "Verified"}
    if center_code:
        query["center_code"] = center_code
    if student_class:
        query["student_class"] = student_class
    students = list(mongo.db.students.find(query).sort("roll_no", 1))
    return render_template('admin_attendance.html',
                           students=students,
                           all_centers=all_centers,
                           current_center=center_code or "All Centers",
                           now=datetime.now())

@app.route('/admin/seat-plan')
def seat_plan():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    center_filter = request.args.get('center', '')
    student_class = request.args.get('class', '')
    all_centers = mongo.db.students.distinct("center_code")
    query = {"status": "Verified"}
    if center_filter:
        query["center_code"] = center_filter
    if student_class:
        query["student_class"] = str(student_class)
    students = list(mongo.db.students.find(query).sort([("student_class", 1), ("roll_no", 1)]))
    return render_template('admin_seat_plan.html', students=students, all_centers=all_centers)

@app.route('/admin/entry-marks', methods=['GET'])
def entry_marks():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    institutes = list(mongo.db.institutions.find().sort("name", 1))
    centers = list(mongo.db.centers.find().sort("center_code", 1))
    f_roll = request.args.get('roll_no')
    f_class = request.args.get('class')
    f_inst = request.args.get('institute')
    f_center = request.args.get('center')
    query = {"status": "Verified"}
    if f_roll:
        query["roll_no"] = f_roll
    else:
        if f_class:
            query["student_class"] = f_class
        if f_inst:
            query["institute_en"] = f_inst
        if f_center:
            query["center_code"] = center_code_filter(f_center)
    students = []
    if f_roll or f_class or f_center:
        students = list(mongo.db.students.find(query).sort("roll_no", 1))
    return render_template('admin_marks_entry.html', students=students, institutes=institutes, centers=centers)

@app.route('/admin/save-bulk-marks', methods=['POST'])
def save_bulk_marks():
    if not session.get('admin_logged_in'):
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
    data = request.get_json()
    if not data:
        return jsonify({"status": "error", "message": "No data received"}), 400
    try:
        roll_no = data.get('roll_no')
        def clean_val(val):
            try: return float(val) if val else 0.0
            except: return 0.0
        m_ban = clean_val(data.get('ban'))
        m_eng = clean_val(data.get('eng'))
        m_math = clean_val(data.get('math'))
        m_gk = clean_val(data.get('gk'))
        total = m_ban + m_eng + m_math + m_gk
        s_grade = data.get('scholarship_grade', "Nothing")
        mongo.db.students.update_one(
            {"roll_no": roll_no},
            {"$set": {
                "marks": {"bangla": m_ban, "english": m_eng, "math": m_math, "gk": m_gk, "total": total},
                "scholarship_grade": s_grade,
                "result_published": True
            }}
        )
        return jsonify({"status": "success", "roll": roll_no}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/admin/toggle-result-publish', methods=['POST'])
def toggle_result_publish():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    setting = mongo.db.settings.find_one({"key": "result_published"})
    current_status = setting['value'] if setting else False
    new_status = not current_status
    mongo.db.settings.update_one(
        {"key": "result_published"},
        {"$set": {"value": new_status}},
        upsert=True
    )
    flash(f"Results are now {'Public' if new_status else 'Hidden'}", "success")
    return redirect(url_for('manage_results'))


@app.route('/admin/toggle-registration', methods=['POST'])
def toggle_registration():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    new_status = not is_registration_open()
    mongo.db.settings.update_one(
        {"key": "registration_open"},
        {"$set": {"value": new_status}},
        upsert=True
    )
    flash(f"রেজিস্ট্রেশন এখন {'চালু' if new_status else 'বন্ধ'} করা হয়েছে।", "success")
    return redirect(url_for('admin_home_settings'))


@app.route('/admin/update-registration-message', methods=['POST'])
def update_registration_message():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    message = request.form.get('registration_closed_message', '').strip()
    mongo.db.settings.update_one(
        {"key": "registration_closed_message"},
        {"$set": {"value": message}},
        upsert=True
    )
    flash("রেজিস্ট্রেশন বন্ধের বার্তা আপডেট হয়েছে।", "success")
    return redirect(url_for('admin_home_settings'))

@app.route('/admin/manage-results')
def manage_results():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    f_class = request.args.get('class', '')
    f_center = request.args.get('center', '')
    f_grade = request.args.get('grade', '')
    f_sort = request.args.get('sort', 'merit')
    setting = mongo.db.settings.find_one({"key": "result_published"})
    is_published = setting['value'] if setting else False
    query = {"marks": {"$exists": True}}
    if f_class:
        query["student_class"] = f_class
    if f_center:
        query["center_code"] = f_center
    if f_grade:
        if f_grade == 'Nothing':
            query["scholarship_grade"] = {"$exists": False}
        else:
            query["scholarship_grade"] = f_grade
    sort_logic = [("marks.total", -1)]
    if f_sort == 'roll':
        sort_logic = [("roll_no", 1)]
    elif f_sort == 'name':
        sort_logic = [("name_en", 1)]
    results = list(mongo.db.students.find(query).sort(sort_logic))
    all_centers = mongo.db.students.distinct("center_code")
    total_count = len(results)
    sum_marks = sum((s.get('marks') or {}).get('total', 0) for s in results)
    avg_score = (sum_marks / total_count) if total_count > 0 else 0
    return render_template('admin_manage_results.html',
                           results=results,
                           is_published=is_published,
                           total_count=total_count,
                           sum_marks=sum_marks,
                           avg_score=avg_score,
                           centers=all_centers)

@app.route('/admin/approve-admits', methods=['GET', 'POST'])
def approve_admits():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        student_ids = request.form.getlist('selected_students')
        action = request.form.get('action')
        filter_center = request.form.get('filter_center', '').strip()
        filter_class = request.form.get('filter_class', '').strip()
        filter_institute = request.form.get('filter_institute', '').strip()
        redirect_args = {}
        if filter_center:
            redirect_args['center'] = filter_center
        if filter_class:
            redirect_args['class'] = filter_class
        if filter_institute:
            redirect_args['institute'] = filter_institute
        if not student_ids:
            flash("দয়া করে অন্তত একজন ছাত্র সিলেক্ট করুন!", "warning")
            return redirect(url_for('approve_admits', **redirect_args))
        try:
            status = True if action == 'approve' else False
            result = mongo.db.students.update_many(
                {"_id": {"$in": [ObjectId(sid) for sid in student_ids]}},
                {"$set": {"admit_approved": status}}
            )
            if result.modified_count > 0:
                flash(f"সফলভাবে {len(student_ids)} জন ছাত্রের এডমিট কার্ড আপডেট হয়েছে।", "success")
            else:
                flash("কোনো পরিবর্তন করা হয়নি।", "info")
        except Exception as e:
            flash(f"সিস্টেম এরর: {str(e)}", "danger")
        return redirect(url_for('approve_admits', **redirect_args))

    filter_center = request.args.get('center', '').strip()
    filter_class = request.args.get('class', '').strip()
    filter_institute = request.args.get('institute', '').strip()
    query = {}
    if filter_center:
        query["center_code"] = center_code_filter(filter_center)
    if filter_class:
        query["student_class"] = filter_class
    if filter_institute:
        query["institute_en"] = filter_institute
    centers = list(mongo.db.centers.find().sort("center_code", 1))
    available_classes = ["5", "6", "7", "8", "9"]
    institutes = sorted({i for i in mongo.db.students.distinct('institute_en') if i})
    students = list(mongo.db.students.find(query).sort("roll_no", 1))
    return render_template('admin_approve_admits.html', students=students, centers=centers,
                           available_classes=available_classes, institutes=institutes,
                           filter_center=filter_center, filter_class=filter_class,
                           filter_institute=filter_institute)

@app.route('/admin/scholarship/labels')
def scholarship_labels():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    center_query = request.args.get('center', '').strip()
    roll_query = request.args.get('roll', '').strip()
    school_query = request.args.get('school', '').strip()
    class_query = request.args.get('student_class', '').strip()

    query = {"status": "Verified"}
    if center_query:
        query["center_code"] = center_code_filter(center_query)
    if roll_query:
        query["roll_no"] = roll_query
    if class_query:
        query["student_class"] = class_query

    # --- Institute filter (works on BOTH Bangla and English name fields) ---
    # Build the canonical list of distinct institute names first, so the form
    # can offer an exact-pick dropdown. If the chosen value matches a known
    # institute exactly we filter exactly; otherwise we fall back to a
    # case-insensitive "contains" match so partial typing still works.
    inst_set = {}
    for s in mongo.db.students.find({"status": "Verified"}, {"institute_bn": 1, "institute_en": 1}):
        name = (s.get('institute_bn') or s.get('institute_en') or '').strip()
        if name:
            inst_set[name] = True
    all_institutes = sorted(inst_set.keys())

    if school_query:
        if school_query in inst_set:
            query["$or"] = [
                {"institute_bn": school_query},
                {"institute_en": school_query},
            ]
        else:
            esc = re.escape(school_query)
            query["$or"] = [
                {"institute_bn": {"$regex": esc, "$options": "i"}},
                {"institute_en": {"$regex": esc, "$options": "i"}},
            ]

    students_list = list(mongo.db.students.find(query).sort("roll_no", 1))

    # Center dropdown: show "code — name" using the live center map.
    center_name_map = get_center_name_map(lang='bn')
    raw_centers = mongo.db.students.distinct("center_code")
    all_centers = sorted(
        [str(c) for c in raw_centers if str(c).strip()],
        key=lambda x: (len(x), x)
    )

    return render_template('admin_labels.html',
                           students=students_list,
                           all_centers=all_centers,
                           center_name_map=center_name_map,
                           all_institutes=all_institutes)

@app.route('/admin/centers')
def manage_centers():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    centers = list(mongo.db.centers.find().sort("center_code", 1))
    bkash_s = mongo.db.settings.find_one({"key": "bkash_number"})
    nagad_s = mongo.db.settings.find_one({"key": "nagad_number"})
    bkash_number = bkash_s['value'] if bkash_s else ''
    nagad_number = nagad_s['value'] if nagad_s else ''

    center_name_map = get_center_name_map()
    groups_raw = list(mongo.db.center_groups.find().sort("group_name_bn", 1))
    grouped_codes = set()
    center_groups = []
    for g in groups_raw:
        codes = g.get('member_codes', [])
        grouped_codes.update(str(c) for c in codes)
        center_groups.append({
            "_id": g["_id"],
            "group_name_en": g.get("group_name_en") or g.get("group_name", ""),
            "group_name_bn": g.get("group_name_bn") or g.get("group_name", ""),
            "member_codes": codes,
            "member_labels": [f"{c} - {center_name_map.get(str(c), c)}" for c in codes],
        })

    return render_template('admin_center.html', centers=centers, bkash_number=bkash_number,
                           nagad_number=nagad_number, center_groups=center_groups,
                           grouped_codes=grouped_codes)

@app.route('/admin/add-center-group', methods=['POST'])
def add_center_group():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    group_name_en = request.form.get('group_name_en', '').strip()
    group_name_bn = request.form.get('group_name_bn', '').strip()
    member_codes = [c.strip() for c in request.form.getlist('member_codes') if c.strip()]
    if not group_name_en or not group_name_bn or not member_codes:
        flash("গ্রুপের নাম (ইংরেজি ও বাংলা — দুটোই) এবং অন্তত একটি কেন্দ্র নির্বাচন করা আবশ্যক।", "danger")
        return redirect(url_for('manage_centers'))

    already_grouped = set()
    for g in mongo.db.center_groups.find():
        already_grouped.update(str(c) for c in g.get('member_codes', []))
    conflicting = [c for c in member_codes if c in already_grouped]
    if conflicting:
        flash(f"এই কেন্দ্রগুলো ইতিমধ্যে অন্য একটি গ্রুপে আছে: {', '.join(conflicting)}। আগে সেই গ্রুপ থেকে বাদ দিন (গ্রুপ মুছে ফেলুন)।", "danger")
        return redirect(url_for('manage_centers'))

    mongo.db.center_groups.insert_one({
        "group_name_en": group_name_en,
        "group_name_bn": group_name_bn,
        "member_codes": member_codes,
        "created_at": datetime.utcnow()
    })
    flash(f"'{group_name_bn}' গ্রুপ সফলভাবে তৈরি হয়েছে। সার্টিফিকেটে '{group_name_en}' এবং প্রসপেক্টাসে '{group_name_bn}' নামটি দেখাবে।", "success")
    return redirect(url_for('manage_centers'))

@app.route('/admin/delete-center-group/<group_id>')
def delete_center_group(group_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    mongo.db.center_groups.delete_one({"_id": ObjectId(group_id)})
    flash("কেন্দ্র গ্রুপ মুছে ফেলা হয়েছে।", "info")
    return redirect(url_for('manage_centers'))

@app.route('/admin/update-payment-numbers', methods=['POST'])
def update_payment_numbers():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    bkash = request.form.get('bkash_number', '').strip()
    nagad = request.form.get('nagad_number', '').strip()
    if bkash:
        mongo.db.settings.update_one({"key": "bkash_number"}, {"$set": {"value": bkash}}, upsert=True)
    if nagad:
        mongo.db.settings.update_one({"key": "nagad_number"}, {"$set": {"value": nagad}}, upsert=True)
    flash("পেমেন্ট নম্বর আপডেট হয়েছে।", "success")
    return redirect(url_for('admin_center'))

@app.route('/admin/add_center', methods=['POST'])
def add_center():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    center_code = request.form.get('center_code', '').strip().upper()
    center_name_en = request.form.get('center_name_en', '').strip()
    center_name_bn = request.form.get('center_name_bn', '').strip()
    center_phone = request.form.get('center_phone', '').strip()
    if not center_code or not center_name_en or not center_name_bn:
        flash("All fields (Code, English Name, Bangla Name) are required!", "danger")
        return redirect(url_for('manage_centers'))
    existing = mongo.db.centers.find_one({"center_code": center_code})
    if not existing:
        mongo.db.centers.insert_one({
            "center_code": center_code,
            "center_name_en": center_name_en,
            "center_name_bn": center_name_bn,
            "center_phone": center_phone
        })
        flash(f"Success! {center_name_en} ({center_code}) has been added.", "success")
    else:
        flash(f"Error! Center code {center_code} already exists.", "danger")
    return redirect(url_for('manage_centers'))

@app.route('/admin/delete_center/<center_id>')
def delete_center(center_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    try:
        center_to_delete = mongo.db.centers.find_one({"_id": ObjectId(center_id)})
        if center_to_delete:
            student_count = mongo.db.students.count_documents({"center_code": center_to_delete['center_code']})
            if student_count > 0:
                flash(f"Cannot delete! There are {student_count} students registered in this center.", "danger")
            else:
                mongo.db.centers.delete_one({"_id": ObjectId(center_id)})
                flash("Center deleted successfully!", "info")
        else:
            flash("Center not found!", "warning")
    except Exception as e:
        flash(f"An error occurred: {str(e)}", "danger")
    return redirect(url_for('manage_centers'))

@app.route('/admin/admit-settings', methods=['GET', 'POST'])
def admin_admit_settings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        data = {
            "key": "admit",
            "signature_image": request.form.get("signature_image", "").strip(),
            "signature_title": request.form.get("signature_title", "").strip() or "পরীক্ষা নিয়ন্ত্রক",
            "exam_datetime": request.form.get("exam_datetime", "").strip(),
        }
        mongo.db.admit_settings.update_one({"key": "admit"}, {"$set": data}, upsert=True)
        flash("এডমিট কার্ড সেটিংস সফলভাবে আপডেট হয়েছে। এখন থেকে সব এডমিট কার্ডে (একক ও বাল্ক) এই তথ্য দেখানো হবে।", "success")
        return redirect(url_for('admin_admit_settings'))
    return render_template('admin_admit_settings.html', s=get_admit_settings())

@app.route('/admin/certificate-settings', methods=['GET', 'POST'])
def admin_certificate_settings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        data = {
            "key": "cert",
            "signature_image": request.form.get("signature_image", "").strip(),
            "signature_name": request.form.get("signature_name", "").strip(),
            "publication_date": request.form.get("publication_date", "").strip(),
        }
        mongo.db.cert_settings.update_one({"key": "cert"}, {"$set": data}, upsert=True)
        flash("সার্টিফিকেট সেটিংস সফলভাবে আপডেট হয়েছে। এখন থেকে সব সার্টিফিকেটে এই স্বাক্ষর ও তারিখ দেখানো হবে।", "success")
        return redirect(url_for('admin_certificate_settings'))
    return render_template('admin_certificate_settings.html', s=get_cert_settings())


@app.route('/admin/certificate-layout', methods=['GET'])
def admin_certificate_layout():
    """Drag-and-drop editor: position every certificate field over the real
    background image, then save. Saved positions are used by both the single
    and bulk certificate prints."""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    return render_template(
        'admin_certificate_layout.html',
        layout=get_cert_layout(),
        defaults=DEFAULT_CERT_LAYOUT,
        fields=CERT_FIELD_LABELS,
        samples=CERT_FIELD_SAMPLES,
    )


@app.route('/admin/certificate-layout/save', methods=['POST'])
def save_certificate_layout():
    """Persist the dragged field layout (JSON body: {field: {top,left,width,
    font_size}}). Each value is validated/clamped before saving."""
    if not session.get('admin_logged_in'):
        return jsonify({"ok": False, "error": "auth"}), 403
    payload = request.get_json(silent=True) or {}
    incoming = payload.get("layout", payload)
    clean = {}
    for field, default in DEFAULT_CERT_LAYOUT.items():
        clean[field] = _coerce_layout_entry(default, incoming.get(field))
    mongo.db.cert_settings.update_one(
        {"key": "cert"}, {"$set": {"layout": clean}}, upsert=True
    )
    return jsonify({"ok": True, "layout": clean})


@app.route('/admin/certificate-layout/reset', methods=['POST'])
def reset_certificate_layout():
    """Remove the custom layout so certificates fall back to the built-in
    calibrated default positions."""
    if not session.get('admin_logged_in'):
        return jsonify({"ok": False, "error": "auth"}), 403
    mongo.db.cert_settings.update_one(
        {"key": "cert"}, {"$unset": {"layout": ""}}, upsert=True
    )
    return jsonify({"ok": True, "layout": DEFAULT_CERT_LAYOUT})

@app.route('/admin/notices')
def admin_notices():
    notices = mongo.db.notices.find().sort("_id", -1)
    return render_template('admin_notices.html', notices=notices)

@app.route('/admin/add_notice', methods=['POST'])
def add_notice():
    import datetime as dt
    notice_data = {
        "title": request.form.get('title'),
        "content": request.form.get('content'),
        "category": request.form.get('category'),
        "date": dt.datetime.now().strftime("%b %d, %Y")
    }
    mongo.db.notices.insert_one(notice_data)
    return redirect(url_for('admin_notices'))

@app.route('/admin/delete_notice/<notice_id>')
def delete_notice(notice_id):
    mongo.db.notices.delete_one({"_id": ObjectId(notice_id)})
    return redirect(url_for('admin_notices'))

@app.route('/admin/institutions')
def manage_institutions():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    institutes = list(mongo.db.institutions.find().sort("name", 1))
    return render_template('admin_institutes.html', institutes=institutes)

@app.route('/admin/add_institute', methods=['POST'])
def add_institute():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    inst_name_en = request.form.get('name', '').strip()
    inst_name_bn = request.form.get('name_bn', '').strip()
    if not inst_name_en:
        flash("Institution name cannot be empty!", "danger")
        return redirect(url_for('manage_institutions'))
    existing = mongo.db.institutions.find_one({"name": inst_name_en})
    if not existing:
        mongo.db.institutions.insert_one({"name": inst_name_en, "bn": inst_name_bn})
        flash(f"Successfully added: {inst_name_en}", "success")
    else:
        flash(f"Error! {inst_name_en} is already in the list.", "danger")
    return redirect(url_for('manage_institutions'))

@app.route('/admin/delete_institute/<inst_id>')
def delete_institute(inst_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    try:
        inst = mongo.db.institutions.find_one({"_id": ObjectId(inst_id)})
        if inst:
            student_exists = mongo.db.students.find_one({"institute_en": inst['name']})
            if student_exists:
                flash("Cannot delete! Some students are already registered from this institution.", "danger")
            else:
                mongo.db.institutions.delete_one({"_id": ObjectId(inst_id)})
                flash("Institution deleted successfully.", "info")
        else:
            flash("Institution not found.", "warning")
    except Exception as e:
        flash(f"Error: {str(e)}", "danger")
    return redirect(url_for('manage_institutions'))

@app.route('/admin/serial-allocation', methods=['GET', 'POST'])
def serial_allocation():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    centers_list = [
        {"code": c.get('center_code'), "name": c.get('center_name_en') or c.get('center_name_bn')}
        for c in mongo.db.centers.find().sort("center_code", 1)
    ]
    if request.method == 'POST':
        try:
            target_class = request.form.get('student_class')
            c_code = request.form.get('center_code')
            start_roll = int(request.form.get('start_roll'))
            start_reg = int(request.form.get('start_reg'))
            query = {
                "student_class": target_class,
                "center_code": {"$in": [c_code, int(c_code) if c_code.isdigit() else c_code]},
                "status": "Verified"
            }
            students = list(mongo.db.students.find(query).sort([("institute_en", 1), ("name_en", 1)]))
            print(f"Query: {query}, Found: {len(students)} students")
            if not students:
                flash(f"সতর্কতা: Class {target_class}-এ এই সেন্টারে কোনো ভেরিফাইড ছাত্র পাওয়া যায়নি।", "warning")
                return redirect(request.url)
            for index, student in enumerate(students):
                update_fields = {"roll_no": str(start_roll + index), "reg_no": str(start_reg + index)}
                # Preserve permanent login serial — backfill from old roll_no if missing
                if not student.get('serial_no'):
                    update_fields["serial_no"] = str(student.get('roll_no', ''))
                mongo.db.students.update_one(
                    {"_id": student["_id"]},
                    {"$set": update_fields}
                )
            flash(f"সফল! {len(students)} জন ছাত্রের রোল ({start_roll} থেকে শুরু) আপডেট করা হয়েছে।", "success")
        except Exception as e:
            flash(f"Error: {str(e)}", "danger")
    return render_template('admin_serial.html', centers=centers_list)

# =====================================================================
# RESULT NOTICE SETTINGS — admin-editable letterhead/announcement text
# & signatories for /admin/print-result. Roll-number tables and the
# grade counts are NEVER stored here — those stay 100% auto-computed
# from the students collection at print time. Single source of truth
# shared by the print page and its admin settings page so edits in one
# always show up in the other immediately.
# =====================================================================

RESULT_ORG_DEFAULTS = {
    'name_bn': 'দ্যা ব্রিলিয়ান্টস্ ফাউন্ডেশন,বগুড়া',
    'name_en': "The Brilliant's Foundation,Bogura",
    'reg_no': 'S-9759',
    'address': 'ব্রিলিয়ান্টস্ হাউজ,সবুজবাগ,বগুড়া।',
    'mobile': '০১৭৮০-২৭৭৪৪৩',
    'email': 'tbfbogura2002@gmail.com',
    'logo_url': 'https://i.postimg.cc/SsLDX6WZ/Screenshot_2026_01_20_020601_removebg_preview.png',
}

RESULT_ANNOUNCEMENT_DEFAULTS = {
    'exam_label': 'বৃত্তি পরীক্ষা-২০২৫',
    'exam_date': '২৫/১২/২০২৫',
    'center_count': '৯',
    'sub_center_count': '১',
    'centers': [
        'সারিয়াকান্দি', 'গাবতলী', 'খোট্রাপাড়া', 'শাজাহানপুর (আড়িয়া)',
        'শাজাহানপুর (রানিরহাট)', 'শেরপুর (সামিট)', 'শেরপুর (ছোনকা)',
        'ধুনট', 'সোনাতলা (সুখানপুকুর)', 'সোনাতলা (ফাজিল মাদ্রাসা)'
    ],
    'result_date': '১৭ই মার্চ ২০২৬',
    'result_time': 'দুপুর ২.০০',
    'recipient_name': 'শাহরিয়ার হাসান বিপ্লব',
    'giver_name': 'রাকিবুল ইসলাম রবিন',
    'present_persons': [
        'পরিচালক তৌফিকুল ইসলাম তাকি', 'সদস্য সচিব তাহিরুল হাবিব',
        'রেজিস্টার মানিক মিয়া', 'কার্যনির্বাহী সদস্যবৃন্দ'
    ],
    'fb_link': 'https://www.facebook.com/thebrilliantsbogura',
    'top_school_roll': '২৫৬৫২০৪',
    'top_madrasha_roll': '২৫৫৫০৯২',
}

RESULT_SIGNATORIES_DEFAULT = [
    {'name': 'রাকিবুল ইসলাম রবিন', 'title': 'পরীক্ষা নিয়ন্ত্রক', 'date': '১৭.০৩.২৬',
     'signature_image': 'https://i.postimg.cc/sX21ngh3/rsz-screenshot-2026-01-23-185732.png'},
    {'name': 'তৌফিকুল ইসলাম তাকি', 'title': 'পরিচালক', 'date': '১৭.৩.২৬',
     'signature_image': 'https://i.postimg.cc/sX21ngh3/rsz-screenshot-2026-01-23-185732.png'},
    {'name': 'শাহরিয়ার হাসান বিপ্লব', 'title': 'মহাপরিচালক', 'date': '১৭.৩.২৬',
     'signature_image': 'https://i.postimg.cc/sX21ngh3/rsz-screenshot-2026-01-23-185732.png'},
]

def get_result_settings():
    """Reads mongo.db.result_settings and merges per-field defaults (instead
    of swapping the whole sub-document) so a partial save never blanks out
    fields the admin hasn't touched yet. Returns the raw settings doc plus
    the four pieces print_result.html needs."""
    settings = mongo.db.result_settings.find_one() or {}

    org = dict(settings.get('org') or {})
    for k, v in RESULT_ORG_DEFAULTS.items():
        org.setdefault(k, v)

    notice_date = settings.get('notice_date') or '১৭/০৩/২০২৬ ইং'

    announcement = dict(settings.get('announcement') or {})
    for k, v in RESULT_ANNOUNCEMENT_DEFAULTS.items():
        announcement.setdefault(k, v)

    signatories = settings.get('signatories', RESULT_SIGNATORIES_DEFAULT)

    return settings, org, notice_date, announcement, signatories


# =====================================================================
# PRINT RESULT PAGE — roll numbers & counts are 100% auto from DB.
# Everything else comes from get_result_settings() above.
# =====================================================================

@app.route('/admin/print-result')
def print_result():
    BN_DIGITS = str.maketrans('0123456789', '০১২৩৪৫৬৭৮৯')
    def bn(value):
        return str(value).translate(BN_DIGITS)

    classes_meta = [
        {'id': '5', 'name_bn': '৫ম'},
        {'id': '6', 'name_bn': '৬ষ্ঠ'},
        {'id': '7', 'name_bn': '৭ম'},
        {'id': '8', 'name_bn': '৮ম'},
        {'id': '9', 'name_bn': '৯ম'},
    ]

    # DB grade value -> template field key. 'Suveccha' holds Institutional
    # Merit students and 'Quata' holds the Greeting/Shuveccha group — same
    # mapping as your existing /admin/print-result summary route.
    grade_map = {
        'Talentpool': 'talentpool',
        'General': 'general',
        'Suveccha': 'institutional_merit',
        'Quata': 'shuveccha',
    }

    classes = []
    grade_totals = {'talentpool': 0, 'general': 0, 'institutional_merit': 0, 'shuveccha': 0}

    for cls in classes_meta:
        cls_row = {'class_display': cls['name_bn']}
        for db_grade, field_key in grade_map.items():
            students = mongo.db.students.find(
                {'student_class': {'$in': [cls['id'], int(cls['id'])]}, 'scholarship_grade': db_grade},
                {'roll_no': 1, '_id': 0}
            ).sort('roll_no', 1)
            rolls = [bn(s['roll_no']) for s in students]
            cls_row[field_key] = rolls
            grade_totals[field_key] += len(rolls)
        classes.append(cls_row)

    total_awarded = sum(grade_totals.values())

    # Letterhead / announcement text that isn't derivable from the students
    # collection — admin-editable via /admin/result-settings, with built-in
    # fallbacks if nothing's been saved yet.
    settings, org, notice_date, announcement, signatories = get_result_settings()

    # Computed live from the roll-number queries above, so these can never
    # drift out of sync with the tables — never admin-editable.
    announcement['talentpool_count'] = bn(grade_totals['talentpool'])
    announcement['general_count'] = bn(grade_totals['general'])
    announcement['institutional_merit_count'] = bn(grade_totals['institutional_merit'])
    announcement['susveccha_count'] = bn(grade_totals['shuveccha'])
    announcement['total_awarded'] = bn(total_awarded)
    # total_examinees: auto-counted from the students collection unless the
    # admin has explicitly overridden it on the settings page.
    total_examinees_override = settings.get('total_examinees')
    announcement['total_examinees'] = bn(total_examinees_override) if total_examinees_override else bn(mongo.db.students.count_documents({}))

    return render_template(
        'print_result.html',
        org=org,
        notice_date=notice_date,
        announcement=announcement,
        classes=classes,
        signatories=signatories
    )


# =====================================================================
# RESULT PRINT SETTINGS — admin form for everything above except the
# auto-computed roll numbers/counts.
# =====================================================================

@app.route('/admin/result-settings', methods=['GET', 'POST'])
def admin_result_settings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_org':
            org_doc = {k: request.form.get(k, '').strip() for k in RESULT_ORG_DEFAULTS}
            mongo.db.result_settings.update_one(
                {}, {"$set": {"org": org_doc, "notice_date": request.form.get('notice_date', '').strip()}},
                upsert=True
            )
            flash("প্রতিষ্ঠানের তথ্য সফলভাবে আপডেট হয়েছে।", "success")

        elif action == 'update_announcement':
            text_fields = ['exam_label', 'exam_date', 'center_count', 'sub_center_count',
                            'result_date', 'result_time', 'recipient_name', 'giver_name',
                            'fb_link', 'top_school_roll', 'top_madrasha_roll']
            set_ops = {f"announcement.{f}": request.form.get(f, '').strip() for f in text_fields}
            total_examinees = request.form.get('total_examinees', '').strip()
            if total_examinees:
                set_ops['total_examinees'] = total_examinees
                mongo.db.result_settings.update_one({}, {"$set": set_ops}, upsert=True)
            else:
                mongo.db.result_settings.update_one({}, {"$set": set_ops}, upsert=True)
                mongo.db.result_settings.update_one({}, {"$unset": {"total_examinees": ""}})
            flash("ঘোষণার তথ্য সফলভাবে আপডেট হয়েছে।", "success")

        elif action == 'add_center':
            name = request.form.get('center_name', '').strip()
            if name:
                mongo.db.result_settings.update_one({}, {"$push": {"announcement.centers": name}}, upsert=True)
                flash("কেন্দ্র যোগ করা হয়েছে।", "success")

        elif action == 'remove_center':
            mongo.db.result_settings.update_one({}, {"$pull": {"announcement.centers": request.form.get('center_name', '')}})
            flash("কেন্দ্র মুছে ফেলা হয়েছে।", "success")

        elif action == 'add_person':
            name = request.form.get('person_name', '').strip()
            if name:
                mongo.db.result_settings.update_one({}, {"$push": {"announcement.present_persons": name}}, upsert=True)
                flash("নাম যোগ করা হয়েছে।", "success")

        elif action == 'remove_person':
            mongo.db.result_settings.update_one({}, {"$pull": {"announcement.present_persons": request.form.get('person_name', '')}})
            flash("নাম মুছে ফেলা হয়েছে।", "success")

        elif action == 'add_signatory':
            sig = {
                "name": request.form.get('sig_name', '').strip(),
                "title": request.form.get('sig_title', '').strip(),
                "date": request.form.get('sig_date', '').strip(),
                "signature_image": request.form.get('sig_image', '').strip(),
            }
            if sig['name']:
                mongo.db.result_settings.update_one({}, {"$push": {"signatories": sig}}, upsert=True)
                flash("স্বাক্ষরকারী যোগ করা হয়েছে।", "success")

        elif action == 'update_signatory':
            idx = int(request.form.get('sig_index', -1))
            doc = mongo.db.result_settings.find_one() or {}
            sigs = doc.get('signatories', list(RESULT_SIGNATORIES_DEFAULT))
            if 0 <= idx < len(sigs):
                sigs[idx] = {
                    "name": request.form.get('sig_name', '').strip(),
                    "title": request.form.get('sig_title', '').strip(),
                    "date": request.form.get('sig_date', '').strip(),
                    "signature_image": request.form.get('sig_image', '').strip(),
                }
                mongo.db.result_settings.update_one({}, {"$set": {"signatories": sigs}}, upsert=True)
                flash("স্বাক্ষরকারীর তথ্য আপডেট করা হয়েছে।", "success")

        elif action == 'remove_signatory':
            idx = int(request.form.get('sig_index', -1))
            doc = mongo.db.result_settings.find_one() or {}
            sigs = doc.get('signatories', list(RESULT_SIGNATORIES_DEFAULT))
            if 0 <= idx < len(sigs):
                sigs.pop(idx)
                mongo.db.result_settings.update_one({}, {"$set": {"signatories": sigs}}, upsert=True)
                flash("স্বাক্ষরকারী মুছে ফেলা হয়েছে।", "success")

        return redirect(url_for('admin_result_settings'))

    settings, org, notice_date, announcement, signatories = get_result_settings()
    return render_template(
        'admin_result_settings.html',
        org=org,
        notice_date=notice_date,
        announcement=announcement,
        signatories=signatories,
        settings_total_examinees=settings.get('total_examinees', '')
    )

@app.route('/forgot-serial', methods=['GET', 'POST'])
def forgot_serial():
    student_data = None
    if request.method == 'POST':
        input_mobile = request.form.get('phone', '').strip()
        student = mongo.db.students.find_one({"mobile": input_mobile})
        if not student and input_mobile.isdigit():
            student = mongo.db.students.find_one({"mobile": int(input_mobile)})
        if student:
            student_data = {'serial': student.get('serial_no') or student.get('roll_no'), 'name': student.get('name_en')}
        else:
            flash('এই মোবাইল নম্বর দিয়ে কোনো শিক্ষার্থী পাওয়া যায়নি!', 'danger')
    return render_template('forgot_serial.html', student=student_data)


# =====================================================================
# CERTIFICATE SERIAL NUMBER (SL NO.) — auto-generated, 4-digit, GLOBALLY
# UNIQUE across every certificate (0001 .. 9999). Not scoped per class or
# institute. The whole scholarship pool is numbered in roll-number order and
# the value is saved back onto the student document so reprints always show
# the same serial.
# =====================================================================

def get_or_assign_certificate_serial(student):
    """Return the 4-digit certificate serial number (e.g. '0001') for a
    scholarship-winning student. The serial is GLOBALLY UNIQUE across every
    certificate in the system (0001 .. 9999) — it is NOT scoped per class or
    institute. The whole scholarship pool is ordered by roll number for a
    stable, predictable sequence; once a number is assigned it is persisted on
    the student document and never reshuffles on reprint."""
    existing = student.get('certificate_sl_no')
    if existing:
        return existing

    # Global pool of all scholarship-winning students, ordered by roll number
    # so the numbering is stable and predictable for everyone.
    group_query = {
        "scholarship_grade": {"$exists": True, "$nin": [None, "", "Nothing"]}
    }
    group_students = list(mongo.db.students.find(group_query).sort("roll_no", 1))

    # Highest serial already handed out, so re-runs keep extending the
    # sequence instead of reshuffling numbers that are already in print.
    used = [
        int(s['certificate_sl_no'])
        for s in group_students
        if s.get('certificate_sl_no') and str(s['certificate_sl_no']).isdigit()
    ]
    next_serial = (max(used) + 1) if used else 1

    assigned_serial = None
    for s in group_students:
        if s.get('certificate_sl_no'):
            if str(s['_id']) == str(student.get('_id')):
                assigned_serial = s['certificate_sl_no']
            continue
        serial = str(next_serial).zfill(4)
        next_serial += 1
        mongo.db.students.update_one(
            {"_id": s['_id']},
            {"$set": {"certificate_sl_no": serial}}
        )
        if str(s['_id']) == str(student.get('_id')):
            assigned_serial = serial

    return assigned_serial or "0001"


def reset_and_regenerate_certificate_serials():
    """Wipe every existing certificate serial and reassign a fresh, globally
    unique 0001-upward sequence across all scholarship-winning students
    (ordered by roll number). Used by the admin "reset serials" action so the
    whole set can be cleanly renumbered from 0001 on demand."""
    mongo.db.students.update_many({}, {"$unset": {"certificate_sl_no": ""}})
    group_students = list(mongo.db.students.find({
        "scholarship_grade": {"$exists": True, "$nin": [None, "", "Nothing"]}
    }).sort("roll_no", 1))
    for idx, s in enumerate(group_students, start=1):
        mongo.db.students.update_one(
            {"_id": s['_id']},
            {"$set": {"certificate_sl_no": str(idx).zfill(4)}}
        )
    return len(group_students)


def get_certificate_date_and_signature(student):
    """Return (date_string, signature_dict) for a certificate, both pulled
    dynamically from admin settings (with sensible fallbacks) so the printed
    date and the bottom-right authority signature are never hard-coded.

    Priority for both is the dedicated Certificate Settings, then the result
    settings / admit settings, then a final fallback.

    - date  : certificate-settings publication date, else the student's own
              result_publication_date, else the result-settings notice date,
              else today's date.
    - signature : {signature_image, name}. No 'title' is returned because the
              certificate background already has 'Controller of Examinations'
              pre-printed beneath the signature line."""
    cert = get_cert_settings()
    _settings, _org, notice_date, _announcement, signatories = get_result_settings()

    cert_date = (
        cert.get('publication_date')
        or student.get('result_publication_date')
        or notice_date
        or datetime.now().strftime('%d-%m-%Y')
    )

    signature = {'signature_image': '', 'name': ''}
    if cert.get('signature_image') or cert.get('signature_name'):
        signature['signature_image'] = cert.get('signature_image', '')
        signature['name'] = cert.get('signature_name', '')
    elif signatories:
        signature['signature_image'] = signatories[0].get('signature_image', '')
        signature['name'] = signatories[0].get('name', '')

    if not signature['signature_image']:
        admit = get_admit_settings()
        signature['signature_image'] = admit.get('signature_image', '')

    return cert_date, signature


@app.route('/admin/certificates', methods=['GET'])
def admin_certificates():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    search_query = request.args.get('search_query', '').strip()
    student_class = request.args.get('class', '').strip()
    center_code = request.args.get('center', '').strip()
    query = {"status": "Verified"}
    if search_query:
        query["$or"] = [
            {"roll_no": search_query},
            {"name_en": {"$regex": search_query, "$options": "i"}}
        ]
    if student_class:
        query["student_class"] = student_class
    if center_code:
        query["center_code"] = center_code
    students = list(mongo.db.students.find(query).sort("roll_no", 1))
    all_centers = mongo.db.students.distinct("center_code")
    return render_template('admin_certificates.html', students=students, all_centers=all_centers)

@app.route('/admin/print-certificate/<student_id>')
def print_certificate(student_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    try:
        student = mongo.db.students.find_one({"_id": ObjectId(student_id)})
        if not student:
            flash("দুঃখিত, এই ছাত্রের তথ্য পাওয়া যায়নি!", "danger")
            return redirect(url_for('admin_certificates'))
        c_code = str(student.get('center_code', ''))
        center_name = get_grouped_center_name_map(lang="en").get(c_code, "Brilliants Foundation Center")
        student['certificate_sl_no'] = get_or_assign_certificate_serial(student)
        cert_date, cert_signature = get_certificate_date_and_signature(student)
        return render_template('certificate_design.html', student=student,
                               center_name=center_name, cert_date=cert_date,
                               cert_signature=cert_signature,
                               field_styles=build_cert_field_styles())
    except Exception as e:
        flash(f"সার্টিফিকেট রেন্ডার করতে সমস্যা হয়েছে: {str(e)}", "danger")
        return redirect(url_for('admin_certificates'))

@app.route('/admin/print-all-certificates')
def print_all_certificates():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    search_query = request.args.get('search_query', '')
    student_class = request.args.get('class', '')
    center_code = request.args.get('center', '')
    query = {"status": "Verified"}
    if search_query:
        query["$or"] = [{"roll_no": search_query}, {"name_en": {"$regex": search_query, "$options": "i"}}]
    if student_class:
        query["student_class"] = student_class
    if center_code:
        query["center_code"] = center_code
    students = list(mongo.db.students.find(query).sort("roll_no", 1))
    if not students:
        flash("প্রিন্ট করার মতো কোনো স্টুডেন্ট খুঁজে পাওয়া যায়নি!", "warning")
        return redirect(url_for('admin_certificates'))
    for s in students:
        s['certificate_sl_no'] = get_or_assign_certificate_serial(s)
    center_names = get_grouped_center_name_map(lang='en')
    cert_date, cert_signature = get_certificate_date_and_signature(students[0])
    return render_template('bulk_certificates_design.html', students=students,
                           center_names=center_names, cert_date=cert_date,
                           cert_signature=cert_signature,
                           field_styles=build_cert_field_styles())


@app.route('/admin/certificates/reset-serials', methods=['POST'])
def reset_certificate_serials():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    count = reset_and_regenerate_certificate_serials()
    flash(f"সকল সার্টিফিকেট সিরিয়াল রিসেট করা হয়েছে। {count} জনকে নতুন করে ০০০১ থেকে ক্রমিক নম্বর দেওয়া হয়েছে।", "success")
    return redirect(url_for('admin_certificates'))

@app.route('/admin/attendance/print')
def admin_attendance_print():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    center_code = request.args.get('center', '')
    student_class = request.args.get('student_class', '')
    room = request.args.get('room', '')
    query = {"status": "Verified"}
    if center_code:
        query["center_code"] = center_code
    if student_class:
        query["student_class"] = student_class
    students = list(mongo.db.students.find(query).sort("roll_no", 1))
    return render_template('attendance_print.html',
                           students=students, center=center_code,
                           student_class=student_class, room=room, now=datetime.now())

@app.route('/admin/bulk-admit-filter')
def bulk_admit_filter():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    selected_class = request.args.get('class', '')
    selected_school = request.args.get('school', '')
    selected_center = request.args.get('center', '')
    schools = mongo.db.students.distinct('institute_en')
    centers = list(mongo.db.centers.find().sort("center_code", 1))
    classes = ["5", "6", "7", "8", "9"]
    students = []
    if selected_class or selected_school or selected_center:
        query = {"status": "Verified"}
        if selected_class:
            query["student_class"] = selected_class
        if selected_school:
            query["institute_en"] = selected_school
        if selected_center:
            query["center_code"] = center_code_filter(selected_center)
        students = list(mongo.db.students.find(query).sort("roll_no", 1))
    return render_template('admin_bulk_filter.html',
                           schools=schools, classes=classes, centers=centers, students=students,
                           selected_class=selected_class, selected_school=selected_school,
                           selected_center=selected_center)

@app.route('/admin/bulk-admit-download')
def bulk_admit_download():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    selected_class = request.args.get('class')
    selected_school = request.args.get('school')
    selected_center = request.args.get('center')
    query = {"status": "Verified"}
    if selected_class:
        query["student_class"] = {"$in": [selected_class, str(selected_class), int(selected_class) if selected_class.isdigit() else selected_class]}
    if selected_school:
        query["institute_en"] = selected_school
    if selected_center:
        query["center_code"] = center_code_filter(selected_center)
    students = list(mongo.db.students.find(query).sort("roll_no", 1))
    for s in students:
        c_code = s.get('center_code')
        if c_code:
            c_info = mongo.db.centers.find_one({"center_code": c_code})
            s['center_name'] = c_info.get('center_name_bn', c_code) if c_info else c_code
        else:
            s['center_name'] = "নির্ধারিত নয়"
    if not students:
        return "<script>alert('No students found for this selection!'); window.history.back();</script>"
    return render_template('admin_print_engine.html', students=students, admit_settings=get_admit_settings())

@app.route('/admin/export-filter')
def export_filter_page():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    schools = mongo.db.students.distinct('institute_en')
    centers = list(mongo.db.centers.find().sort("center_code", 1))
    grades = ["Talentpool", "General", "Suveccha", "Quata", "Nothing"]
    years = sorted({d.get('applied_at').year for d in mongo.db.students.find({}, {"applied_at": 1}) if d.get('applied_at')}, reverse=True)
    return render_template('export_filter.html', schools=schools, centers=centers, grades=grades, years=years)

@app.route('/admin/export-students')
def export_detailed_data():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    selected_class = request.args.get('class', '').strip()
    selected_school = request.args.get('school', '').strip()
    selected_center = request.args.get('center_code', '').strip()
    selected_grade = request.args.get('grade', '').strip()
    selected_year = request.args.get('year', '').strip()
    sort_by = request.args.get('sort_by', 'roll').strip()
    query = {}
    if selected_class:
        query['student_class'] = selected_class
    if selected_school:
        query['institute_en'] = selected_school
    if selected_center:
        query['center_code'] = center_code_filter(selected_center)
    if selected_grade:
        if selected_grade == 'Nothing':
            query['scholarship_grade'] = {"$in": [None, "Nothing", ""]}
        else:
            query['scholarship_grade'] = selected_grade
    if selected_year and selected_year.isdigit():
        year = int(selected_year)
        query['applied_at'] = {"$gte": datetime(year, 1, 1), "$lt": datetime(year + 1, 1, 1)}
    if sort_by == "year":
        sort_field = [("applied_at", 1)]
    elif sort_by == "institute_class":
        sort_field = [("institute_en", 1), ("student_class", 1), ("roll_no", 1)]
    else:
        sort_field = [("roll_no", 1)]
    try:
        students = list(mongo.db.students.find(query).sort(sort_field))
    except Exception as e:
        return f"Database Error: {str(e)}", 500
    output = io.StringIO()
    output.write(u'\ufeff')
    writer = csv.writer(output)
    headers = [
        'Roll No', 'Reg No', 'Student Name (BN)', 'Student Name (EN)',
        'Father Name', 'Mother Name', 'Institution', 'Institution Type',
        'Class', 'Exam Center', 'Address', 'Mobile',
        'Bangla (25)', 'English (25)', 'Math (25)', 'G.K (25)', 'Total Marks',
        'Scholarship Grade', 'Application Year', 'Status'
    ]
    writer.writerow(headers)
    for s in students:
        center_display = s.get('center_name') or s.get('center_code', '')
        marks = s.get('marks', {})
        if not isinstance(marks, dict):
            marks = {}
        m_bangla = marks.get('bangla')
        m_english = marks.get('english')
        m_math = marks.get('math')
        m_gk = marks.get('gk')
        sub_marks = [m_bangla, m_english, m_math, m_gk]
        valid_marks = [m for m in sub_marks if isinstance(m, (int, float))]
        total_marks = sum(valid_marks) if valid_marks else 0
        applied_at = s.get('applied_at')
        applied_year = applied_at.year if isinstance(applied_at, datetime) else ''
        address = s.get('address_present', '')
        if isinstance(address, dict):
            address = ", ".join(filter(None, [address.get('village'), address.get('upazila'), address.get('district')]))
        writer.writerow([
            s.get('roll_no', ''), s.get('reg_no', ''), s.get('name_bn', ''),
            s.get('name_en', '').upper(), s.get('father_en', '').upper(),
            s.get('mother_en', '').upper(), s.get('institute_en', ''),
            s.get('institute_type', ''), s.get('student_class', ''),
            center_display, address, s.get('mobile', ''),
            m_bangla if m_bangla is not None else '',
            m_english if m_english is not None else '',
            m_math if m_math is not None else '',
            m_gk if m_gk is not None else '',
            total_marks if valid_marks else '',
            s.get('scholarship_grade', '') or '', applied_year, s.get('status', '')
        ])
    output.seek(0)
    file_info = f"Class_{selected_class if selected_class else 'All'}"
    if selected_center:
        file_info += f"_Center_{selected_center}"
    if selected_grade:
        file_info += f"_Grade_{selected_grade}"
    filename = f"Student_Report_{file_info}.csv"
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-disposition": f"attachment; filename={filename}"})

# =====================================================================
# YEARLY ARCHIVE SYSTEM — preserves a permanent snapshot of each year's
# participants & scholarship winners so the data survives even after
# the live 'students' collection is reused for the next exam cycle.
# =====================================================================

def _archive_query(year, dataset):
    query = {"archive_year": year}
    if dataset == 'winners':
        query["scholarship_grade"] = {"$in": SCHOLARSHIP_GRADES}
    return list(mongo.db.archive_students.find(query).sort("roll_no", 1))

@app.route('/admin/archive')
def admin_archive():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    archived = list(mongo.db.archive_meta.find().sort("year", -1))
    live_years = sorted({d.get('applied_at').year for d in mongo.db.students.find({}, {"applied_at": 1}) if d.get('applied_at')}, reverse=True)
    archived_years_set = {a['year'] for a in archived}
    return render_template('admin_archive.html',
                           archived=archived, live_years=live_years,
                           archived_years_set=archived_years_set,
                           current_year=datetime.now().year)

@app.route('/admin/archive/create', methods=['POST'])
def create_archive():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    try:
        year = int(request.form.get('year'))
    except (TypeError, ValueError):
        flash("সঠিক বছর উল্লেখ করুন।", "danger")
        return redirect(url_for('admin_archive'))

    start = datetime(year, 1, 1)
    end = datetime(year + 1, 1, 1)
    students = list(mongo.db.students.find({"applied_at": {"$gte": start, "$lt": end}}))
    if not students:
        flash(f"{year} সালের জন্য বর্তমান ডাটাবেজে কোনো শিক্ষার্থীর তথ্য পাওয়া যায়নি।", "warning")
        return redirect(url_for('admin_archive'))

    # পূর্বের আর্কাইভ থাকলে রিফ্রেশ করা হবে (মুছে নতুন করে কপি)
    mongo.db.archive_students.delete_many({"archive_year": year})
    archived_at = datetime.utcnow()
    docs = []
    for s in students:
        doc = dict(s)
        doc.pop('_id', None)
        doc['archive_year'] = year
        doc['archived_at'] = archived_at
        docs.append(doc)
    if docs:
        mongo.db.archive_students.insert_many(docs)

    total_winners = sum(1 for s in students if s.get('scholarship_grade') in SCHOLARSHIP_GRADES)
    mongo.db.archive_meta.update_one(
        {"year": year},
        {"$set": {
            "year": year,
            "archived_at": archived_at,
            "total_participants": len(students),
            "total_winners": total_winners,
        }},
        upsert=True
    )
    flash(f"{year} সালের {len(students)} জন শিক্ষার্থীর তথ্য (এর মধ্যে {total_winners} জন বৃত্তিপ্রাপ্ত) সফলভাবে আর্কাইভ করা হয়েছে।", "success")
    return redirect(url_for('admin_archive'))

@app.route('/admin/archive/delete/<int:year>')
def delete_archive(year):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    mongo.db.archive_students.delete_many({"archive_year": year})
    mongo.db.archive_meta.delete_one({"year": year})
    flash(f"{year} সালের আর্কাইভ মুছে ফেলা হয়েছে।", "info")
    return redirect(url_for('admin_archive'))

@app.route('/admin/archive/print/<int:year>')
def archive_print(year):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    dataset = request.args.get('dataset', 'participants')
    students = _archive_query(year, dataset)
    meta = mongo.db.archive_meta.find_one({"year": year}) or {}
    return render_template('archive_print.html', students=students, year=year,
                           dataset=dataset, meta=meta, now=datetime.now())

@app.route('/admin/archive/download-csv/<int:year>')
def archive_download_csv(year):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    dataset = request.args.get('dataset', 'participants')
    students = _archive_query(year, dataset)

    output = io.StringIO()
    output.write(u'\ufeff')
    writer = csv.writer(output)
    writer.writerow(['ক্রম', 'রোল নং', 'রেজি নং', 'নাম (বাংলা)', 'নাম (ইংরেজি)', 'পিতার নাম', 'মাতার নাম',
                     'প্রতিষ্ঠান', 'প্রতিষ্ঠানের ধরন', 'শ্রেণি', 'পরীক্ষা কেন্দ্র', 'মোবাইল',
                     'মোট নম্বর', 'বৃত্তি গ্রেড', 'স্ট্যাটাস'])
    for idx, s in enumerate(students, 1):
        marks = s.get('marks', {})
        if not isinstance(marks, dict):
            marks = {}
        valid_marks = [m for m in [marks.get('bangla'), marks.get('english'), marks.get('math'), marks.get('gk')] if isinstance(m, (int, float))]
        total_marks = sum(valid_marks) if valid_marks else ''
        center_display = s.get('center_name') or s.get('center_code', '')
        writer.writerow([
            idx, s.get('roll_no', ''), s.get('reg_no', ''), s.get('name_bn', ''), s.get('name_en', ''),
            s.get('father_en') or s.get('father_bn', ''), s.get('mother_en') or s.get('mother_bn', ''),
            s.get('institute_en') or s.get('institute_bn', ''), s.get('institute_type', ''),
            s.get('student_class', ''), center_display, s.get('mobile', ''),
            total_marks, s.get('scholarship_grade', '') or '', s.get('status', '')
        ])
    output.seek(0)
    label = 'Scholarship_Winners' if dataset == 'winners' else 'All_Participants'
    fname = f"Archive_{year}_{label}.csv"
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-disposition": f"attachment; filename={fname}"})

@app.route('/student/download-application')
def download_application_copy():
    student_roll = session.get('student_roll')
    if not student_roll:
        flash("আপনার সেশন শেষ হয়ে গেছে। দয়া করে আবার লগইন করুন।", "warning")
        return redirect(url_for('login'))
    try:
        student = mongo.db.students.find_one({"roll_no": student_roll})
        if not student:
            return "ডাটা খুঁজে পাওয়া যায়নি!", 404
        c_code = str(student.get('center_code', ''))
        center_name = get_center_name_map(lang='en').get(c_code, "Unknown Center")
        now = datetime.now().strftime("%d %b %Y, %I:%M %p")
        return render_template('application_copy.html', student=student, center_name=center_name,
                               current_time=now, admit_settings=get_admit_settings())
    except Exception as e:
        return f"Error occurred: {str(e)}", 500

# =====================================================================
# NEW: PROSPECTURE (SCHOLARSHIP) SECTION
# =====================================================================

@app.route('/admin/prospecture')
def admin_prospecture():
    """Admin panel - Prospecture/Scholarship section: list all scholarship classes"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    # Get scholarship summary per class
    pipeline = [
        {"$match": {"scholarship_grade": {"$exists": True, "$ne": None, "$ne": "Nothing", "$ne": ""}}},
        {"$group": {
            "_id": "$student_class",
            "total": {"$sum": 1},
            "talentpool": {"$sum": {"$cond": [{"$eq": ["$scholarship_grade", "Talentpool"]}, 1, 0]}},
            "general": {"$sum": {"$cond": [{"$eq": ["$scholarship_grade", "General"]}, 1, 0]}},
            "suveccha": {"$sum": {"$cond": [{"$eq": ["$scholarship_grade", "Suveccha"]}, 1, 0]}},
            "quata": {"$sum": {"$cond": [{"$eq": ["$scholarship_grade", "Quata"]}, 1, 0]}},
        }},
        {"$sort": {"_id": 1}}
    ]
    class_summary = list(mongo.db.students.aggregate(pipeline))
    total_scholarship = mongo.db.students.count_documents({
        "scholarship_grade": {"$exists": True, "$nin": [None, "", "Nothing"]}
    })

    return render_template('admin_prospecture.html',
                           class_summary=class_summary,
                           total_scholarship=total_scholarship)


@app.route('/admin/prospecture/class/<student_class>')
def admin_prospecture_class(student_class):
    """Admin panel - view all scholarship students for a specific class"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    grade_filter = request.args.get('grade', '')
    center_filter = request.args.get('center', '')

    query = {
        "student_class": student_class,
        "scholarship_grade": {"$exists": True, "$nin": [None, "", "Nothing"]}
    }
    if grade_filter:
        query["scholarship_grade"] = grade_filter
    if center_filter:
        query["center_code"] = center_code_filter(center_filter)

    students = list(mongo.db.students.find(query).sort([("scholarship_grade", 1), ("marks.total", -1)]))
    all_centers = mongo.db.students.distinct("center_code")
    center_display_map = get_grouped_center_name_map(lang='bn')

    return render_template('admin_prospecture_class.html',
                           students=students,
                           student_class=student_class,
                           grade_filter=grade_filter,
                           center_filter=center_filter,
                           all_centers=all_centers,
                           center_display_map=center_display_map)


@app.route('/admin/prospecture/class/<student_class>/download-csv')
def download_prospecture_csv(student_class):
    """Download CSV of scholarship students for a given class"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    grade_filter = request.args.get('grade', '').strip()
    center_filter = request.args.get('center', '').strip()

    query = {"student_class": student_class, "scholarship_grade": {"$exists": True, "$ne": "Nothing"}}
    if grade_filter:
        query["scholarship_grade"] = grade_filter
    if center_filter:
        query["center_code"] = center_code_filter(center_filter)

    students = list(mongo.db.students.find(query).sort([("scholarship_grade", 1), ("marks.total", -1)]))
    center_display_map = get_grouped_center_name_map(lang='bn')

    output = io.StringIO()
    output.write(u'\ufeff')
    writer = csv.writer(output)
    writer.writerow(['#', 'Roll No', 'Reg No', 'Name (EN)', 'Name (BN)', 'Institute', 'Center',
                     'Bangla', 'English', 'Math', 'GK', 'Total', 'Scholarship Grade'])
    for idx, s in enumerate(students, 1):
        marks = s.get('marks') or {}
        center_display = center_display_map.get(str(s.get('center_code', '')), s.get('center_code', ''))
        writer.writerow([
            idx,
            s.get('roll_no', ''),
            s.get('reg_no', ''),
            s.get('name_en', ''),
            s.get('name_bn', ''),
            s.get('institute_en') or s.get('institute_bn', ''),
            center_display,
            marks.get('bangla', ''),
            marks.get('english', ''),
            marks.get('math', ''),
            marks.get('gk', ''),
            marks.get('total', ''),
            s.get('scholarship_grade', '')
        ])
    output.seek(0)
    filename = f"Prospecture_Class{student_class}"
    if grade_filter:
        filename += f"_{grade_filter}"
    filename += ".csv"
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-disposition": f"attachment; filename={filename}"})


# ---------------------------------------------------------------------
# Prospecture Photo Album — the printed-booklet style page (photo + name +
# institute + center, grouped by grade) shown in admin and downloadable as
# a PDF via the browser's print dialog, exactly like the rest of this app's
# "PDF" pages (e.g. participant_summary_print, archive_print).
# ---------------------------------------------------------------------
@app.route('/admin/prospecture/class/<student_class>/album')
def admin_prospecture_album(student_class):
    """Admin panel - photo album view (like a printed scholarship
    prospectus page) for a class, grouped by scholarship grade."""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    grade_filter = request.args.get('grade', '')
    center_filter = request.args.get('center', '')
    students, grouped = get_prospecture_students(student_class, grade_filter, center_filter)
    all_centers = mongo.db.students.distinct("center_code")
    center_display_map = get_grouped_center_name_map(lang='bn')
    return render_template('admin_prospecture_album.html',
                           student_class=student_class, grouped=grouped,
                           total=len(students), grade_filter=grade_filter,
                           center_filter=center_filter, all_centers=all_centers,
                           center_display_map=center_display_map,
                           grade_bn_labels=GRADE_BN_LABELS,
                           year=datetime.now().year)


@app.route('/admin/prospecture/class/<student_class>/album/print')
def admin_prospecture_album_print(student_class):
    """Standalone, print-ready photo album page (Download as PDF via the
    browser's print dialog — same convention used throughout this app)."""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    grade_filter = request.args.get('grade', '')
    center_filter = request.args.get('center', '')
    students, grouped = get_prospecture_students(student_class, grade_filter, center_filter)
    center_display_map = get_grouped_center_name_map(lang='bn')
    return render_template('prospecture_album_print.html',
                           student_class=student_class, grouped=grouped,
                           total=len(students), grade_filter=grade_filter,
                           center_filter=center_filter,
                           center_display_map=center_display_map,
                           grade_bn_labels=GRADE_BN_LABELS,
                           year=datetime.now().year)


# Order requested for the combined printable prospectus booklet: within each
# class, Talentpool students first, then General, then Medha Britti (the
# 'Quata' DB value), then Suveccha — repeated for classes 5 through 9.
PROSPECTUS_GRADE_ORDER = ['Talentpool', 'General', 'Quata', 'Suveccha']


@app.route('/admin/prospecture/print-all')
def admin_prospecture_print_all():
    """Combined, A5-print-ready scholarship prospectus covering classes 5-9
    in one document — within each class, students are grouped Talentpool ->
    General -> Medha Britti -> Suveccha, exactly as requested. Optional
    ?center= filter narrows it to a single exam center."""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    center_filter = request.args.get('center', '')
    center_display_map = get_grouped_center_name_map(lang='bn')

    classes_meta = [
        {'id': '5', 'name_bn': '৫ম শ্রেণি'},
        {'id': '6', 'name_bn': '৬ষ্ঠ শ্রেণি'},
        {'id': '7', 'name_bn': '৭ম শ্রেণি'},
        {'id': '8', 'name_bn': '৮ম শ্রেণি'},
        {'id': '9', 'name_bn': '৯ম শ্রেণি'},
    ]

    classes = []
    grand_total = 0
    for cls in classes_meta:
        query = {
            "student_class": {"$in": [cls['id'], int(cls['id'])]},
            "scholarship_grade": {"$exists": True, "$nin": [None, "", "Nothing"]}
        }
        if center_filter:
            query["center_code"] = center_code_filter(center_filter)
        students = list(mongo.db.students.find(query).sort([("scholarship_grade", 1), ("marks.total", -1)]))

        grouped = {}
        for g in PROSPECTUS_GRADE_ORDER:
            bucket = [s for s in students if s.get('scholarship_grade') == g]
            if bucket:
                grouped[g] = bucket

        if grouped:
            classes.append({
                'class_id': cls['id'],
                'class_name_bn': cls['name_bn'],
                'grouped': grouped,
                'total': len(students),
            })
            grand_total += len(students)

    return render_template('prospectus_print_all.html',
                           classes=classes,
                           grand_total=grand_total,
                           center_filter=center_filter,
                           center_display_map=center_display_map,
                           grade_bn_labels=GRADE_BN_LABELS,
                           prospectus_grade_labels=PROSPECTUS_GRADE_LABELS,
                           year=datetime.now().year)



@app.route('/admin/prospecture/search-result', methods=['GET', 'POST'])
def admin_prospecture_result_search():
    """Admin panel - Search student result by roll, mobile, or school name"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    students = []
    search_query = ''
    search_type = ''
    school_list = mongo.db.students.distinct('institute_en')

    if request.method == 'POST':
        search_query = request.form.get('search_query', '').strip()
        search_type = request.form.get('search_type', 'roll')

        if search_query:
            if search_type == 'school':
                # Search all students from that school
                students = list(mongo.db.students.find({
                    "institute_en": {"$regex": search_query, "$options": "i"},
                    "marks": {"$exists": True}
                }).sort([("student_class", 1), ("marks.total", -1)]))
            elif search_type == 'mobile':
                student = mongo.db.students.find_one({"mobile": search_query})
                if student:
                    students = [student]
            else:
                # roll search
                student = mongo.db.students.find_one({"roll_no": search_query})
                if student:
                    students = [student]

            if not students:
                flash("কোনো ফলাফল পাওয়া যায়নি।", "warning")
        else:
            flash("অনুগ্রহ করে একটি মান লিখুন।", "danger")

    return render_template('admin_prospecture_result_search.html',
                           students=students,
                           search_query=search_query,
                           search_type=search_type,
                           school_list=school_list)


# Public result search page (like admit search)
@app.route('/result-search', methods=['GET', 'POST'])
def public_result_search():
    """Public page - search result by roll number AND mobile number together,
    so a result can only be viewed by someone who has both pieces of
    information (matches the applicant's own submitted details)."""
    student = None
    search_done = False

    if request.method == 'POST':
        roll_query = request.form.get('roll_no', '').strip()
        mobile_query = request.form.get('mobile', '').strip()
        search_done = True

        if roll_query and mobile_query:
            # Check if result is published
            setting = mongo.db.settings.find_one({"key": "result_published"})
            is_published = setting['value'] if setting else False

            if not is_published:
                flash("ফলাফল এখনো প্রকাশিত হয়নি। অনুগ্রহ করে পরে আবার চেষ্টা করুন।", "warning")
                return render_template('public_result_search.html', student=None, search_done=True)

            # Search by roll number AND mobile number together
            student = mongo.db.students.find_one({"roll_no": roll_query, "mobile": mobile_query})
            if not student:
                flash("এই রোল ও মোবাইল নম্বরের মিল খুঁজে পাওয়া যায়নি। অনুগ্রহ করে সঠিক তথ্য দিন।", "danger")
        else:
            flash("অনুগ্রহ করে রোল নম্বর ও মোবাইল নম্বর উভয়ই লিখুন।", "danger")

    return render_template('public_result_search.html', student=student, search_done=search_done)


# Teacher/Institute-wise scholarship result search
@app.route('/result-search/institute', methods=['GET', 'POST'])
def institute_result_search():
    """Teachers can search by institute name to see all scholarshiped students,
    organized by class and grade."""
    grouped = None
    institute_name = ''
    search_done = False

    setting = mongo.db.settings.find_one({"key": "result_published"})
    is_published = setting['value'] if setting else False

    if request.method == 'POST':
        institute_name = request.form.get('institute_name', '').strip()
        search_done = True

        if not is_published:
            flash("ফলাফল এখনো প্রকাশিত হয়নি। অনুগ্রহ করে পরে আবার চেষ্টা করুন।", "warning")
        elif not institute_name:
            flash("অনুগ্রহ করে শিক্ষা প্রতিষ্ঠানের নাম লিখুন।", "danger")
        else:
            # Match either Bangla or English institute name, case-insensitive partial match
            regex = {"$regex": institute_name, "$options": "i"}
            query = {
                "$and": [
                    {"$or": [{"institute_bn": regex}, {"institute_en": regex}]},
                    {"marks": {"$exists": True}},
                    {"scholarship_grade": {"$exists": True, "$nin": ["", "Nothing", None]}}
                ]
            }
            students = list(mongo.db.students.find(query).sort([
                ("student_class", 1), ("scholarship_grade", 1), ("marks.total", -1)
            ]))

            if not students:
                flash("এই প্রতিষ্ঠানের কোনো বৃত্তিপ্রাপ্ত শিক্ষার্থী পাওয়া যায়নি।", "danger")
            else:
                # Group by class, then by grade
                grouped = {}
                for s in students:
                    cls = s.get('student_class', 'Unknown')
                    grade = s.get('scholarship_grade', 'Nothing')
                    grouped.setdefault(cls, {}).setdefault(grade, []).append(s)

    return render_template('institute_result_search.html',
                           grouped=grouped,
                           institute_name=institute_name,
                           search_done=search_done,
                           is_published=is_published)


# =====================================================================
# HOMEPAGE CONTENT (LEADERSHIP / SPEECH SECTION) MANAGEMENT
# =====================================================================

@app.route('/admin/homepage')
def admin_homepage():
    """Admin: manage homepage leadership/speech section (names, designations, speeches, photos)"""
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    leaders = list(mongo.db.leaders.find().sort("order", 1))
    return render_template('admin_homepage.html', leaders=leaders)


def _resolve_leader_photo(default_url=None):
    """Photo can come as an uploaded file (sent to ImgBB) or a direct URL"""
    photo_file = request.files.get('photo')
    photo_url_input = request.form.get('photo_url', '').strip()
    if photo_file and photo_file.filename:
        uploaded = upload_to_imgbb(photo_file)
        if uploaded:
            return uploaded
    if photo_url_input:
        return photo_url_input
    return default_url


@app.route('/admin/homepage/add', methods=['POST'])
def admin_homepage_add():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    name = request.form.get('name', '').strip()
    designation = request.form.get('designation', '').strip()
    speech = request.form.get('speech', '').strip()
    if not name or not designation:
        flash("নাম এবং পদবি অবশ্যই দিতে হবে!", "danger")
        return redirect(url_for('admin_homepage'))
    photo_url = _resolve_leader_photo(
        "https://i.postimg.cc/SsLDX6WZ/Screenshot_2026_01_20_020601_removebg_preview.png")
    last = mongo.db.leaders.find_one(sort=[("order", -1)])
    next_order = (last.get('order', 0) + 1) if last else 1
    mongo.db.leaders.insert_one({
        "name": name,
        "designation": designation,
        "speech": speech,
        "photo_url": photo_url,
        "order": next_order
    })
    flash(f"সফলভাবে '{name}' যোগ করা হয়েছে।", "success")
    return redirect(url_for('admin_homepage'))


@app.route('/admin/homepage/edit/<leader_id>', methods=['POST'])
def admin_homepage_edit(leader_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    try:
        leader = mongo.db.leaders.find_one({"_id": ObjectId(leader_id)})
        if not leader:
            flash("তথ্য খুঁজে পাওয়া যায়নি!", "danger")
            return redirect(url_for('admin_homepage'))
        photo_url = _resolve_leader_photo(leader.get('photo_url'))
        update_data = {
            "name": request.form.get('name', '').strip() or leader.get('name'),
            "designation": request.form.get('designation', '').strip() or leader.get('designation'),
            "speech": request.form.get('speech', '').strip(),
            "photo_url": photo_url
        }
        order_val = request.form.get('order', '').strip()
        if order_val.isdigit():
            update_data["order"] = int(order_val)
        mongo.db.leaders.update_one({"_id": ObjectId(leader_id)}, {"$set": update_data})
        flash("সফলভাবে আপডেট করা হয়েছে।", "success")
    except Exception as e:
        flash(f"আপডেট করতে সমস্যা হয়েছে: {str(e)}", "danger")
    return redirect(url_for('admin_homepage'))


@app.route('/admin/homepage/delete/<leader_id>')
def admin_homepage_delete(leader_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    try:
        mongo.db.leaders.delete_one({"_id": ObjectId(leader_id)})
        flash("সফলভাবে মুছে ফেলা হয়েছে।", "info")
    except Exception as e:
        flash(f"মুছে ফেলতে সমস্যা হয়েছে: {str(e)}", "danger")
    return redirect(url_for('admin_homepage'))


# --- ADMIN: DYNAMIC HOME PAGE SETTINGS ---
@app.route('/admin/home-settings', methods=['GET', 'POST'])
def admin_home_settings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        action = request.form.get('action', '')

        if action == 'add_slide':
            url = request.form.get('slide_url', '').strip()
            if url:
                mongo.db.home_settings.update_one(
                    {"key": "home"}, {"$push": {"hero_slides": url}}, upsert=True)
                flash("স্লাইড যোগ হয়েছে।", "success")

        elif action == 'remove_slide':
            url = request.form.get('slide_url', '').strip()
            if url:
                mongo.db.home_settings.update_one(
                    {"key": "home"}, {"$pull": {"hero_slides": url}})
                flash("স্লাইড মুছে ফেলা হয়েছে।", "info")

        elif action == 'add_date':
            date_entry = {
                "day": request.form.get('date_day', '').strip(),
                "month": request.form.get('date_month', '').strip(),
                "title": request.form.get('date_title', '').strip(),
                "desc": request.form.get('date_desc', '').strip(),
                "highlight": request.form.get('date_highlight') == 'on'
            }
            if date_entry['day'] and date_entry['title']:
                mongo.db.home_settings.update_one(
                    {"key": "home"}, {"$push": {"important_dates": date_entry}}, upsert=True)
                flash("তারিখ যোগ হয়েছে।", "success")

        elif action == 'remove_date':
            idx = int(request.form.get('date_index', -1))
            settings = mongo.db.home_settings.find_one({"key": "home"}) or {}
            dates = settings.get("important_dates", [])
            if 0 <= idx < len(dates):
                dates.pop(idx)
                mongo.db.home_settings.update_one(
                    {"key": "home"}, {"$set": {"important_dates": dates}})
                flash("তারিখ মুছে ফেলা হয়েছে।", "info")

        elif action == 'add_gallery':
            url = request.form.get('gallery_url', '').strip()
            if url:
                mongo.db.home_settings.update_one(
                    {"key": "home"}, {"$push": {"gallery_images": url}}, upsert=True)
                flash("গ্যালারি ছবি যোগ হয়েছে।", "success")

        elif action == 'remove_gallery':
            url = request.form.get('gallery_url', '').strip()
            if url:
                mongo.db.home_settings.update_one(
                    {"key": "home"}, {"$pull": {"gallery_images": url}})
                flash("গ্যালারি ছবি মুছে ফেলা হয়েছে।", "info")

        elif action == 'update_impact':
            mongo.db.home_settings.update_one({"key": "home"}, {"$set": {
                "impact_image": request.form.get("impact_image", "").strip(),
                "impact_title": request.form.get("impact_title", "").strip(),
                "impact_text": request.form.get("impact_text", "").strip(),
            }}, upsert=True)
            # Update stats
            s1 = {"number": request.form.get("stat1_num","").strip(), "label": request.form.get("stat1_label","").strip()}
            s2 = {"number": request.form.get("stat2_num","").strip(), "label": request.form.get("stat2_label","").strip()}
            mongo.db.home_settings.update_one({"key": "home"}, {"$set": {"stats": [s1, s2]}}, upsert=True)
            flash("ইমপ্যাক্ট সেকশন আপডেট হয়েছে।", "success")

        elif action == 'update_hero_text':
            mongo.db.home_settings.update_one({"key": "home"}, {"$set": {
                "hero_title": request.form.get("hero_title", "").strip(),
                "hero_subtitle": request.form.get("hero_subtitle", "").strip(),
            }}, upsert=True)
            flash("হিরো টেক্সট আপডেট হয়েছে।", "success")

        return redirect(url_for('admin_home_settings'))

    settings = mongo.db.home_settings.find_one({"key": "home"}) or {}
    reg_open_setting = mongo.db.settings.find_one({"key": "registration_open"})
    registration_open = reg_open_setting['value'] if reg_open_setting else True
    reg_msg_setting = mongo.db.settings.find_one({"key": "registration_closed_message"})
    registration_closed_message = reg_msg_setting['value'] if reg_msg_setting else "এই মুহূর্তে নতুন আবেদন গ্রহণ বন্ধ রয়েছে। অনুগ্রহ করে পরে আবার চেষ্টা করুন অথবা কর্তৃপক্ষের সাথে যোগাযোগ করুন।"
    return render_template('admin_home_settings.html', s=settings,
                            registration_open=registration_open,
                            registration_closed_message=registration_closed_message)


# --- ADMIN: DYNAMIC CONTACT PAGE SETTINGS ---
@app.route('/admin/contact-settings', methods=['GET', 'POST'])
def admin_contact_settings():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        data = {
            "key": "contact",
            "hero_image": request.form.get("hero_image", "").strip(),
            "office_address": request.form.get("office_address", "").strip(),
            "phone_mobile": request.form.get("phone_mobile", "").strip(),
            "phone_office": request.form.get("phone_office", "").strip(),
            "email": request.form.get("email", "").strip(),
            "facebook_url": request.form.get("facebook_url", "").strip(),
            "map_embed_url": request.form.get("map_embed_url", "").strip()
        }
        mongo.db.contact_settings.update_one({"key": "contact"}, {"$set": data}, upsert=True)
        flash("যোগাযোগ পেজ আপডেট হয়েছে।", "success")
        return redirect(url_for('admin_contact_settings'))
    settings = mongo.db.contact_settings.find_one({"key": "contact"}) or {}
    return render_template('admin_contact_settings.html', s=settings)


# --- CENTER-WISE BULK APPROVAL (from dashboard filters) ---
@app.route('/admin/bulk-update-status', methods=['POST'])
def bulk_update_status():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    center = request.form.get('center', '').strip()
    student_class = request.form.get('class', '').strip()
    action = request.form.get('action', 'Verified')
    query = {}
    if center:
        query["center_code"] = center
    if student_class:
        query["student_class"] = student_class
    if not query:
        flash("বাল্ক অ্যাপ্রুভালের জন্য অন্তত একটি সেন্টার বা শ্রেণি নির্বাচন করুন!", "warning")
        return redirect(url_for('admin_dashboard'))
    new_status = "Verified" if action == 'Verified' else "Pending"
    verification = new_status == "Verified"
    result = mongo.db.students.update_many(
        query, {"$set": {"status": new_status, "verification": verification}})
    flash(f"সফল! {result.modified_count} জন শিক্ষার্থীর স্ট্যাটাস '{new_status}' করা হয়েছে।", "success")
    return redirect(url_for('admin_dashboard', center=center, **{'class': student_class}))


# --- ADMIN LOGOUT ---
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash("You have been logged out.", "info")
    return redirect(url_for('admin_login'))

if __name__ == '__main__':
    app.run(debug=True)

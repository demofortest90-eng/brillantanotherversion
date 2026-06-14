import os
import random
import string
import datetime
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
        gallery_images=gallery_images
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

@app.route('/apply', methods=['GET', 'POST'])
def apply():
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

            existing_student = mongo.db.students.find_one({"mobile": mobile_number})
            if existing_student:
                flash("এই মোবাইল নম্বর দিয়ে ইতিমধ্যে একটি আবেদন জমা দেওয়া হয়েছে। একটি নম্বর দিয়ে শুধুমাত্র একবার রেজিস্ট্রেশন করা যাবে।", "danger")
                return redirect(request.url)

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
            center_display_name = center_info.get('center_name', 'N/A') if center_info else 'N/A'

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
    return render_template('payment_slip.html', student=student)

@app.route('/download-admit', methods=['GET', 'POST'])
def download_admit():
    if request.method == 'POST':
        query = request.form.get('search_query', '').strip()
        if not query:
            flash("অনুগ্রহ করে রোল বা মোবাইল নম্বর লিখুন।", "warning")
            return redirect(url_for('download_admit'))

        if len(query) == 11 and query.isdigit():
            student = mongo.db.students.find_one({"mobile": query})
        else:
            student = mongo.db.students.find_one({"roll_no": query})

        if student:
            if not student.get('verification', False):
                flash("আপনার রেজিস্ট্রেশন এখনো ভেরিফাই হয়নি। অনুগ্রহ করে এডমিনের সাথে যোগাযোগ করুন।", "danger")
                return redirect(url_for('download_admit'))

            center_info = mongo.db.centers.find_one({"center_code": student.get('center_code')})
            center_display_name = center_info.get('center_name_bn') if center_info else student.get('center_code')
            return render_template('admit_card.html', student=student, center_name=center_display_name)
        else:
            flash("এই রোল বা মোবাইল নম্বর দিয়ে কোনো শিক্ষার্থী পাওয়া যায়নি।", "danger")
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
    centers_mapping = {
        "1": "Sariakandi", "2": "Gabtali", "3": "Khottapara",
        "4": "Aria Bajar", "5": "Dhunat", "6": "Summit",
        "7": "Sonka", "8": "Sukhanpukur", "9": "Sonatola"
    }
    c_code = str(student.get('center_code', ''))
    center_name = centers_mapping.get(c_code, "ব্রিলিয়ান্টস ফাউন্ডেশন সেন্টার")
    return render_template('certificate_design.html', student=student, center_name=center_name)

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

    match_stage = {}
    if status_filter == 'Verified':
        match_stage["status"] = "Verified"
    elif status_filter == 'Pending':
        match_stage["status"] = {"$ne": "Verified"}

    if view_by == 'institute':
        group_field = "$institute_en"
        bn_field = "$institute_bn"
    elif view_by == 'class':
        group_field = "$student_class"
        bn_field = None
    else:
        view_by = 'center'
        group_field = "$center_code"
        bn_field = "$center_name"

    pipeline = []
    if match_stage:
        pipeline.append({"$match": match_stage})

    group_dict = {
        "_id": group_field,
        "total": {"$sum": 1},
        "verified": {"$sum": {"$cond": [{"$eq": ["$status", "Verified"]}, 1, 0]}},
        "pending": {"$sum": {"$cond": [{"$ne": ["$status", "Verified"]}, 1, 0]}},
    }
    if bn_field:
        group_dict["display_name"] = {"$first": bn_field}

    pipeline.append({"$group": group_dict})
    pipeline.append({"$sort": {"_id": 1}})

    summary = list(mongo.db.students.aggregate(pipeline))
    grand_total = sum(item.get("total", 0) for item in summary)

    return render_template('admin_participant_summary.html',
                           summary=summary,
                           view_by=view_by,
                           status_filter=status_filter,
                           grand_total=grand_total)

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
    f_roll = request.args.get('roll_no')
    f_class = request.args.get('class')
    f_inst = request.args.get('institute')
    query = {"status": "Verified"}
    if f_roll:
        query["roll_no"] = f_roll
    else:
        if f_class:
            query["student_class"] = f_class
        if f_inst:
            query["institute_en"] = f_inst
    students = []
    if f_roll or f_class:
        students = list(mongo.db.students.find(query).sort("roll_no", 1))
    return render_template('admin_marks_entry.html', students=students, institutes=institutes)

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
        if not student_ids:
            flash("দয়া করে অন্তত একজন ছাত্র সিলেক্ট করুন!", "warning")
            return redirect(url_for('approve_admits'))
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
        return redirect(url_for('approve_admits'))
    students = list(mongo.db.students.find().sort("roll_no", 1))
    return render_template('admin_approve_admits.html', students=students)

@app.route('/admin/scholarship/labels')
def scholarship_labels():
    center_query = request.args.get('center', '')
    roll_query = request.args.get('roll', '')
    school_query = request.args.get('school', '')
    class_query = request.args.get('student_class', '')
    query = {"status": "Verified"}
    if center_query:
        query["center_code"] = center_query
    if roll_query:
        query["roll_no"] = roll_query
    if class_query:
        query["student_class"] = class_query
    if school_query:
        query["institute_en"] = {"$regex": school_query, "$options": "i"}
    students_list = list(mongo.db.students.find(query).sort("roll_no", 1))
    all_centers = mongo.db.students.distinct("center_code")
    return render_template('admin_labels.html', students=students_list, all_centers=all_centers)

@app.route('/admin/centers')
def manage_centers():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    centers = list(mongo.db.centers.find().sort("center_code", 1))
    bkash_s = mongo.db.settings.find_one({"key": "bkash_number"})
    nagad_s = mongo.db.settings.find_one({"key": "nagad_number"})
    bkash_number = bkash_s['value'] if bkash_s else ''
    nagad_number = nagad_s['value'] if nagad_s else ''
    return render_template('admin_center.html', centers=centers, bkash_number=bkash_number, nagad_number=nagad_number)

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
        {"code": "1", "name": "Sariakandi"}, {"code": "2", "name": "Gabtali"},
        {"code": "3", "name": "Khottapara"}, {"code": "4", "name": "Aria Bajar"},
        {"code": "5", "name": "Dhunat"}, {"code": "6", "name": "Summit (Sherpur)"},
        {"code": "7", "name": "Sonka (Sherpur)"}, {"code": "8", "name": "Sukhanpukur"},
        {"code": "9", "name": "Sonatola"}
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

@app.route('/admin/print-result')
def print_result():
    summary_data = []
    classes = [
        {'id': '5', 'name': 'Five'}, {'id': '6', 'name': 'Six'},
        {'id': '7', 'name': 'Seven'}, {'id': '8', 'name': 'Eight'},
        {'id': '9', 'name': 'Nine'}
    ]
    target_grades = ['Talentpool', 'General', 'Suveccha', 'Quata']
    for cls in classes:
        cls_row = {'class_display': cls['name']}
        for grade in target_grades:
            students = mongo.db.students.find(
                {'student_class': {'$in': [cls['id'], int(cls['id'])]}, 'scholarship_grade': grade},
                {'roll_no': 1, '_id': 0}
            ).sort('roll_no', 1)
            rolls = [str(s['roll_no']) for s in students]
            cls_row[grade] = ", ".join(rolls)
        summary_data.append(cls_row)
    return render_template('print_result.html', summary_data=summary_data)

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
        centers_mapping = {
            "1": "Sariakandi", "2": "Gabtali", "3": "Khottapara",
            "4": "Aria Bajar", "5": "Dhunat", "6": "Summit",
            "7": "Sonka", "8": "Sukhanpukur", "9": "Sonatola"
        }
        c_code = str(student.get('center_code', ''))
        center_name = centers_mapping.get(c_code, "ব্রিলিয়ান্টস ফাউন্ডেশন সেন্টার")
        return render_template('certificate_design.html', student=student, center_name=center_name)
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
    return render_template('bulk_certificates_design.html', students=students)

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
    schools = mongo.db.students.distinct('institute_en')
    classes = ["5", "6", "7", "8", "9"]
    students = []
    if selected_class or selected_school:
        query = {"status": "Verified"}
        if selected_class:
            query["student_class"] = selected_class
        if selected_school:
            query["institute_en"] = selected_school
        students = list(mongo.db.students.find(query).sort("roll_no", 1))
    return render_template('admin_bulk_filter.html',
                           schools=schools, classes=classes, students=students,
                           selected_class=selected_class, selected_school=selected_school)

@app.route('/admin/bulk-admit-download')
def bulk_admit_download():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))
    selected_class = request.args.get('class')
    selected_school = request.args.get('school')
    query = {"status": "Verified"}
    if selected_class:
        query["student_class"] = {"$in": [selected_class, str(selected_class), int(selected_class) if selected_class.isdigit() else selected_class]}
    if selected_school:
        query["institute_en"] = selected_school
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
    return render_template('admin_print_engine.html', students=students)

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
        query['center_code'] = selected_center
    if selected_grade:
        if selected_grade == 'Nothing':
            query['scholarship_grade'] = {"$in": [None, "Nothing", ""]}
        else:
            query['scholarship_grade'] = selected_grade
    if selected_year and selected_year.isdigit():
        year = int(selected_year)
        query['applied_at'] = {"$gte": datetime(year, 1, 1), "$lt": datetime(year + 1, 1, 1)}
    sort_field = [("applied_at", 1)] if sort_by == "year" else [("roll_no", 1)]
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
        centers = {
            "1": "Sariakandi", "2": "Gabtali", "3": "Khottapara",
            "4": "Aria Bajar", "5": "Dhunat", "6": "Summit",
            "7": "Sonka", "8": "Sukhanpukur", "9": "Sonatola"
        }
        c_code = str(student.get('center_code', ''))
        center_name = centers.get(c_code, "Unknown Center")
        now = datetime.now().strftime("%d %b %Y, %I:%M %p")
        return render_template('application_copy.html', student=student, center_name=center_name, current_time=now)
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
        query["center_code"] = center_filter

    students = list(mongo.db.students.find(query).sort([("scholarship_grade", 1), ("marks.total", -1)]))
    all_centers = mongo.db.students.distinct("center_code")

    return render_template('admin_prospecture_class.html',
                           students=students,
                           student_class=student_class,
                           grade_filter=grade_filter,
                           center_filter=center_filter,
                           all_centers=all_centers)


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
        query["center_code"] = center_filter

    students = list(mongo.db.students.find(query).sort([("scholarship_grade", 1), ("marks.total", -1)]))

    output = io.StringIO()
    output.write(u'\ufeff')
    writer = csv.writer(output)
    writer.writerow(['#', 'Roll No', 'Reg No', 'Name (EN)', 'Name (BN)', 'Institute', 'Center',
                     'Bangla', 'English', 'Math', 'GK', 'Total', 'Scholarship Grade'])
    for idx, s in enumerate(students, 1):
        marks = s.get('marks') or {}
        writer.writerow([
            idx,
            s.get('roll_no', ''),
            s.get('reg_no', ''),
            s.get('name_en', ''),
            s.get('name_bn', ''),
            s.get('institute_en') or s.get('institute_bn', ''),
            s.get('center_code', ''),
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
    """Public page - search result by roll number only"""
    student = None
    search_done = False

    if request.method == 'POST':
        query = request.form.get('search_query', '').strip()
        search_done = True

        if query:
            # Check if result is published
            setting = mongo.db.settings.find_one({"key": "result_published"})
            is_published = setting['value'] if setting else False

            if not is_published:
                flash("ফলাফল এখনো প্রকাশিত হয়নি। অনুগ্রহ করে পরে আবার চেষ্টা করুন।", "warning")
                return render_template('public_result_search.html', student=None, search_done=True)

            # Search by roll number only
            student = mongo.db.students.find_one({"roll_no": query})
            if not student:
                flash("এই রোল নম্বর দিয়ে কোনো শিক্ষার্থী পাওয়া যায়নি।", "danger")
        else:
            flash("অনুগ্রহ করে রোল নম্বর লিখুন।", "danger")

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
    return render_template('admin_home_settings.html', s=settings)


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

import json
from datetime import date
from io import BytesIO
from xml.sax.saxutils import escape
import pandas as pd
from bson import ObjectId
from flask import Blueprint, Response, abort, render_template, request, redirect, url_for, flash, session, send_file
from app.extensions import db
from app.security import decrypt_text, encrypt_bytes, encrypt_json
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image as RLImage, Paragraph, SimpleDocTemplate, Spacer

files_collection = db.db.files
images_collection = db.db.images

tasks_bp = Blueprint('tasks', __name__)


def _text_to_rows(text):
    if text is None:
        return [{"line": ""}]
    if isinstance(text, str):
        lines = text.splitlines() or [""]
        return [{"line": line} for line in lines]
    if isinstance(text, list):
        return text
    return [{"line": str(text)}]


def _rows_to_text(content_rows):
    if isinstance(content_rows, dict):
        if "content" in content_rows and isinstance(content_rows["content"], str):
            return content_rows["content"]
        if "ciphertext" in content_rows and "nonce" in content_rows:
            return decrypt_text(content_rows)
        if "line" in content_rows:
            return str(content_rows.get("line", ""))
        if not content_rows:
            return ""

    if isinstance(content_rows, str):
        trimmed = content_rows.strip()
        if not trimmed:
            return ""
        try:
            parsed = json.loads(trimmed)
        except (TypeError, ValueError):
            return content_rows
        return _rows_to_text(parsed)

    if not content_rows:
        return ""
    try:
        df = pd.DataFrame(content_rows)
    except ValueError:
        return "".join(str(item) for item in content_rows)
    if "line" not in df.columns:
        return ""
    return "\n".join(df["line"].fillna("").astype(str).tolist())


def _find_image_doc(image_ref):
    try:
        return images_collection.find_one({'_id': ObjectId(str(image_ref))})
    except Exception:
        return images_collection.find_one({'filename': str(image_ref)})

@tasks_bp.route('/', methods=['GET', 'POST'])
def welcome():
    if 'user' in session:
        return redirect(url_for('tasks.view'))
    
    if request.method == 'POST':
        return redirect(url_for('auth.login'))
        
    return render_template('index.html')


@tasks_bp.route('/view', methods=['GET', 'POST'])
def view():
    user = session.get('user')
    personal_filter = {
        'user': user,
        '$or': [{'category': 'personal'}, {'category': {'$exists': False}}]
    }
    cursor = files_collection.find(personal_filter, {'date': 1, '_id': 0})
    dates = sorted({doc['date'] for doc in cursor if 'date' in doc})
    files = list(files_collection.find(
        {**personal_filter, 'date': session.get('selected_date')},
        {'file': 1, 'title': 1, '_id': 0}
    ))
    today = date.today()
    if 'selected_date' not in session:
        session['selected_date']=str(today)
    
    if request.method=='POST':
        if request.form.get('form_name')=="df":
            new_date=request.form.get('date')
            if str(new_date)!=session['selected_date']:
                session['selected_date']=str(new_date)
                return redirect(url_for('tasks.view'))
        else:
            file_from_form=request.form.get('file')
            File=files_collection.find_one({
                'user': user,
                'file': str(file_from_form),
                'date': session.get('selected_date'),
                '$or': [{'category': 'personal'}, {'category': {'$exists': False}}]
            })
            if File:
                raw_content = File.get('content', File.get('content_rows', ''))
                session['text'] = _rows_to_text(raw_content)
                session['image'] = File.get('image', [])
                session['file'] = File.get('file')
                session['date'] = File.get('date')
                session['place'] = File.get('place', '')
                return redirect(url_for('tasks.editing'))
            else:
                flash(f"File '{file_from_form}' not found in database.", "error")
                return redirect(url_for('tasks.view'))

    return render_template('main.html',dates=dates,files=files)


@tasks_bp.route('/write', methods=['GET', 'POST'])
def writing():
    image_ids = []
    if request.method == 'POST':
        text = request.form.get('text_content')
        
        image_files = request.files.getlist('image_file')
        for image_file in image_files:
            if image_file and image_file.filename:
                image_data = image_file.read()
                if image_data:
                    inserted = images_collection.insert_one({
                        'user': str(session.get('user')),
                        'filename': image_file.filename,
                        'content_type': image_file.mimetype or 'application/octet-stream',
                        'data': encrypt_bytes(image_data)
                    })
                    image_ids.append(str(inserted.inserted_id))

        filename = request.form.get('filename')
        title = request.form.get('title')
        entry_date = request.form.get('entry_date')
        place = request.form.get('place')

        if not filename:
            filename = f"entry_{date.today()}.txt"

        plain_text = text or ""
        new_rec = {
            'user': str(session.get('user')),
            'category': 'personal',
            'date': entry_date or str(session.get('selected_date')),
            'file': filename,
            'image': image_ids,
            'title': title,
            'place': place,
            'content': plain_text,
            'content_rows': encrypt_json(_text_to_rows(plain_text))
        }
        files_collection.insert_one(new_rec)
        return redirect(url_for('tasks.view'))
        
    return render_template('writing.html')

@tasks_bp.route('/editing', methods=['GET', 'POST'])
def editing():
    text = session.get('text', '')
    if request.method == 'POST':
        updated = request.form.get('text_content')
        session['text'] = updated
        updated_date = request.form.get('entry_date')
        
        old_file = session.get('file')
        old_date = session.get('date')
        
        query = {
            'user': str(session.get('user')),
            'file': old_file,
            'date': old_date,
            '$or': [{'category': 'personal'}, {'category': {'$exists': False}}]
        }
        set_values = {
            'content': updated or '',
            'content_rows': encrypt_json(_text_to_rows(updated or '')),
            'category': 'personal'
        }

        if updated_date and updated_date != old_date:
            set_values['date'] = updated_date
            session['date'] = updated_date
        
        new_place = request.form.get('place')
        if new_place != session.get('place'):
            set_values['place'] = new_place
            session['place'] = new_place

        files_collection.update_one(query, {'$set': set_values})
        active_date = session.get('date', old_date)
        
        new_image_ids = []
        new_img_files = request.files.getlist('image_file')
        for new_img_file in new_img_files:
            if new_img_file and new_img_file.filename:
                image_data = new_img_file.read()
                if image_data:
                    inserted = images_collection.insert_one({
                        'user': str(session.get('user')),
                        'filename': new_img_file.filename,
                        'content_type': new_img_file.mimetype or 'application/octet-stream',
                        'data': encrypt_bytes(image_data)
                    })
                    new_image_ids.append(str(inserted.inserted_id))

        if new_image_ids:
            files_collection.update_one(
                {
                    'user': str(session.get('user')),
                    'file': old_file,
                    'date': active_date,
                    '$or': [{'category': 'personal'}, {'category': {'$exists': False}}]
                },
                {'$push': {'image': {'$each': new_image_ids}}}
            )
            session['image'] = (session.get('image') or []) + new_image_ids
            
        return redirect(url_for('tasks.view'))
    i_n=len(session.get('image', []))
    return render_template('writing.html', text=text,i_n=i_n, images=session.get('image'))

@tasks_bp.route('/delete', methods=['POST'])
def delete():
    user = str(session.get('user'))
    file = request.form.get('file')
    file_date = request.form.get('date')
    query = {
        'user': user,
        'file': file,
        'date': file_date,
        '$or': [{'category': 'personal'}, {'category': {'$exists': False}}]
    }
    file_doc = files_collection.find_one(query)
    if file_doc:
        image_ids = []
        for image_ref in file_doc.get('image', []):
            try:
                image_ids.append(ObjectId(str(image_ref)))
            except Exception:
                continue
        if image_ids:
            images_collection.delete_many({'_id': {'$in': image_ids}})
    files_collection.delete_one(query)
    return redirect(url_for('tasks.view'))

@tasks_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    image_doc = _find_image_doc(filename)
    if not image_doc:
        abort(404)

    raw_image = image_doc.get('data', b'')
    if isinstance(raw_image, dict) and "ciphertext" in raw_image and "nonce" in raw_image:
        raw_image = decrypt_bytes(raw_image)
    return Response(
        raw_image,
        mimetype=image_doc.get('content_type', 'application/octet-stream')
    )

@tasks_bp.route('/read/<filename>', methods=['GET'])
def read_file(filename):
    user = session.get('user')
    file_data = files_collection.find_one({
        'user': user,
        'file': filename,
        '$or': [{'category': 'personal'}, {'category': {'$exists': False}}]
    })
    if file_data:
        content = _rows_to_text(file_data.get('content', file_data.get('content_rows', '')))
        return render_template('read.html', 
                               name=file_data['file'], 
                               date=file_data.get('date'), 
                               place=file_data.get('place'), 
                               images=file_data.get('image', []), 
                               content=content)
    flash(f"File '{filename}' not found.", "error")
    return redirect(url_for('tasks.view'))


@tasks_bp.route('/read/<filename>/download', methods=['GET'])
def download_file_pdf(filename):
    user = session.get('user')
    file_data = files_collection.find_one({
        'user': user,
        'file': filename,
        '$or': [{'category': 'personal'}, {'category': {'$exists': False}}]
    })
    if not file_data:
        flash(f"File '{filename}' not found.", "error")
        return redirect(url_for('tasks.view'))

    content = _rows_to_text(file_data.get('content', file_data.get('content_rows', '')))

    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.textColor = colors.HexColor("#940350")
    body_style = styles['BodyText']
    body_style.leading = 16

    safe_content = escape(content or "").replace("\n", "<br/>")

    story = [
        Paragraph("Journal Entry", title_style),
        Spacer(1, 12),
        Paragraph(f"<b>Filename:</b> {escape(str(file_data.get('file', '')))}", body_style),
        Paragraph(f"<b>Date:</b> {escape(str(file_data.get('date', '')))}", body_style),
        Paragraph(f"<b>Place:</b> {escape(str(file_data.get('place', '')))}", body_style),
        Spacer(1, 14),
        Paragraph("<b>Content:</b>", body_style),
        Paragraph(safe_content, body_style),
        Spacer(1, 16)
    ]

    image_refs = file_data.get('image', [])
    if image_refs:
        story.append(Paragraph("<b>Images:</b>", body_style))
        story.append(Spacer(1, 8))

        max_width = A4[0] - 72
        max_height = 220

        for image_ref in image_refs:
            image_doc = _find_image_doc(image_ref)
            if not image_doc or not image_doc.get('data'):
                continue

            image_data = BytesIO(image_doc['data'])
            image_reader = ImageReader(image_data)
            img_w, img_h = image_reader.getSize()
            scale = min(max_width / img_w, max_height / img_h, 1)
            pdf_image = RLImage(image_data, width=img_w * scale, height=img_h * scale)
            story.append(pdf_image)
            story.append(Spacer(1, 10))

    doc.build(story)
    pdf_buffer.seek(0)

    download_name = f"{(filename.rsplit('.', 1)[0] if '.' in filename else filename)}.pdf"
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=download_name
    )





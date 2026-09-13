from datetime import date
from io import BytesIO
import secrets
from xml.sax.saxutils import escape
from bson import ObjectId
from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, session, url_for
import pandas as pd
from app.extensions import db
from app.security import decrypt_bytes, decrypt_text, encrypt_bytes, encrypt_json
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image as RLImage, Paragraph, SimpleDocTemplate, Spacer

users_collection = db.db.user
files_collection = db.db.files
images_collection = db.db.images

connection_bp = Blueprint('connection', __name__)


def _text_to_rows(text):
    lines = (text or "").splitlines() or [""]
    df = pd.DataFrame({"line": lines})
    return df.to_dict(orient="records")


def _rows_to_text(content_rows):
    if isinstance(content_rows, dict) and "ciphertext" in content_rows and "nonce" in content_rows:
        return decrypt_text(content_rows)
    if isinstance(content_rows, str):
        return content_rows
    if not content_rows:
        return ""
    df = pd.DataFrame(content_rows)
    if "line" not in df.columns:
        return ""
    return "\n".join(df["line"].fillna("").astype(str).tolist())


def _generate_connection_code():
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    group_patterns = [(4, 4, 4), (5, 5), (3, 4, 5), (6, 6), (4, 6, 4)]
    separator = secrets.choice(["-", ":", "."])
    chosen_pattern = secrets.choice(group_patterns)
    groups = [
        "".join(secrets.choice(alphabet) for _ in range(group_size))
        for group_size in chosen_pattern
    ]
    return separator.join(groups)


def _normalize_connection_code(code):
    return "".join(ch for ch in str(code or "").upper() if ch.isalnum())


def _get_or_create_connection_code(username):
    user_doc = users_collection.find_one(
        {"username": username},
        {"connection_code": 1, "connection_code_normalized": 1}
    )
    if user_doc and user_doc.get("connection_code"):
        if not user_doc.get("connection_code_normalized"):
            users_collection.update_one(
                {"username": username},
                {"$set": {"connection_code_normalized": _normalize_connection_code(user_doc["connection_code"])}}
            )
        return user_doc["connection_code"]

    for _ in range(30):
        candidate = _generate_connection_code()
        normalized = _normalize_connection_code(candidate)
        exists = users_collection.find_one(
            {"$or": [{"connection_code": candidate}, {"connection_code_normalized": normalized}]},
            {"_id": 1}
        )
        if not exists:
            users_collection.update_one(
                {"username": username},
                {"$set": {"connection_code": candidate, "connection_code_normalized": normalized}}
            )
            return candidate
    raise RuntimeError("Could not generate a unique connection code")


def _get_connected_usernames(username):
    user_doc = users_collection.find_one(
        {"username": username},
        {"connected_users": 1, "connections": 1, "connected_accounts": 1}
    ) or {}
    raw_connections = (
        user_doc.get("connected_users")
        or user_doc.get("connections")
        or user_doc.get("connected_accounts")
        or []
    )
    if isinstance(raw_connections, str):
        raw_connections = [raw_connections]
    cleaned = []
    for name in raw_connections:
        name_str = str(name).strip()
        if name_str and name_str != username and name_str not in cleaned:
            cleaned.append(name_str)
    return cleaned


def _get_pending_connection_requests(username):
    user_doc = users_collection.find_one({"username": username}, {"connection_requests": 1}) or {}
    requests = user_doc.get("connection_requests", [])
    if isinstance(requests, str):
        requests = [requests]

    cleaned = []
    for requester in requests:
        requester_name = str(requester).strip()
        if requester_name and requester_name != username and requester_name not in cleaned:
            cleaned.append(requester_name)
    return cleaned


def _connection_key(user_a, user_b):
    ordered = sorted([str(user_a).strip(), str(user_b).strip()])
    return f"{ordered[0]}||{ordered[1]}"


def _find_image_doc(image_ref):
    try:
        return images_collection.find_one({'_id': ObjectId(str(image_ref))})
    except Exception:
        return images_collection.find_one({'filename': str(image_ref)})


@connection_bp.route('/connect-code', methods=['GET'])
def connect_code():
    username = session.get('user')
    if not username:
        flash('Please log in first.', 'warning')
        return redirect(url_for('auth.login'))

    user_doc = users_collection.find_one({"username": username}, {"_id": 1})
    if not user_doc:
        session.pop('user', None)
        flash('User session is invalid. Please log in again.', 'warning')
        return redirect(url_for('auth.login'))

    connection_code = _get_or_create_connection_code(username)
    pending_requests = _get_pending_connection_requests(username)
    return render_template(
        'connect.html',
        connection_code=connection_code,
        pending_requests=pending_requests
    )


@connection_bp.route('/connect/request', methods=['POST'])
def send_connection_request():
    username = session.get('user')
    if not username:
        flash('Please log in first.', 'warning')
        return redirect(url_for('auth.login'))

    entered_code = (request.form.get('target_code') or "").strip()
    if not entered_code:
        flash('Please enter a connection code.', 'warning')
        return redirect(url_for('connection.connect_code'))

    normalized_code = _normalize_connection_code(entered_code)
    target_user = users_collection.find_one(
        {"$or": [{"connection_code": entered_code}, {"connection_code_normalized": normalized_code}]},
        {"username": 1}
    )
    if not target_user:
        flash('Invalid connection code.', 'danger')
        return redirect(url_for('connection.connect_code'))

    target_username = target_user.get("username")
    if target_username == username:
        flash('You cannot connect to your own account.', 'warning')
        return redirect(url_for('connection.connect_code'))

    if target_username in _get_connected_usernames(username):
        flash(f'You are already connected with {target_username}.', 'info')
        return redirect(url_for('connection.connect_code'))

    users_collection.update_one(
        {"username": target_username},
        {"$addToSet": {"connection_requests": username}}
    )
    flash(f'Connection request sent to {target_username}.', 'success')
    return redirect(url_for('connection.connect_code'))


@connection_bp.route('/connect/respond', methods=['POST'])
def respond_connection_request():
    username = session.get('user')
    if not username:
        flash('Please log in first.', 'warning')
        return redirect(url_for('auth.login'))

    requester = (request.form.get('requester') or "").strip()
    decision = (request.form.get('decision') or "").strip().lower()
    if not requester or decision not in {'accept', 'reject'}:
        flash('Invalid request action.', 'danger')
        return redirect(url_for('connection.connect_code'))

    pending_requests = _get_pending_connection_requests(username)
    if requester not in pending_requests:
        flash('That connection request is no longer available.', 'warning')
        return redirect(url_for('connection.connect_code'))

    users_collection.update_one(
        {"username": username},
        {"$pull": {"connection_requests": requester}}
    )

    if decision == 'accept':
        users_collection.update_one(
            {"username": username},
            {"$addToSet": {"connected_users": requester}}
        )
        users_collection.update_one(
            {"username": requester},
            {"$addToSet": {"connected_users": username}}
        )
        flash(f'Connection request from {requester} accepted.', 'success')
    else:
        flash(f'Connection request from {requester} rejected.', 'info')

    return redirect(url_for('connection.connect_code'))


@connection_bp.route('/connections', methods=['GET'])
@connection_bp.route('/shared/messages', methods=['GET'], endpoint='shared_connections')
def connections():
    username = session.get('user')
    if not username:
        flash('Please log in first.', 'warning')
        return redirect(url_for('auth.login'))

    connected_usernames = _get_connected_usernames(username)
    connected_accounts = []
    for connected_username in connected_usernames:
        latest_file = files_collection.find_one(
            {
                'category': 'shared',
                'shared_one': _connection_key(username, connected_username)
            },
            {'title': 1, 'file': 1, 'date': 1},
            sort=[('date', -1)]
        )
        connected_accounts.append({
            'username': connected_username,
            'latest_title': (latest_file or {}).get('title') or (latest_file or {}).get('file') or 'No messages yet',
            'latest_date': (latest_file or {}).get('date')
        })

    return render_template('connection.html', connected_accounts=connected_accounts)


@connection_bp.route('/connections/<connected_username>', methods=['GET'])
@connection_bp.route('/shared/messages/<connected_username>', methods=['GET'], endpoint='shared_connection_entries')
def connection_entries(connected_username):
    username = session.get('user')
    if not username:
        flash('Please log in first.', 'warning')
        return redirect(url_for('auth.login'))

    allowed = _get_connected_usernames(username)
    if connected_username not in allowed:
        abort(403)

    connection_key = _connection_key(username, connected_username)
    shared_filter = {'category': 'shared', 'shared_one': connection_key}
    files = list(files_collection.find(
        shared_filter,
        {'file': 1, 'title': 1, 'date': 1, 'created_by': 1}
    ).sort('date', -1))

    return render_template(
        'connected_main.html',
        connected_username=connected_username,
        files=files,
        current_username=username
    )


@connection_bp.route('/connections/<connected_username>/read/<entry_id>', methods=['GET'])
@connection_bp.route('/shared/messages/<connected_username>/read/<entry_id>', methods=['GET'], endpoint='shared_read_connected_file')
def read_connected_file(connected_username, entry_id):
    username = session.get('user')
    if not username:
        flash('Please log in first.', 'warning')
        return redirect(url_for('auth.login'))

    allowed = _get_connected_usernames(username)
    if connected_username not in allowed:
        abort(403)

    connection_key = _connection_key(username, connected_username)
    try:
        file_data = files_collection.find_one({
            '_id': ObjectId(entry_id),
            'category': 'shared',
            'shared_one': connection_key
        })
    except Exception:
        file_data = None

    if file_data:
        content = _rows_to_text(file_data.get('content_rows', file_data.get('content', '')))
        return render_template(
            'read.html',
            name=file_data['file'],
            date=file_data.get('date'),
            place=file_data.get('place'),
            images=file_data.get('image', []),
            content=content,
            download_url=url_for(
                'connection.shared_download_connected_file_pdf',
                connected_username=connected_username,
                entry_id=entry_id
            )
        )
    flash("Shared entry not found.", "error")
    return redirect(url_for('connection.connection_entries', connected_username=connected_username))


@connection_bp.route('/connections/<connected_username>/read/<entry_id>/download', methods=['GET'])
@connection_bp.route(
    '/shared/messages/<connected_username>/read/<entry_id>/download',
    methods=['GET'],
    endpoint='shared_download_connected_file_pdf'
)
def download_connected_file_pdf(connected_username, entry_id):
    username = session.get('user')
    if not username:
        flash('Please log in first.', 'warning')
        return redirect(url_for('auth.login'))

    allowed = _get_connected_usernames(username)
    if connected_username not in allowed:
        abort(403)

    connection_key = _connection_key(username, connected_username)
    try:
        file_data = files_collection.find_one({
            '_id': ObjectId(entry_id),
            'category': 'shared',
            'shared_one': connection_key
        })
    except Exception:
        file_data = None

    if not file_data:
        flash("Shared entry not found.", "error")
        return redirect(url_for('connection.connection_entries', connected_username=connected_username))

    content = _rows_to_text(file_data.get('content_rows', file_data.get('content', '')))

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
        Paragraph("Shared Journal Entry", title_style),
        Spacer(1, 12),
        Paragraph(f"<b>Filename:</b> {escape(str(file_data.get('file', '')))}", body_style),
        Paragraph(f"<b>Date:</b> {escape(str(file_data.get('date', '')))}", body_style),
        Paragraph(f"<b>Place:</b> {escape(str(file_data.get('place', '')))}", body_style),
        Paragraph(f"<b>Shared With:</b> {escape(str(connected_username))}", body_style),
        Paragraph(f"<b>Created By:</b> {escape(str(file_data.get('created_by', '')))}", body_style),
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

    filename = str(file_data.get('file', 'shared_entry'))
    download_name = f"{(filename.rsplit('.', 1)[0] if '.' in filename else filename)}.pdf"
    return send_file(
        pdf_buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=download_name
    )


@connection_bp.route('/connections/<connected_username>/write', methods=['GET', 'POST'])
@connection_bp.route('/shared/messages/<connected_username>/write', methods=['GET', 'POST'], endpoint='shared_write_connected_file')
def write_connected_file(connected_username):
    username = session.get('user')
    if not username:
        flash('Please log in first.', 'warning')
        return redirect(url_for('auth.login'))

    allowed = _get_connected_usernames(username)
    if connected_username not in allowed:
        abort(403)

    if request.method == 'POST':
        text = request.form.get('text_content')
        filename = (request.form.get('filename') or "").strip()
        title = (request.form.get('title') or "").strip()
        entry_date = request.form.get('entry_date') or str(date.today())
        place = (request.form.get('place') or "").strip()
        image_ids = []

        image_files = request.files.getlist('image_file')
        for image_file in image_files:
            if image_file and image_file.filename:
                image_data = image_file.read()
                if image_data:
                    inserted = images_collection.insert_one({
                        'user': str(username),
                        'filename': image_file.filename,
                        'content_type': image_file.mimetype or 'application/octet-stream',
                        'data': encrypt_bytes(image_data)
                    })
                    image_ids.append(str(inserted.inserted_id))

        if not filename:
            filename = f"shared_entry_{date.today()}.txt"

        files_collection.insert_one({
            'category': 'shared',
            'shared_one': _connection_key(username, connected_username),
            'shared_with': sorted([username, connected_username]),
            'created_by': username,
            'date': entry_date,
            'file': filename,
            'title': title,
            'place': place,
            'image': image_ids,
            'content_rows': encrypt_json(_text_to_rows(text))
        })
        flash('Shared file posted.', 'success')
        return redirect(url_for('connection.connection_entries', connected_username=connected_username))

    return render_template('writing.html', connected_username=connected_username)

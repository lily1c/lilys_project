import os
import csv
import io
import codecs
from flask import Blueprint, jsonify, request
from playhouse.shortcuts import model_to_dict
from peewee import DoesNotExist
from app.models.user import User

users_bp = Blueprint('users', __name__)

@users_bp.route('/users', methods=['GET'])
def list_users():
    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 20, type=int), 1), 100)
    query = User.select().order_by(User.id)
    total_items = query.count()
    users = query.paginate(page, per_page)
    return jsonify({
        'kind': 'list',
        'sample': [model_to_dict(u) for u in users],
        'total_items': total_items,
        'page': page,
        'per_page': per_page
    })

@users_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        user = User.get_by_id(user_id)
        return jsonify(model_to_dict(user))
    except DoesNotExist:
        return jsonify({'error': 'User not found'}), 404

@users_bp.route('/users', methods=['POST'])
def create_user():
    data = request.get_json(force=True, silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({'error': 'Malformed JSON'}), 400
    if 'username' not in data or 'email' not in data:
        return jsonify({'error': 'Missing required fields: username and email'}), 400
    username = data['username']
    email = data['email']
    # Stricter validation
    if not isinstance(username, str) or not isinstance(email, str):
        return jsonify({'error': 'Invalid data types: username and email must be strings'}), 400
    if len(username) > 50:
        return jsonify({'error': 'Username too long (max 50)'}), 400
    if len(email) > 255:
        return jsonify({'error': 'Email too long (max 255)'}), 400
    try:
        user = User.create(username=username, email=email)
        return jsonify(model_to_dict(user)), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@users_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        user = User.get_by_id(user_id)
    except DoesNotExist:
        return jsonify({'error': 'User not found'}), 404
    data = request.get_json(force=True, silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({'error': 'Malformed JSON'}), 400
    if 'username' in data:
        if not isinstance(data['username'], str):
            return jsonify({'error': 'Invalid data type for username'}), 400
        if len(data['username']) > 50:
            return jsonify({'error': 'Username too long (max 50)'}), 400
        user.username = data['username']
    if 'email' in data:
        if not isinstance(data['email'], str):
            return jsonify({'error': 'Invalid data type for email'}), 400
        if len(data['email']) > 255:
            return jsonify({'error': 'Email too long (max 255)'}), 400
        user.email = data['email']
    try:
        user.save()
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    return jsonify(model_to_dict(user))

@users_bp.route('/users/bulk', methods=['POST'])
def bulk_load():
    # Unified Bulk Load with validation
    data = {}
    try:
        if request.is_json:
            data = request.get_json(silent=True) or {}
        else:
            data = request.form.to_dict()
    except Exception:
        pass
    filename = data.get('file')
    uploaded_file = request.files.get('file')
    try:
        count = 0
        if uploaded_file:
            import csv
            import io
            import codecs
            try:
                stream = io.StringIO(uploaded_file.stream.read().decode("UTF8"), newline=None)
            except Exception:
                uploaded_file.stream.seek(0)
                stream = codecs.iterdecode(uploaded_file.stream, 'utf-8')
            reader = csv.DictReader(stream)
            for row in reader:
                if not row.get('id') or not row.get('username') or not row.get('email'):
                    continue
                if len(row['username']) > 50 or len(row['email']) > 255:
                    continue
                User.get_or_create(id=row['id'], defaults={'username': row['username'], 'email': row['email']})
                count += 1
        elif filename:
            file_path = f"seed_data/{filename}"
            if not os.path.exists(file_path):
                file_path = filename
            with open(file_path, 'r') as f:
                import csv
                reader = csv.DictReader(f)
                for row in reader:
                    if not row.get('id') or not row.get('username') or not row.get('email'):
                        continue
                    if len(row['username']) > 50 or len(row['email']) > 255:
                        continue
                    User.get_or_create(id=row['id'], defaults={'username': row['username'], 'email': row['email']})
                    count += 1
        else:
            return jsonify({'error': 'No file or filename provided'}), 400
        from app.database import db
        db.execute_sql("SELECT setval('users_id_seq', (SELECT MAX(id) FROM users))")
        return jsonify({'status': 'ok', 'count': count}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        user = User.get_by_id(user_id)
        # Cascade delete associated URLs and Events
        from app.models.url import URL
        from app.models.event import Event
        
        Event.delete().where(Event.user_id == user_id).execute()
        URL.delete().where(URL.user_id == user_id).execute()
        
        user.delete_instance()
    except DoesNotExist:
        pass
    return '', 204
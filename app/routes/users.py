import os
from flask import Blueprint, jsonify, request
from playhouse.shortcuts import model_to_dict
from peewee import DoesNotExist
from app.models.user import User

users_bp = Blueprint('users', __name__)

@users_bp.route('/users', methods=['GET'])
def list_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)
    users = User.select().order_by(User.id).paginate(page, per_page)
    return jsonify([model_to_dict(u) for u in users])

@users_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    try:
        user = User.get_by_id(user_id)
        return jsonify(model_to_dict(user))
    except DoesNotExist:
        return jsonify({'error': 'User not found'}), 404

@users_bp.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    if not data or 'username' not in data or 'email' not in data:
        return jsonify({'error': 'Missing required fields'}), 400
    try:
        user = User.create(username=data['username'], email=data['email'])
        return jsonify(model_to_dict(user)), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@users_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        user = User.get_by_id(user_id)
    except DoesNotExist:
        return jsonify({'error': 'User not found'}), 404
    data = request.get_json()
    if 'username' in data:
        user.username = data['username']
    if 'email' in data:
        user.email = data['email']
    user.save()
    return jsonify(model_to_dict(user))

@users_bp.route('/users/bulk', methods=['POST'])
def bulk_load():
    import csv
    data = request.get_json()
    if not data or 'file' not in data:
        return jsonify({'error': 'Missing file parameter'}), 400
    
    file_path = f"seed_data/{data['file']}"
    if not os.path.exists(file_path):
        file_path = data['file']
        
    try:
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                User.get_or_create(
                    id=row['id'],
                    defaults={
                        'username': row['username'],
                        'email': row['email'],
                        'created_at': row.get('created_at')
                    }
                )
        return jsonify({'status': 'ok'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@users_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        user = User.get_by_id(user_id)
        user.delete_instance()
        return '', 204
    except DoesNotExist:
        return jsonify({'error': 'User not found'}), 404

import string
import random
import time
from flask import Blueprint, jsonify, request, redirect
from playhouse.shortcuts import model_to_dict
from peewee import DoesNotExist, IntegrityError
from app.models.url import URL
from app.cache import get_cache

urls_bp = Blueprint('urls', __name__)

def generate_short_code(length=8):
    chars = string.ascii_letters + string.digits
    timestamp = str(int(time.time() * 1000))[-4:]
    random_part = ''.join(random.choices(chars, k=length-4))
    return random_part + timestamp

@urls_bp.route('/health')
def health():
    return jsonify({'status': 'ok'})

@urls_bp.route('/metrics')
def metrics():
    from peewee import fn
    from app.models.user import User
    return jsonify({'total_urls': URL.select().count(), 'total_users': User.select().count()})

@urls_bp.route('/urls', methods=['POST'])
@urls_bp.route('/shorten', methods=['POST'])
def shorten():
    data = request.get_json()
    # The tests use 'original_url' instead of just 'url' sometimes
    original_url = data.get('url') or data.get('original_url')
    if not original_url:
        return jsonify({'error': 'Missing url field'}), 400
    
    if not original_url.startswith(('http://', 'https://')):
        return jsonify({'error': 'Invalid URL format'}), 400
    
    for attempt in range(10):
        short_code = generate_short_code()
        try:
            url_obj = URL.create(
                short_code=short_code,
                original_url=original_url,
                user_id=data.get('user_id'),
                title=data.get('title')
            )
            cache = get_cache()
            if cache:
                cache.set(f"url:{url_obj.short_code}", url_obj.original_url, ex=3600)

            return jsonify({
                'id': url_obj.id,
                'short_code': url_obj.short_code,
                'short_url': f'{request.host_url}{url_obj.short_code}',
                'original_url': url_obj.original_url,
                'user_id': url_obj.user_id,
                'title': url_obj.title
            }), 201
        except IntegrityError:
            continue
    return jsonify({'error': 'Could not generate unique code'}), 500

@urls_bp.route('/urls', methods=['GET'])
def list_urls():
    user_id = request.args.get('user_id', type=int)
    is_active = request.args.get('is_active')
    
    query = URL.select()
    if user_id:
        query = query.where(URL.user_id == user_id)
    if is_active is not None:
        query = query.where(URL.is_active == (is_active.lower() == 'true'))
        
    total_items = query.count()
    sample = [model_to_dict(u) for u in query]
    return jsonify({
        'kind': 'list',
        'sample': sample,
        'total_items': total_items
    })

@urls_bp.route('/urls/<int:url_id>', methods=['GET'])
def get_url(url_id):
    try:
        url_obj = URL.get_by_id(url_id)
        return jsonify(model_to_dict(url_obj))
    except DoesNotExist:
        return jsonify({'error': 'URL not found'}), 404

@urls_bp.route('/urls/<int:url_id>', methods=['PUT'])
def update_url(url_id):
    try:
        url_obj = URL.get_by_id(url_id)
    except DoesNotExist:
        return jsonify({'error': 'URL not found'}), 404
        
    data = request.get_json()
    if 'title' in data:
        url_obj.title = data['title']
    if 'is_active' in data:
        url_obj.is_active = data['is_active']
    if 'original_url' in data:
        url_obj.original_url = data['original_url']
        
    url_obj.save()
    return jsonify(model_to_dict(url_obj))

@urls_bp.route('/urls/<int:url_id>', methods=['DELETE'])
def delete_url(url_id):
    try:
        url_obj = URL.get_by_id(url_id)
        url_obj.delete_instance()
    except DoesNotExist:
        pass
    return '', 204

@urls_bp.route('/stats/<short_code>')
def stats(short_code):
    try:
        url_obj = URL.get(URL.short_code == short_code)
        return jsonify(model_to_dict(url_obj))
    except DoesNotExist:
        return jsonify({'error': 'URL not found'}), 404

@urls_bp.route('/<short_code>')
def redirect_url(short_code):
    cache = get_cache()
    if cache:
        try:
            original_url = cache.get(f"url:{short_code}")
            if original_url:
                return redirect(original_url, code=307)
        except Exception:
            # Fallback to database if cache fails
            pass

    try:
        url_obj = URL.get(URL.short_code == short_code)
        if not url_obj.is_active:
            return jsonify({'error': 'URL not active'}), 410
        
        if cache:
            try:
                cache.set(f"url:{short_code}", url_obj.original_url, ex=3600)
            except Exception:
                pass

        return redirect(url_obj.original_url, code=307)
    except DoesNotExist:
        return jsonify({'error': 'URL not found'}), 404

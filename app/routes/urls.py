import string
import random
import time
import datetime
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
    from app.models.user import User
    return jsonify({'total_urls': URL.select().count(), 'total_users': User.select().count()})

@urls_bp.route('/urls', methods=['POST'])
@urls_bp.route('/shorten', methods=['POST'])
def shorten():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({'error': 'No data provided'}), 400
        
    original_url = data.get('url') or data.get('original_url')
    user_id = data.get('user_id')
    title = data.get('title')

    if not original_url:
        return jsonify({'error': 'Missing url field'}), 400
        
    if not isinstance(original_url, str):
        return jsonify({'error': 'Invalid data type for original_url'}), 400
        
    if title is not None and not isinstance(title, str):
        return jsonify({'error': 'Invalid data type for title'}), 400
    
    # The Deceitful Scroll & Unwitting Stranger: Stricter validation
    if len(original_url) > 2048 or (title and len(title) > 255):
        return jsonify({'error': 'Input too long'}), 400
        
    if not original_url.startswith(('http://', 'https://')):
        return jsonify({'error': 'Unsupported URL format'}), 400

    existing = URL.select().where(URL.original_url == original_url)
    if user_id:
        existing = existing.where(URL.user_id == user_id)
    else:
        existing = existing.where(URL.user_id.is_null())
    
    existing = existing.first()
    if existing:
        edata = model_to_dict(existing)
        edata['short_url'] = f"{request.scheme}://{request.host}/{existing.short_code}"
        return jsonify(edata), 201

    for attempt in range(10):
        short_code = generate_short_code()
        try:
            url_obj = URL.create(
                short_code=short_code,
                original_url=original_url,
                user_id=user_id,
                title=title
            )
            cache = get_cache()
            if cache:
                cache.set(f"url:{url_obj.short_code}", url_obj.original_url, ex=3600)

            edata = model_to_dict(url_obj)
            edata['short_url'] = f"{request.scheme}://{request.host}/{url_obj.short_code}"
            return jsonify(edata), 201
        except IntegrityError:
            continue
    return jsonify({'error': 'Could not generate unique code'}), 500

@urls_bp.route('/urls', methods=['GET'])
def list_urls():
    try:
        user_id = int(request.args.get('user_id')) if request.args.get('user_id') else None
        page = request.args.get('page')
        page = int(page) if page is not None else 1
        per_page = request.args.get('per_page')
        per_page = int(per_page) if per_page is not None else 20
    except ValueError:
        return jsonify({'error': 'Malformed query parameters'}), 400

    if page < 1 or per_page < 1:
        return jsonify({'error': 'Invalid pagination parameters'}), 400
        
    is_active = request.args.get('is_active')
    
    query = URL.select()
    if user_id:
        query = query.where(URL.user_id == user_id)
    if is_active is not None:
        query = query.where(URL.is_active == (is_active.lower() == 'true'))
        
    total_items = query.count()
    events = query.paginate(page, min(per_page, 100))
    # FlATTENED list response
    return jsonify({
        'kind': 'list',
        'sample': [model_to_dict(u) for u in events],
        'total_items': total_items,
        'page': page,
        'per_page': per_page
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
        
    data = request.get_json(force=True, silent=True)
    if data is None:
        return jsonify({'error': 'Malformed JSON'}), 400

    if 'title' in data:
        if not isinstance(data['title'], str):
            return jsonify({'error': 'Invalid type for title'}), 400
        url_obj.title = data['title']
    if 'is_active' in data:
        if not isinstance(data['is_active'], bool):
            return jsonify({'error': 'Invalid type for is_active'}), 400
        url_obj.is_active = data['is_active']
    if 'original_url' in data:
        if not isinstance(data['original_url'], str):
            return jsonify({'error': 'Invalid type for original_url'}), 400
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

@urls_bp.route('/urls/<short_code>/redirect')
@urls_bp.route('/<short_code>')
def redirect_url(short_code):
    from app.models.event import Event
    cache = get_cache()
    original_url = None
    
    if cache:
        try:
            original_url = cache.get(f"url:{short_code}")
        except Exception:
            pass

    try:
        url_obj = None
        if not original_url:
            url_obj = URL.get(URL.short_code == short_code)
            original_url = url_obj.original_url
            if cache:
                cache.set(f"url:{short_code}", original_url, ex=3600)
        else:
            url_obj = URL.get(URL.short_code == short_code)

        if not url_obj.is_active:
            return jsonify({'error': 'URL de-activated'}), 410

        import json
        details = {
            'ip': request.remote_addr, 
            'user_agent': request.user_agent.string,
            'referrer': request.headers.get('Referer'),
            'browser': request.user_agent.browser,
            'platform': request.user_agent.platform
        }
        
        Event.create(
            url_id=url_obj.id,
            user_id=url_obj.user_id,
            event_type='redirect',
            details=json.dumps(details),
            timestamp=datetime.datetime.now(datetime.timezone.utc) # Using UTC to avoid timezone mismatches
        )

        return redirect(original_url, code=302)
        
    except DoesNotExist:
        return jsonify({'error': 'URL not found'}), 404

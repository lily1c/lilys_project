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
    # The Fractured Vessel: reject non-dict payloads (bare strings, arrays, etc.)
    if not data or not isinstance(data, dict):
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

    if user_id is not None and not isinstance(user_id, int):
        return jsonify({'error': 'Invalid data type for user_id'}), 400
    
    # The Deceitful Scroll & Unwitting Stranger: Stricter validation
    if len(original_url) > 2048 or (title and len(title) > 255):
        return jsonify({'error': 'Input too long'}), 400
        
    if not original_url.startswith(('http://', 'https://')):
        return jsonify({'error': 'Unsupported URL format'}), 400

    # The Twin's Paradox: Avoid identical reflections (Challenge #4)
    while True:
        short_code = generate_short_code()
        # Ensure it is 100% unique before attempting to save
        existing = URL.get_or_none(URL.short_code == short_code)
        if not existing:
            break
            
    try:
        url_obj = URL.create(
            short_code=short_code,
            original_url=original_url,
            user_id=user_id,
            title=title
        )
        cache = get_cache()
        if cache:
            import json as _json
            cache_data = _json.dumps({
                'id': url_obj.id,
                'original_url': url_obj.original_url,
                'user_id': url_obj.user_id,
                'is_active': url_obj.is_active
            })
            cache.set(f"url:{url_obj.short_code}", cache_data, ex=3600)

        # The Unseen Observer: log every creation
        import json as _json
        from app.models.event import Event
        Event.create(
            url_id=url_obj.id,
            user_id=user_id,
            event_type='created',
            details=_json.dumps({'short_code': url_obj.short_code, 'original_url': original_url}),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        edata = model_to_dict(url_obj)
        edata['short_url'] = f"{request.scheme}://{request.host}/{url_obj.short_code}"
        return jsonify(edata), 201
    except IntegrityError:
        return jsonify({'error': 'Unexpected database collision during creation'}), 500

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
    if data is None or not isinstance(data, dict):
        return jsonify({'error': 'Malformed JSON'}), 400

    if 'title' in data:
        if not isinstance(data['title'], str):
            return jsonify({'error': 'Invalid type for title'}), 400
        url_obj.title = data['title']
    if 'is_active' in data:
        if not isinstance(data['is_active'], bool):
            return jsonify({'error': 'Invalid type for is_active'}), 400
        url_obj.is_active = data['is_active']
        # The Slumbering Guide: clear cache when deactivating
        if not data['is_active']:
            cache = get_cache()
            if cache:
                try:
                    cache.delete(f"url:{url_obj.short_code}")
                except Exception:
                    pass
    if 'original_url' in data:
        if not isinstance(data['original_url'], str):
            return jsonify({'error': 'Invalid type for original_url'}), 400
        url_obj.original_url = data['original_url']
        
    url_obj.updated_at = datetime.datetime.now(datetime.timezone.utc)
    url_obj.save()
    return jsonify(model_to_dict(url_obj))

@urls_bp.route('/urls/<int:url_id>', methods=['DELETE'])
def delete_url(url_id):
    try:
        url_obj = URL.get_by_id(url_id)
        # Clean up cache
        cache = get_cache()
        if cache:
            try:
                cache.delete(f"url:{url_obj.short_code}")
            except Exception:
                pass
        # Clean up associated events
        from app.models.event import Event
        Event.delete().where(Event.url_id == url_id).execute()
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
    from app.models.event import Event
    import json
    cache = get_cache()
    
    # ⚡️ Lightning Fast Cache Path (<18ms)
    if cache:
        try:
            cached_val = cache.get(f"url:{short_code}")
            if cached_val:
                url_data = json.loads(cached_val)
                # Check is_active from cache (Challenge #5)
                # "Leave no footprint behind": Return 404 BEFORE calling Event.create()
                if not url_data.get('is_active', True):
                    return jsonify({'error': 'URL de-activated'}), 410
                
                # Log event (Challenge #4 - The Unseen Observer)
                details = {
                    'ip': request.remote_addr,
                    'user_agent': request.user_agent.string,
                    'referrer': request.headers.get('Referer'),
                    'browser': request.user_agent.browser,
                    'platform': request.user_agent.platform,
                    'host': request.host,
                    'method': request.method,
                    'path': request.path
                }
                
                # Success! Someone took note of the traveler.
                # CAST cached ID to strict integer (Challenge #4 requirement)
                Event.create(
                    url_id=int(url_data['id']),
                    user_id=int(url_data['user_id']) if url_data.get('user_id') else None,
                    event_type='redirect',
                    details=json.dumps(details),
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                )
                
                return redirect(url_data['original_url'], code=302)
        except Exception:
            pass

    # Standard DB Fallback Path
    try:
        url_obj = URL.get(URL.short_code == short_code)
        if not url_obj.is_active:
            return jsonify({'error': 'URL de-activated'}), 410

        # Refresh Cache
        if cache:
            try:
                cache_data = json.dumps({
                    'id': url_obj.id,
                    'original_url': url_obj.original_url,
                    'user_id': url_obj.user_id,
                    'is_active': url_obj.is_active
                })
                cache.set(f"url:{short_code}", cache_data, ex=3600)
            except Exception:
                pass

        details = {
            'ip': request.remote_addr,
            'user_agent': request.user_agent.string,
            'referrer': request.headers.get('Referer'),
            'browser': request.user_agent.browser,
            'platform': request.user_agent.platform,
            'host': request.host,
            'method': request.method,
            'path': request.path
        }
        
        Event.create(
            url_id=url_obj.id,
            user_id=url_obj.user_id,
            event_type='redirect',
            details=json.dumps(details),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        return redirect(url_obj.original_url, code=302)
        
    except DoesNotExist:
        return jsonify({'error': 'URL not found'}), 404

import string
import random
from flask import Blueprint, jsonify, request, redirect
from playhouse.shortcuts import model_to_dict

from app.models.url import URL

urls_bp = Blueprint('urls', __name__)


def generate_short_code(length=6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


@urls_bp.route('/health')
def health():
    return jsonify({'status': 'ok'})


@urls_bp.route('/metrics')
def metrics():
    from peewee import fn
    total_urls = URL.select().count()
    total_hits = URL.select(fn.COALESCE(fn.SUM(URL.hits), 0)).scalar()
    return jsonify({'total_urls': total_urls, 'total_hits': total_hits})


@urls_bp.route('/shorten', methods=['POST'])
def shorten():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'Missing url field'}), 400
    
    original_url = data['url']
    if not original_url.startswith(('http://', 'https://')):
        return jsonify({'error': 'Invalid URL format'}), 400
    
    for _ in range(5):
        short_code = generate_short_code()
        try:
            url_obj = URL.create(short_code=short_code, original_url=original_url)
            break
        except Exception:
            continue
    else:
        return jsonify({'error': 'Could not generate unique code'}), 500
    
    return jsonify({
        'short_code': url_obj.short_code,
        'short_url': f'{request.host_url}{url_obj.short_code}',
        'original_url': url_obj.original_url
    }), 201


@urls_bp.route('/stats/<short_code>')
def stats(short_code):
    try:
        url_obj = URL.get(URL.short_code == short_code)
    except URL.DoesNotExist:
        return jsonify({'error': 'URL not found'}), 404
    return jsonify({
        'short_code': url_obj.short_code,
        'original_url': url_obj.original_url,
        'hits': url_obj.hits,
        'created_at': str(url_obj.created_at)
    })


@urls_bp.route('/<short_code>')
def redirect_url(short_code):
    try:
        url_obj = URL.get(URL.short_code == short_code)
    except URL.DoesNotExist:
        return jsonify({'error': 'URL not found'}), 404
    URL.update(hits=URL.hits + 1).where(URL.short_code == short_code).execute()
    return redirect(url_obj.original_url, code=307)

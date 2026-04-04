from flask import Blueprint, jsonify, request
from playhouse.shortcuts import model_to_dict
from peewee import DoesNotExist
from app.models.event import Event

events_bp = Blueprint('events', __name__)

@events_bp.route('/events', methods=['GET'])
def list_events():
    url_id = request.args.get('url_id', type=int)
    user_id = request.args.get('user_id', type=int)
    event_type = request.args.get('event_type')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = Event.select()
    if url_id:
        query = query.where(Event.url_id == url_id)
    if user_id:
        query = query.where(Event.user_id == user_id)
    if event_type:
        query = query.where(Event.event_type == event_type)
        
    total_items = query.count()
    events = query.order_by(Event.id).paginate(page, min(per_page, 100))
    sample = [model_to_dict(e) for e in events]
    return jsonify({
        'kind': 'list',
        'sample': sample,
        'total_items': total_items,
        'page': page,
        'per_page': per_page
    })

@events_bp.route('/events/<int:event_id>', methods=['GET'])
def get_event(event_id):
    try:
        return jsonify(model_to_dict(Event.get_by_id(event_id)))
    except DoesNotExist:
        return jsonify({'error': 'Event not found'}), 404

@events_bp.route('/events', methods=['POST'])
def create_event():
    data = request.get_json()
    if not data or 'event_type' not in data:
        return jsonify({'error': 'Missing event_type'}), 400
    event = Event.create(url_id=data.get('url_id'), user_id=data.get('user_id'), event_type=data['event_type'], details=data.get('details'))
    return jsonify(model_to_dict(event)), 201

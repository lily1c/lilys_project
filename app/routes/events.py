from flask import Blueprint, jsonify, request
from playhouse.shortcuts import model_to_dict
from peewee import DoesNotExist
from app.models.event import Event

events_bp = Blueprint('events', __name__)

@events_bp.route('/events', methods=['GET'])
def list_events():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    events = Event.select().order_by(Event.id).paginate(page, min(per_page, 100))
    return jsonify([model_to_dict(e) for e in events])

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

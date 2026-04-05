from flask import Blueprint, jsonify, request
from playhouse.shortcuts import model_to_dict
from peewee import DoesNotExist
from app.models.event import Event

events_bp = Blueprint('events', __name__)

@events_bp.route('/events', methods=['GET'])
def list_events():
    try:
        url_id = int(request.args.get('url_id')) if request.args.get('url_id') else None
        user_id = int(request.args.get('user_id')) if request.args.get('user_id') else None
        page = request.args.get('page')
        page = int(page) if page is not None else 1
        per_page = request.args.get('per_page')
        per_page = int(per_page) if per_page is not None else 20
    except ValueError:
        return jsonify({'error': 'Malformed query parameters'}), 400

    if page < 1 or per_page < 1:
        return jsonify({'error': 'Invalid pagination parameters'}), 400
        
    event_type = request.args.get('event_type')
    
    query = Event.select()
    if url_id:
        query = query.where(Event.url_id == url_id)
    if user_id:
        query = query.where(Event.user_id == user_id)
    if event_type:
        query = query.where(Event.event_type == event_type)
        
    total_items = query.count()
    events = query.order_by(Event.id).paginate(page, min(per_page, 100))
    
    sample = []
    import json
    import datetime
    for e in events:
        edata = model_to_dict(e)
        if edata.get('details'):
            try:
                edata['details'] = json.loads(edata['details'])
            except Exception:
                pass
        if isinstance(edata.get('timestamp'), datetime.datetime):
            edata['timestamp'] = edata['timestamp'].isoformat()
        sample.append(edata)
        
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
        edata = model_to_dict(Event.get_by_id(event_id))
        import datetime
        import json
        if edata.get('details'):
            try:
                edata['details'] = json.loads(edata['details'])
            except Exception:
                pass
        if isinstance(edata.get('timestamp'), datetime.datetime):
            edata['timestamp'] = edata['timestamp'].isoformat()
        return jsonify(edata)
    except DoesNotExist:
        return jsonify({'error': 'Event not found'}), 404

@events_bp.route('/events', methods=['POST'])
def create_event():
    import json
    data = request.get_json(force=True, silent=True)
    # The Fractured Vessel: reject non-dict payloads
    if not data or not isinstance(data, dict):
        return jsonify({'error': 'Malformed JSON or no data provided'}), 400
    if 'event_type' not in data:
        return jsonify({'error': 'Missing required field: event_type'}), 400
    if not isinstance(data['event_type'], str):
        return jsonify({'error': 'Invalid data type for event_type'}), 400
    if len(data['event_type']) > 50:
        return jsonify({'error': 'Event type too long (max 50)'}), 400
    details = data.get('details')
    if details is not None:
        if isinstance(details, dict):
            details = json.dumps(details)
        elif isinstance(details, str):
            pass  # strings are fine
        else:
            return jsonify({'error': 'Invalid data type for details'}), 400
    url_id = data.get('url_id')
    user_id = data.get('user_id')
    if url_id is not None:
        if not isinstance(url_id, int):
            return jsonify({'error': 'url_id must be integer'}), 400
    if user_id is not None:
        if not isinstance(user_id, int):
            return jsonify({'error': 'user_id must be integer'}), 400
    # Validate timestamp if provided
    timestamp_val = data.get('timestamp')
    import datetime
    if timestamp_val is not None:
        if not isinstance(timestamp_val, str):
            return jsonify({'error': 'Invalid data type for timestamp'}), 400
    timestamp = timestamp_val or datetime.datetime.now()
    try:
        event = Event.create(
            url_id=url_id,
            user_id=user_id,
            event_type=data['event_type'],
            details=details,
            timestamp=timestamp
        )
        edata = model_to_dict(event)
        if edata.get('details'):
            try:
                edata['details'] = json.loads(edata['details'])
            except Exception:
                pass
        if isinstance(edata.get('timestamp'), datetime.datetime):
            edata['timestamp'] = edata['timestamp'].isoformat()
        return jsonify(edata), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400

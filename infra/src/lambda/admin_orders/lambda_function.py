"""Administrative order workflow. API Gateway authenticates; this handler authorizes."""
import base64
import hashlib
import json
import logging
import os
import re
import secrets
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import BotoCoreError, ClientError

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
REQUESTS = os.environ.get('REQUESTS_TABLE', '')
ORDERS = os.environ.get('CONFIRMED_ORDERS_TABLE', '')
PRODUCTS = os.environ.get('PRODUCTS_TABLE', '')
NOTIFICATIONS = os.environ.get('CUSTOMER_NOTIFICATIONS_TABLE', '')
PAYMENT_INSTRUCTIONS = os.environ.get('PAYMENT_INSTRUCTIONS', '').strip()
ALLOWED_ORIGINS = set(filter(None, (x.strip() for x in os.environ.get('ALLOWED_ORIGINS', '').split(','))))
DB = None
CLIENT = None
SER = TypeSerializer()

class ApiError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message
        super().__init__(message)

def db():
    global DB
    if DB is None:
        DB = boto3.resource('dynamodb')
    return DB

def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')

def clean(value):
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, list):
        return [clean(v) for v in value]
    return value

def wire(item):
    return {k: SER.serialize(v) for k, v in item.items()}

def text(value, label, limit=500, required=True):
    if value is None and not required:
        return ''
    if not isinstance(value, str) or (required and not value.strip()) or len(value.strip()) > limit:
        raise ApiError(400, f'{label} must be text of at most {limit} characters.' if not required else f'{label} is required and must be at most {limit} characters.')
    return value.strip()

def amount(value, label):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 100000000:
        raise ApiError(400, f'{label} must be a nonnegative whole number of cents.')
    return value

def identifier(value, label):
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError):
        raise ApiError(400, f'{label} must be a UUID.')

def claims(event):
    return (((event.get('requestContext') or {}).get('authorizer') or {}).get('jwt') or {}).get('claims') or {}

def is_admin(event):
    groups = claims(event).get('cognito:groups', '')
    if isinstance(groups, str):
        try:
            parsed = json.loads(groups)
        except ValueError:
            parsed = None
        groups = parsed if isinstance(parsed, list) else [g.strip().strip('"') for g in groups.strip('[]').split(',')]
    return isinstance(groups, (list, tuple)) and 'starchild-admin' in groups

def body(event):
    raw = event.get('body') or ''
    try:
        if event.get('isBase64Encoded'):
            raw = base64.b64decode(raw, validate=True).decode('utf-8')
        if len(raw.encode('utf-8')) > 32000:
            raise ApiError(400, 'Request is too large.')
        obj = json.loads(raw)
    except (ValueError, UnicodeError, TypeError):
        raise ApiError(400, 'Request body must be valid JSON.')
    if not isinstance(obj, dict):
        raise ApiError(400, 'Request body must be a JSON object.')
    return obj

def response(status, payload, origin):
    headers = {'content-type': 'application/json', 'cache-control': 'no-store'}
    if origin in ALLOWED_ORIGINS:
        headers.update({'access-control-allow-origin': origin, 'vary': 'Origin'})
    return {'statusCode': status, 'headers': headers, 'body': json.dumps(clean(payload))}

def get_request(request_id):
    result = db().Table(REQUESTS).get_item(Key={'submission_id': request_id}, ConsistentRead=True).get('Item')
    if not result:
        raise ApiError(404, 'Order request not found.')
    return result

def get_order(order_id):
    result = db().Table(ORDERS).get_item(Key={'pk': f'ORDER#{order_id}', 'sk': 'META'}, ConsistentRead=True).get('Item')
    if not result:
        raise ApiError(404, 'Order not found.')
    return result

def public_order(order):
    return {k: v for k, v in order.items() if k not in {'pk', 'sk', 'all_pk', 'status_pk', 'fulfillment_pk', 'index_sort'}}

def quote(request):
    items, checks = [], {}
    for old in request['items']:
        slug = old['product_slug']
        product = checks.get(slug)
        if product is None:
            product = db().Table(PRODUCTS).get_item(Key={'slug': slug}, ConsistentRead=True).get('Item')
            if not product or product.get('catalog_status') != 'ACTIVE':
                raise ApiError(409, f"Product {slug} is no longer available. Decline the request or update the catalog.")
            checks[slug] = product
        if old['color'] not in product.get('colors', []) or old['size'] not in product.get('sizes', []):
            raise ApiError(409, f"A requested variant of {slug} is no longer available.")
        price = int(product['price_cents'])
        items.append({'product_slug': slug, 'name': product['name'], 'color': old['color'], 'size': old['size'],
                      'quantity': int(old['quantity']), 'unit_price_cents': price, 'line_total_cents': price * int(old['quantity'])})
    serialized = json.dumps(clean(items), sort_keys=True, separators=(',', ':')).encode()
    return items, checks, hashlib.sha256(serialized).hexdigest()

def cursor_decode(value, scope, expected_keys=None, partition=None):
    if not value:
        return None
    try:
        if len(value) > 4096:
            raise ValueError()
        parsed = json.loads(base64.urlsafe_b64decode(value.encode()).decode())
        if parsed['scope'] != scope or not isinstance(parsed['key'], dict) or not all(isinstance(v, str) for v in parsed['key'].values()):
            raise ValueError()
        if expected_keys and set(parsed['key']) != set(expected_keys):
            raise ValueError()
        if partition and parsed['key'].get(partition[0]) != partition[1]:
            raise ValueError()
        return parsed['key']
    except (ValueError, KeyError, TypeError, UnicodeError):
        raise ApiError(400, 'Invalid pagination cursor.')

def cursor_encode(key, scope):
    if not key:
        return None
    return base64.urlsafe_b64encode(json.dumps({'scope': scope, 'key': key}, separators=(',', ':')).encode()).decode()

def query(table, index, partition, value, params, scope, descending=True):
    try:
        limit = int(params.get('limit', '25'))
    except (ValueError, TypeError):
        raise ApiError(400, 'Limit must be a number between 1 and 50.')
    if not 1 <= limit <= 50:
        raise ApiError(400, 'Limit must be a number between 1 and 50.')
    options = {'KeyConditionExpression': Key(partition).eq(value), 'Limit': limit, 'ScanIndexForward': not descending}
    if index:
        options['IndexName'] = index
    expected = {'submission_id', 'review_status', 'review_sort'} if table == REQUESTS else {'pk', 'sk', partition, 'index_sort'}
    start = cursor_decode(params.get('cursor'), scope, expected, (partition, value))
    if start:
        options['ExclusiveStartKey'] = start
    result = db().Table(table).query(**options)
    return result.get('Items', []), cursor_encode(result.get('LastEvaluatedKey'), scope)

def event_item(order_id, typ, actor, timestamp, metadata):
    event_id = str(uuid4())
    return {'pk': f'ORDER#{order_id}', 'sk': f'EVENT#{timestamp}#{event_id}', 'event_id': event_id,
            'order_id': order_id, 'event_type': typ, 'created_at': timestamp, 'actor': actor, 'metadata': metadata}

def transact(actions):
    global CLIENT
    if CLIENT is None:
        CLIENT = boto3.client('dynamodb')
    CLIENT.transact_write_items(TransactItems=actions)

def put_action(table, item, condition=None):
    action = {'TableName': table, 'Item': wire(item)}
    if condition:
        action['ConditionExpression'] = condition
    return {'Put': action}

def notification_action(notification_id, kind, snapshot, timestamp):
    return put_action(NOTIFICATIONS, {'notification_id': notification_id, 'kind': kind, 'status': 'PENDING',
                                    'created_at': timestamp, 'snapshot': snapshot}, 'attribute_not_exists(notification_id)')

def confirm(request_id, payload, actor):
    request = get_request(request_id)
    if request.get('order_id'):
        return public_order(get_order(request['order_id']))
    if request.get('review_status', 'PENDING') != 'PENDING':
        raise ApiError(409, 'This request is no longer pending.')
    if not PAYMENT_INSTRUCTIONS:
        raise ApiError(503, 'Payment instructions are not configured. Contact the store administrator.')
    if payload.get('availabilityConfirmed') is not True:
        raise ApiError(400, 'Confirm availability before creating the order.')
    items, products, digest = quote(request)
    if payload.get('quoteToken') != digest:
        raise ApiError(409, 'Catalog pricing changed. Reload and review the request again.')
    method = payload.get('fulfillmentMethod')
    if method not in ('SHIPPING', 'PICKUP'):
        raise ApiError(400, 'Choose shipping or pickup.')
    instructions = text(payload.get('pickupInstructions'), 'Pickup instructions', 500, method == 'PICKUP')
    if method == 'SHIPPING':
        customer = request.get('customer', {})
        if not all(customer.get(k) for k in ('address', 'city', 'state', 'postal_code', 'country')):
            raise ApiError(400, 'A complete shipping address is required.')
    subtotal = sum(x['line_total_cents'] for x in items)
    discount = amount(payload.get('discountCents', 0), 'Discount')
    shipping = amount(payload.get('shippingCents', 0 if method == 'PICKUP' else int(request['shipping_cents'])), 'Shipping')
    tax = amount(payload.get('taxCents', 0), 'Tax')
    if discount > subtotal:
        raise ApiError(400, 'Discount cannot exceed the subtotal.')
    if method == 'PICKUP' and shipping:
        raise ApiError(400, 'Shipping must be zero for pickup.')
    reason = text(payload.get('adjustmentReason'), 'Adjustment explanation', 500, bool(discount or tax or shipping != (0 if method == 'PICKUP' else int(request['shipping_cents']))))
    timestamp, order_id = now(), str(uuid4())
    number = f"SC-{timestamp[:10].replace('-', '')}-{secrets.token_hex(4).upper()}"
    order = {'pk': f'ORDER#{order_id}', 'sk': 'META', 'order_id': order_id, 'order_number': number,
             'request_id': request_id, 'request_reference': request.get('order_reference', ''), 'created_at': timestamp,
             'updated_at': timestamp, 'customer': request['customer'], 'items': items, 'subtotal_cents': subtotal,
             'discount_cents': discount, 'shipping_cents': shipping, 'tax_cents': tax,
             'total_cents': subtotal - discount + shipping + tax, 'currency': 'USD', 'adjustment_reason': reason,
             'order_status': 'CONFIRMED', 'payment_status': 'UNPAID', 'fulfillment_status': 'UNFULFILLED',
             'fulfillment_method': method, 'pickup_instructions': instructions, 'manual_availability_confirmed': True,
             'payment': None, 'provider_reference': None, 'refund_follow_up': False, 'version': 1,
             'all_pk': 'ORDERS', 'status_pk': 'CONFIRMED', 'fulfillment_pk': 'OPEN', 'index_sort': f'{timestamp}#{order_id}'}
    actions = [put_action(ORDERS, order, 'attribute_not_exists(pk)'),
               put_action(ORDERS, {'pk': f'NUMBER#{number}', 'sk': 'RESERVED', 'order_id': order_id}, 'attribute_not_exists(pk)'),
               put_action(ORDERS, event_item(order_id, 'ORDER_CONFIRMED', actor, timestamp, {'request_id': request_id, 'adjustment_reason': reason}), 'attribute_not_exists(pk)'),
               {'Update': {'TableName': REQUESTS, 'Key': wire({'submission_id': request_id}),
                           'UpdateExpression': 'SET review_status = :converted, order_id = :order, reviewed_at = :at, reviewed_by = :actor',
                           'ConditionExpression': 'attribute_exists(submission_id) AND attribute_not_exists(order_id) AND (attribute_not_exists(review_status) OR review_status = :pending)',
                           'ExpressionAttributeValues': wire({':converted': 'CONVERTED', ':order': order_id, ':at': timestamp, ':actor': actor, ':pending': 'PENDING'})}}]
    actions.append(notification_action(f'ORDER#{order_id}#CONFIRMED', 'ORDER_CONFIRMED', {**order, 'payment_instructions': PAYMENT_INSTRUCTIONS}, timestamp))
    for slug, product in products.items():
        # Compare every field used to create the snapshot or validate the selected variant.
        actions.append({'ConditionCheck': {'TableName': PRODUCTS, 'Key': wire({'slug': slug}),
                       'ConditionExpression': 'catalog_status = :active AND #n = :name AND price_cents = :price AND colors = :colors AND sizes = :sizes',
                       'ExpressionAttributeNames': {'#n': 'name'},
                       'ExpressionAttributeValues': wire({':active': 'ACTIVE', ':name': product['name'], ':price': product['price_cents'], ':colors': product['colors'], ':sizes': product['sizes']})}})
    try:
        transact(actions)
    except ClientError as exc:
        if exc.response.get('Error', {}).get('Code') == 'TransactionCanceledException':
            fresh = get_request(request_id)
            if fresh.get('order_id'):
                return public_order(get_order(fresh['order_id']))
            raise ApiError(409, 'The request or catalog changed. Reload and review it again.')
        raise
    return public_order(order)

def decline(request_id, payload, actor):
    reason = text(payload.get('reason'), 'Decline reason')
    timestamp = now()
    request = get_request(request_id)
    updated = {**request, 'review_status': 'DECLINED', 'reviewed_at': timestamp, 'reviewed_by': actor, 'decline_reason': reason}
    try:
        transact([
            {'Update': {'TableName': REQUESTS, 'Key': wire({'submission_id': request_id}),
                        'UpdateExpression': 'SET review_status = :declined, reviewed_at = :at, reviewed_by = :actor, decline_reason = :reason',
                        'ConditionExpression': 'attribute_exists(submission_id) AND attribute_not_exists(order_id) AND (attribute_not_exists(review_status) OR review_status = :pending)',
                        'ExpressionAttributeValues': wire({':declined': 'DECLINED', ':at': timestamp, ':actor': actor, ':reason': reason, ':pending': 'PENDING'})}},
            notification_action(f'REQUEST#{request_id}#DECLINED', 'REQUEST_DECLINED', updated, timestamp),
        ])
        return updated
    except ClientError as exc:
        if exc.response.get('Error', {}).get('Code') == 'TransactionCanceledException':
            get_request(request_id)
            raise ApiError(409, 'This request is no longer pending.')
        raise

def action(order_id, payload, actor):
    operation = identifier(payload.get('operationId'), 'operationId')
    expected = payload.get('version')
    if isinstance(expected, bool) or not isinstance(expected, int) or expected < 1:
        raise ApiError(400, 'A valid order version is required.')
    pk = f'ORDER#{order_id}'
    op_key = {'pk': pk, 'sk': f'OP#{operation}'}
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    prior = db().Table(ORDERS).get_item(Key=op_key, ConsistentRead=True).get('Item')
    if prior:
        if prior['fingerprint'] != fingerprint:
            raise ApiError(409, 'Operation ID was already used for another action.')
        return public_order(get_order(order_id))
    order = get_order(order_id)
    if int(order['version']) != expected:
        raise ApiError(409, 'This order changed. Reload it before trying again.')
    kind = payload.get('action')
    if order['order_status'] in ('COMPLETED', 'CANCELED'):
        raise ApiError(409, 'This order is closed.')
    timestamp = now()
    previous = {'order_status': order['order_status'], 'payment_status': order['payment_status'], 'fulfillment_status': order['fulfillment_status']}
    if kind == 'START_PROCESSING' and order['order_status'] == 'CONFIRMED':
        order.update(order_status='PROCESSING', fulfillment_status='PROCESSING', status_pk='PROCESSING')
    elif kind in ('RECORD_PAYMENT', 'PICKED_UP_AND_PAY'):
        if order['payment_status'] != 'UNPAID':
            raise ApiError(409, 'Payment has already been recorded.')
        if kind == 'PICKED_UP_AND_PAY' and not (order['fulfillment_method'] == 'PICKUP' and order['fulfillment_status'] == 'READY_FOR_PICKUP'):
            raise ApiError(409, 'This order is not ready for pickup.')
        payment_method = text(payload.get('paymentMethod'), 'Payment method', 80)
        reference = text(payload.get('paymentReference'), 'Payment reference', 160, False)
        order.update(payment_status='PAID', payment={'amount_cents': order['total_cents'], 'method': payment_method,
                     'reference': reference, 'recorded_at': timestamp, 'recorded_by': actor})
        if kind == 'PICKED_UP_AND_PAY':
            order.update(fulfillment_status='PICKED_UP', order_status='COMPLETED', status_pk='COMPLETED')
            order.pop('fulfillment_pk', None)
    elif kind == 'SHIP' and order['fulfillment_method'] == 'SHIPPING' and order['fulfillment_status'] == 'PROCESSING':
        if order['payment_status'] != 'PAID':
            raise ApiError(409, 'Record payment before shipping.')
        order['shipment'] = {'carrier': text(payload.get('carrier'), 'Carrier', 100),
                             'tracking': text(payload.get('tracking'), 'Tracking number', 160, False), 'shipped_at': timestamp}
        order['fulfillment_status'] = 'SHIPPED'
    elif kind == 'DELIVER' and order['fulfillment_status'] == 'SHIPPED':
        order.update(fulfillment_status='DELIVERED', order_status='COMPLETED', status_pk='COMPLETED')
        order.pop('fulfillment_pk', None)
    elif kind == 'READY_FOR_PICKUP' and order['fulfillment_method'] == 'PICKUP' and order['fulfillment_status'] == 'PROCESSING':
        order['fulfillment_status'] = 'READY_FOR_PICKUP'
    elif kind == 'PICK_UP' and order['fulfillment_method'] == 'PICKUP' and order['fulfillment_status'] == 'READY_FOR_PICKUP':
        if order['payment_status'] != 'PAID':
            raise ApiError(409, 'Record payment before completing pickup.')
        order.update(fulfillment_status='PICKED_UP', order_status='COMPLETED', status_pk='COMPLETED')
        order.pop('fulfillment_pk', None)
    elif kind == 'CANCEL' and order['fulfillment_status'] not in ('SHIPPED', 'DELIVERED', 'PICKED_UP'):
        order.update(order_status='CANCELED', status_pk='CANCELED', cancel_reason=text(payload.get('reason'), 'Cancellation reason'),
                     refund_follow_up=order['payment_status'] == 'PAID')
        order.pop('fulfillment_pk', None)
    else:
        raise ApiError(409, 'This action is not valid for the current order state.')
    order.update(updated_at=timestamp, version=expected + 1)
    event = event_item(order_id, kind, actor, timestamp, {'before': previous,
        'after': {'order_status': order['order_status'], 'payment_status': order['payment_status'], 'fulfillment_status': order['fulfillment_status']},
        'payment': order.get('payment') if kind in ('RECORD_PAYMENT', 'PICKED_UP_AND_PAY') else None,
        'shipment': order.get('shipment') if kind == 'SHIP' else None,
        'reason': order.get('cancel_reason') if kind == 'CANCEL' else None})
    write = {'TableName': ORDERS, 'Item': wire(order), 'ConditionExpression': '#version = :expected',
             'ExpressionAttributeNames': {'#version': 'version'}, 'ExpressionAttributeValues': wire({':expected': expected})}
    try:
        actions = [{'Put': write}, put_action(ORDERS, event, 'attribute_not_exists(pk)'),
                   put_action(ORDERS, {**op_key, 'fingerprint': fingerprint, 'created_at': timestamp}, 'attribute_not_exists(pk)')]
        if kind in ('RECORD_PAYMENT', 'SHIP', 'DELIVER', 'READY_FOR_PICKUP', 'PICK_UP', 'PICKED_UP_AND_PAY', 'CANCEL'):
            actions.append(notification_action(f'ORDER#{order_id}#OP#{operation}', kind, order, timestamp))
        transact(actions)
    except ClientError as exc:
        if exc.response.get('Error', {}).get('Code') == 'TransactionCanceledException':
            prior = db().Table(ORDERS).get_item(Key=op_key, ConsistentRead=True).get('Item')
            if prior and prior['fingerprint'] == fingerprint:
                return public_order(get_order(order_id))
            raise ApiError(409, 'This order changed. Reload it before trying again.')
        raise
    return public_order(order)

def lambda_handler(event, _context):
    origin = (event.get('headers') or {}).get('origin') or (event.get('headers') or {}).get('Origin')
    if origin and origin not in ALLOWED_ORIGINS:
        return response(403, {'message': 'This origin is not allowed.'}, origin)
    if not is_admin(event):
        return response(403, {'message': 'Administrator access is required.'}, origin)
    actor = claims(event).get('sub')
    if not actor:
        return response(403, {'message': 'Administrator identity is required.'}, origin)
    route = event.get('routeKey', '')
    params = event.get('queryStringParameters') or {}
    path = event.get('pathParameters') or {}
    try:
        if route == 'GET /admin/order-requests':
            state = params.get('status', 'PENDING')
            if state not in ('PENDING', 'CONVERTED', 'DECLINED'):
                raise ApiError(400, 'Invalid request status.')
            items, cursor = query(REQUESTS, 'review', 'review_status', state, params, f'requests:{state}')
            return response(200, {'requests': items, 'nextCursor': cursor}, origin)
        if route == 'GET /admin/order-requests/{id}':
            req = get_request(identifier(path.get('id'), 'Request ID'))
            try:
                items, _, digest = quote(req)
                preview = {'items': items, 'quoteToken': digest, 'subtotal_cents': sum(x['line_total_cents'] for x in items)}
                return response(200, {'request': req, 'preview': preview}, origin)
            except ApiError as exc:
                if exc.status != 409:
                    raise
                return response(200, {'request': req, 'preview': None, 'previewError': exc.message}, origin)
        if route == 'POST /admin/order-requests/{id}/confirm':
            order = confirm(identifier(path.get('id'), 'Request ID'), body(event), actor)
            return response(200, {'order': order}, origin)
        if route == 'POST /admin/order-requests/{id}/decline':
            req = decline(identifier(path.get('id'), 'Request ID'), body(event), actor)
            return response(200, {'request': req}, origin)
        if route == 'GET /admin/orders':
            status = params.get('status')
            queue = params.get('fulfillment')
            if status and queue:
                raise ApiError(400, 'Choose a status or the fulfillment queue.')
            if status:
                if status not in ('CONFIRMED', 'PROCESSING', 'COMPLETED', 'CANCELED'):
                    raise ApiError(400, 'Invalid order status.')
                index, partition, value = 'by-status', 'status_pk', status
            elif queue:
                if queue != 'open':
                    raise ApiError(400, 'Invalid fulfillment filter.')
                index, partition, value = 'by-fulfillment', 'fulfillment_pk', 'OPEN'
            else:
                index, partition, value = 'all-orders', 'all_pk', 'ORDERS'
            items, cursor = query(ORDERS, index, partition, value, params, f'orders:{index}:{value}')
            return response(200, {'orders': [public_order(x) for x in items], 'nextCursor': cursor}, origin)
        if route == 'GET /admin/orders/{id}':
            return response(200, {'order': public_order(get_order(identifier(path.get('id'), 'Order ID')))}, origin)
        if route == 'GET /admin/orders/{id}/events':
            order_id = identifier(path.get('id'), 'Order ID')
            get_order(order_id)
            # Query only the EVENT prefix, not metadata and idempotency records.
            scope = f'events:{order_id}'
            try:
                limit = int(params.get('limit', '25'))
            except (TypeError, ValueError):
                raise ApiError(400, 'Invalid limit.')
            if not 1 <= limit <= 50:
                raise ApiError(400, 'Invalid limit.')
            options = {'KeyConditionExpression': Key('pk').eq(f'ORDER#{order_id}') & Key('sk').begins_with('EVENT#'), 'Limit': limit, 'ScanIndexForward': False}
            start = cursor_decode(params.get('cursor'), scope, {'pk', 'sk'}, ('pk', f'ORDER#{order_id}'))
            if start:
                options['ExclusiveStartKey'] = start
            result = db().Table(ORDERS).query(**options)
            return response(200, {'events': [public_order(x) for x in result.get('Items', [])], 'nextCursor': cursor_encode(result.get('LastEvaluatedKey'), scope)}, origin)
        if route == 'POST /admin/orders/{id}/actions':
            order = action(identifier(path.get('id'), 'Order ID'), body(event), actor)
            return response(200, {'order': order}, origin)
        raise ApiError(404, 'Route not found.')
    except ApiError as exc:
        return response(exc.status, {'message': exc.message}, origin)
    except (ClientError, BotoCoreError):
        LOG.exception('Order administration operation failed: route=%s', route)
        return response(503, {'message': 'The order service is temporarily unavailable.'}, origin)

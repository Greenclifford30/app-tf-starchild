"""Stripe checkout, webhook reconciliation, and authorization monitoring."""
import base64
import hashlib
import json
import logging
import os
import secrets
from datetime import datetime, timezone, timedelta
from uuid import UUID

import boto3
from boto3.dynamodb.conditions import Key
from boto3.dynamodb.types import TypeSerializer
from botocore.exceptions import ClientError

import order_validation as validation
from starchild_stripe import client, plain

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
REQUESTS = os.environ.get('REQUESTS_TABLE', '')
ORDERS = os.environ.get('CONFIRMED_ORDERS_TABLE', '')
NOTIFICATIONS = os.environ.get('CUSTOMER_NOTIFICATIONS_TABLE', '')
TAX_CODE = os.environ.get('STRIPE_APPAREL_TAX_CODE', '')
ORIGINS = set(filter(None, os.environ.get('ALLOWED_ORIGINS', '').split(',')))
ALERT_TOPIC = os.environ.get('PAYMENT_ALERT_TOPIC_ARN', '')
DB = boto3.resource('dynamodb')
DYNAMO = boto3.client('dynamodb')
SER = TypeSerializer()

class BadRequest(Exception):
    pass

def now():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')

def wire(value):
    return {k: SER.serialize(v) for k, v in value.items()}

def response(status, payload, origin=None):
    headers = {'content-type': 'application/json', 'cache-control': 'no-store'}
    if origin in ORIGINS:
        headers.update({'access-control-allow-origin': origin, 'vary': 'Origin'})
    return {'statusCode': status, 'headers': headers, 'body': json.dumps(payload)}

def parse_body(event):
    raw = event.get('body') or ''
    if event.get('isBase64Encoded'):
        raw = base64.b64decode(raw, validate=True).decode('utf-8')
    if len(raw.encode()) > 32000:
        raise BadRequest('Request is too large.')
    result = json.loads(raw)
    if not isinstance(result, dict):
        raise BadRequest('Expected a JSON object.')
    return result

def attempt_id(value):
    try:
        return str(UUID(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise BadRequest('A valid checkout attempt ID is required.') from exc

def create_session(payload, origin):
    if not TAX_CODE or not origin or origin not in ORIGINS:
        raise BadRequest('Checkout is not configured for this address.')
    attempt = attempt_id(payload.get('attemptId'))
    raw_items = payload.get('items')
    fingerprint = hashlib.sha256(json.dumps(raw_items, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    table = DB.Table(REQUESTS)
    saved = table.get_item(Key={'submission_id': attempt}, ConsistentRead=True).get('Item')
    if saved:
        if saved.get('checkout_fingerprint') != fingerprint or saved.get('checkout_origin') != origin:
            raise BadRequest('This checkout attempt cannot be reused for a different bag.')
        if saved.get('checkout_status') not in ('CREATING', 'OPEN'):
            raise BadRequest('This checkout attempt is no longer open.')
        if saved['checkout_status'] == 'OPEN':
            stripe, _ = client()
            session = plain(stripe.checkout.Session.retrieve(saved['checkout_session_id']))
            if session.get('status') != 'open' or not session.get('client_secret'):
                raise BadRequest('This checkout is no longer open. Check your order status before starting again.')
            return {'clientSecret': session['client_secret'], 'attemptId': attempt}
        items = saved['items']
    else:
        items = validation._validate_items({'items': raw_items})
        subtotal = sum(int(item['line_total_cents']) for item in items)
        if subtotal <= 0:
            raise BadRequest('The order total must be greater than zero.')
        timestamp = now()
        saved = {'submission_id': attempt, 'order_reference': f"SC-{timestamp[:10].replace('-', '')}-{secrets.token_hex(4).upper()}",
                 'created_at': timestamp, 'checkout_fingerprint': fingerprint, 'checkout_origin': origin, 'checkout_status': 'CREATING',
                 'payment_provider': 'stripe', 'items': items, 'subtotal_cents': subtotal,
                 'shipping_cents': 0 if subtotal >= 10000 else 800, 'currency': 'USD'}
        try:
            table.put_item(Item=saved, ConditionExpression='attribute_not_exists(submission_id)')
        except ClientError as exc:
            if exc.response['Error']['Code'] != 'ConditionalCheckFailedException':
                raise
            return create_session(payload, origin)
    stripe, _ = client()
    line_items = [{'price_data': {'currency': 'usd', 'unit_amount': int(item['unit_price_cents']),
                   'tax_behavior': 'exclusive', 'product_data': {'name': item['name'],
                   'description': f"{item['color']} / {item['size']}", 'tax_code': TAX_CODE}},
                   'quantity': int(item['quantity'])} for item in items]
    session = plain(stripe.checkout.Session.create(
        mode='payment', ui_mode='form', line_items=line_items,
        automatic_tax={'enabled': True}, shipping_address_collection={'allowed_countries': ['US', 'CA']},
        phone_number_collection={'enabled': True},
        shipping_options=[{'shipping_rate_data': {'type': 'fixed_amount', 'fixed_amount': {'amount': int(saved['shipping_cents']), 'currency': 'usd'},
                           'display_name': 'Standard shipping', 'tax_behavior': 'exclusive'}}],
        payment_intent_data={'capture_method': 'manual', 'metadata': {'starchild_attempt_id': attempt}},
        metadata={'starchild_attempt_id': attempt}, return_url=f'{origin}/checkout?session_id={{CHECKOUT_SESSION_ID}}',
        idempotency_key=f'checkout-v2-{attempt}'))
    table.update_item(Key={'submission_id': attempt},
        UpdateExpression='SET checkout_status = :open, checkout_session_id = :session',
        ConditionExpression='checkout_status = :creating OR (checkout_status = :open AND checkout_session_id = :session)',
        ExpressionAttributeValues={':creating': 'CREATING', ':open': 'OPEN', ':session': session['id']})
    return {'clientSecret': session['client_secret'], 'attemptId': attempt}

def status(attempt, session_id):
    item = DB.Table(REQUESTS).get_item(Key={'submission_id': attempt_id(attempt)}, ConsistentRead=True).get('Item')
    if not item or item.get('payment_provider') != 'stripe' or not session_id or item.get('checkout_session_id') != session_id:
        raise BadRequest('Checkout was not found.')
    state = item.get('checkout_status', 'CREATING')
    if item.get('review_status') == 'DECLINED' or item.get('payment_status') == 'FAILED':
        state = 'CANCELED'
    if item.get('order_id'):
        order = DB.Table(ORDERS).get_item(Key={'pk': f"ORDER#{item['order_id']}", 'sk': 'META'}, ConsistentRead=True).get('Item') or {}
        if order.get('payment_status') == 'PAID':
            state = 'PAID'
        elif order.get('payment_status') in ('FAILED', 'REFUNDED', 'REFUND_FAILED', 'PARTIALLY_REFUNDED'):
            state = 'UPDATED'
    return {'status': state, 'orderReference': item.get('order_reference') if state in ('AUTHORIZED', 'PAID') else None}

def notification(notification_id, kind, snapshot, timestamp):
    item = {'notification_id': notification_id, 'kind': kind, 'status': 'PENDING', 'created_at': timestamp, 'snapshot': snapshot}
    return {'Put': {'TableName': NOTIFICATIONS, 'Item': wire(item), 'ConditionExpression': 'attribute_not_exists(notification_id)'}}

def authorize(session_id):
    stripe, _ = client()
    session = plain(stripe.checkout.Session.retrieve(session_id, expand=['payment_intent.latest_charge']))
    identifier = (session.get('metadata') or {}).get('starchild_attempt_id')
    if not identifier:
        return  # Stripe account events can include unrelated Checkout Sessions.
    attempt = attempt_id(identifier)
    table = DB.Table(REQUESTS)
    saved = table.get_item(Key={'submission_id': attempt}, ConsistentRead=True).get('Item')
    if not saved or saved.get('checkout_session_id') not in (None, session_id):
        raise ValueError('Unknown checkout session')
    if saved.get('checkout_status') == 'AUTHORIZED' or saved.get('review_status') in ('CONVERTED', 'DECLINED'):
        return
    intent = session.get('payment_intent') or {}
    if not isinstance(intent, dict) or intent.get('status') != 'requires_capture' or (intent.get('metadata') or {}).get('starchild_attempt_id') != attempt:
        raise ValueError('Session has not been authorized')
    subtotal = int(saved['subtotal_cents'])
    shipping = int(saved['shipping_cents'])
    tax = int((session.get('total_details') or {}).get('amount_tax') or 0)
    total = int(session.get('amount_total') or 0)
    if session.get('currency') != 'usd' or int(session.get('amount_subtotal') or 0) != subtotal or total != subtotal + shipping + tax or int(intent.get('amount_capturable') or 0) != total:
        raise ValueError('Checkout amount does not match order snapshot')
    if (session.get('automatic_tax') or {}).get('status') != 'complete':
        raise ValueError('Stripe Tax calculation is incomplete')
    customer = session.get('customer_details') or {}
    shipping_details = (session.get('collected_information') or {}).get('shipping_details') or session.get('shipping_details') or {}
    address = shipping_details.get('address') or {}
    name = (shipping_details.get('name') or customer.get('name') or '').strip().split(maxsplit=1)
    if not name or not customer.get('email') or not all(address.get(k) for k in ('line1', 'city', 'postal_code', 'country')):
        raise ValueError('Checkout is missing contact or delivery details')
    charge = intent.get('latest_charge') or {}
    capture_before = ((charge.get('payment_method_details') or {}).get('card') or {}).get('capture_before')
    if not capture_before:
        raise ValueError('Stripe did not provide an authorization expiry')
    timestamp = now()
    updated = {**saved, 'checkout_status': 'AUTHORIZED', 'review_status': 'PENDING', 'review_sort': f"{saved['created_at']}#{attempt}",
               'checkout_session_id': session_id, 'payment_intent_id': intent['id'], 'payment_status': 'AUTHORIZED',
               'capture_before': int(capture_before), 'tax_cents': tax, 'total_cents': total,
               'customer': {'first_name': name[0], 'last_name': name[1] if len(name) > 1 else '', 'email': customer['email'],
                   'phone': customer.get('phone') or '', 'address': address['line1'], 'address_line_2': address.get('line2') or '',
                   'city': address['city'], 'state': address.get('state') or '', 'postal_code': address['postal_code'],
                   'country': address['country'], 'notes': ''}}
    actions = [{'Put': {'TableName': REQUESTS, 'Item': wire(updated), 'ConditionExpression': 'checkout_status IN (:open, :creating)',
                        'ExpressionAttributeValues': wire({':open': 'OPEN', ':creating': 'CREATING'})}},
               notification(f'REQUEST#{attempt}#AUTHORIZED', 'STRIPE_AUTHORIZED', updated, timestamp),
               notification(f'REQUEST#{attempt}#OPERATOR', 'OPERATOR_AUTHORIZED', updated, timestamp)]
    try:
        DYNAMO.transact_write_items(TransactItems=actions)
    except ClientError as exc:
        fresh = table.get_item(Key={'submission_id': attempt}, ConsistentRead=True).get('Item') or {}
        if fresh.get('checkout_status') == 'AUTHORIZED' or fresh.get('review_status') in ('CONVERTED', 'DECLINED'):
            return
        raise exc

def reconcile_intent(intent_id, ignore_unlinked=False):
    stripe, _ = client()
    intent = plain(stripe.PaymentIntent.retrieve(intent_id, expand=['latest_charge']))
    identifier = (intent.get('metadata') or {}).get('starchild_attempt_id')
    if not identifier:
        return  # Ignore payments that do not belong to this storefront.
    attempt = attempt_id(identifier)
    req = DB.Table(REQUESTS).get_item(Key={'submission_id': attempt}, ConsistentRead=True).get('Item') or {}
    if req.get('payment_intent_id') != intent_id:
        # Failed attempts before checkout completes are normal and may be retried by the customer.
        if ignore_unlinked and req.get('checkout_status') in ('CREATING', 'OPEN', 'EXPIRED'):
            return
        # Session completion may arrive after the PaymentIntent event. Stripe will retry.
        raise ValueError('Authorization has not been recorded yet')
    order_id = req.get('order_id')
    if not order_id:
        if intent.get('status') == 'canceled' and req.get('review_status') == 'PENDING' and req.get('payment_status') == 'AUTHORIZED':
            DB.Table(REQUESTS).update_item(Key={'submission_id': attempt}, UpdateExpression='SET payment_status = :failed',
                ConditionExpression='review_status = :pending AND payment_status = :authorized',
                ExpressionAttributeValues={':failed': 'FAILED', ':pending': 'PENDING', ':authorized': 'AUTHORIZED'})
        return
    table = DB.Table(ORDERS)
    order = table.get_item(Key={'pk': f'ORDER#{order_id}', 'sk': 'META'}, ConsistentRead=True).get('Item')
    if not order or order.get('payment_intent_id') != intent_id:
        raise ValueError('Linked order is unavailable')
    if intent.get('status') == 'succeeded':
        if int(intent.get('amount_received') or 0) != int(order['total_cents']):
            raise ValueError('Captured amount does not match the order')
        next_status = 'PAID'
    elif intent.get('status') in ('canceled', 'requires_payment_method'):
        next_status = 'FAILED'
    else:
        return
    if order.get('payment_status') == next_status or order.get('payment_status') in ('REFUNDED', 'PARTIALLY_REFUNDED', 'REFUND_PENDING', 'REFUND_FAILED'):
        return
    if next_status == 'FAILED' and order.get('payment_status') == 'PAID':
        return
    timestamp = now()
    version = int(order['version'])
    updated = {**order, 'payment_status': next_status, 'updated_at': timestamp, 'version': version + 1}
    if next_status == 'PAID':
        updated['payment'] = {'amount_cents': int(order['total_cents']), 'method': 'Stripe', 'reference': intent_id, 'recorded_at': timestamp, 'recorded_by': 'stripe'}
    if next_status == 'REFUNDED':
        updated['refund_follow_up'] = False
    event_id = f'STRIPE_{next_status}'
    event = {'pk': f'ORDER#{order_id}', 'sk': f'EVENT#{timestamp}#{event_id}', 'event_id': event_id, 'order_id': order_id,
             'event_type': event_id, 'created_at': timestamp, 'actor': 'stripe', 'metadata': {'payment_intent_id': intent_id}}
    actions = [{'Put': {'TableName': ORDERS, 'Item': wire(updated), 'ConditionExpression': '#version = :version',
                        'ExpressionAttributeNames': {'#version': 'version'}, 'ExpressionAttributeValues': wire({':version': version})}},
               {'Put': {'TableName': ORDERS, 'Item': wire(event), 'ConditionExpression': 'attribute_not_exists(pk)'}}]
    if next_status in ('PAID', 'REFUNDED'):
        actions.append(notification(f'ORDER#{order_id}#{event_id}', event_id, updated, timestamp))
    DYNAMO.transact_write_items(TransactItems=actions)

def reconcile_refund(refund_id):
    stripe, _ = client()
    refund = plain(stripe.Refund.retrieve(refund_id))
    intent_id = refund.get('payment_intent')
    if not intent_id:
        return
    intent = plain(stripe.PaymentIntent.retrieve(intent_id))
    identifier = (intent.get('metadata') or {}).get('starchild_attempt_id')
    if not identifier:
        return  # Ignore payments that do not belong to this storefront.
    attempt = attempt_id(identifier)
    req = DB.Table(REQUESTS).get_item(Key={'submission_id': attempt}, ConsistentRead=True).get('Item') or {}
    if req.get('payment_intent_id') != intent_id or not req.get('order_id'):
        raise ValueError('Refund has no linked order')
    order_id = req['order_id']
    table = DB.Table(ORDERS)
    order = table.get_item(Key={'pk': f'ORDER#{order_id}', 'sk': 'META'}, ConsistentRead=True).get('Item') or {}
    if order.get('payment_intent_id') != intent_id:
        raise ValueError('Refund payment does not match order')
    state = refund.get('status')
    if state == 'succeeded':
        next_status = 'REFUNDED' if int(refund['amount']) == int(order['total_cents']) else 'PARTIALLY_REFUNDED'
    elif state in ('failed', 'canceled'):
        next_status = 'REFUND_FAILED'
    else:
        return
    if order.get('payment_status') == next_status and order.get('refund_id') == refund_id:
        return
    timestamp = now()
    updated = {**order, 'payment_status': next_status, 'refund_id': refund_id,
               'refund_follow_up': next_status != 'REFUNDED', 'updated_at': timestamp, 'version': int(order['version']) + 1}
    event = {'pk': f'ORDER#{order_id}', 'sk': f'EVENT#{timestamp}#REFUND', 'event_id': refund_id,
             'order_id': order_id, 'event_type': f'STRIPE_{next_status}', 'created_at': timestamp,
             'actor': 'stripe', 'metadata': {'refund_id': refund_id, 'status': state}}
    actions = [{'Put': {'TableName': ORDERS, 'Item': wire(updated), 'ConditionExpression': '#version = :version',
                        'ExpressionAttributeNames': {'#version': 'version'}, 'ExpressionAttributeValues': wire({':version': int(order['version'])})}},
               {'Put': {'TableName': ORDERS, 'Item': wire(event), 'ConditionExpression': 'attribute_not_exists(pk)'}}]
    if next_status == 'REFUNDED':
        actions.append(notification(f'ORDER#{order_id}#REFUND#{refund_id}', 'STRIPE_REFUNDED', updated, timestamp))
    elif next_status == 'REFUND_FAILED':
        actions.append(notification(f'ORDER#{order_id}#REFUND_FAILED#{refund_id}', 'OPERATOR_REFUND_FAILED', updated, timestamp))
    DYNAMO.transact_write_items(TransactItems=actions)

def webhook(event):
    stripe, webhook_secret = client()
    raw = event.get('body') or ''
    if event.get('isBase64Encoded'):
        raw = base64.b64decode(raw, validate=True)
    signature = (event.get('headers') or {}).get('stripe-signature', '')
    parsed = plain(stripe.Webhook.construct_event(raw, signature, webhook_secret))
    typ = parsed['type']
    obj = parsed['data']['object']
    if typ == 'checkout.session.completed':
        authorize(obj['id'])
    elif typ in ('payment_intent.succeeded', 'payment_intent.canceled', 'payment_intent.payment_failed'):
        reconcile_intent(obj['id'], ignore_unlinked=typ != 'payment_intent.succeeded')
    elif typ in ('refund.updated', 'refund.created', 'refund.failed'):
        reconcile_refund(obj['id'])
    elif typ == 'checkout.session.expired':
        identifier = (obj.get('metadata') or {}).get('starchild_attempt_id')
        if not identifier:
            return {'received': True}
        attempt = attempt_id(identifier)
        try:
            DB.Table(REQUESTS).update_item(Key={'submission_id': attempt}, UpdateExpression='SET checkout_status = :expired',
                ConditionExpression='checkout_status = :open', ExpressionAttributeValues={':expired': 'EXPIRED', ':open': 'OPEN'})
        except ClientError as exc:
            if exc.response['Error']['Code'] != 'ConditionalCheckFailedException':
                raise
    return {'received': True}

def monitor():
    deadline = int((datetime.now(timezone.utc) + timedelta(hours=24)).timestamp())
    overdue = datetime.now(timezone.utc) - timedelta(hours=48)
    issues = 0
    for table_name, index, key_name, key_value, identity in [
        (REQUESTS, 'review', 'review_status', 'PENDING', 'submission_id'),
        (ORDERS, 'all-orders', 'all_pk', 'ORDERS', 'order_id')]:
        table = DB.Table(table_name)
        args = {'IndexName': index, 'KeyConditionExpression': Key(key_name).eq(key_value)}
        while True:
            result = table.query(**args)
            for item in result.get('Items', []):
                identifier = item.get(identity)
                if not identifier:
                    continue
                key = {'submission_id': identifier} if table_name == REQUESTS else {'pk': f'ORDER#{identifier}', 'sk': 'META'}
                full = table.get_item(Key=key, ConsistentRead=True).get('Item') or {}
                if full.get('payment_provider') != 'stripe' or full.get('payment_status') not in ('AUTHORIZED', 'PENDING'):
                    continue
                expires = int(full.get('capture_before') or 0)
                created = datetime.fromisoformat(full['created_at'])
                if expires <= deadline or created <= overdue:
                    issues += 1
                if expires <= int(datetime.now(timezone.utc).timestamp()) and full.get('payment_intent_id'):
                    reconcile_intent(full['payment_intent_id'])
            if 'LastEvaluatedKey' not in result:
                break
            args['ExclusiveStartKey'] = result['LastEvaluatedKey']
    if issues and ALERT_TOPIC:
        boto3.client('sns').publish(TopicArn=ALERT_TOPIC, Subject='Starchild payment holds need review', Message=f'{issues} payment hold(s) have waited 48 hours or expire within 24 hours. Review the requests and pending captures in the admin.')
    return {'needsReview': issues}

def lambda_handler(event, _context):
    if event.get('source') == 'aws.events':
        return monitor()
    headers = event.get('headers') or {}
    origin = headers.get('origin') or headers.get('Origin')
    route = event.get('routeKey', '')
    try:
        if route == 'POST /stripe/webhook':
            try:
                return response(200, webhook(event))
            except client()[0].error.SignatureVerificationError:
                return response(400, {'message': 'Invalid webhook signature.'})
        if origin not in ORIGINS:
            return response(403, {'message': 'Origin not allowed.'})
        if route == 'POST /checkout/sessions':
            return response(200, create_session(parse_body(event), origin), origin)
        if route == 'GET /checkout/sessions/{id}':
            return response(200, status((event.get('pathParameters') or {}).get('id'), (event.get('queryStringParameters') or {}).get('session_id')), origin)
        return response(404, {'message': 'Not found.'}, origin)
    except (BadRequest, validation.RequestError, ValueError, TypeError, json.JSONDecodeError) as exc:
        if route == 'POST /stripe/webhook':
            LOG.exception('Stripe event could not be reconciled')
            return response(500, {'message': 'Event could not be reconciled.'})
        return response(400, {'message': str(exc)}, origin)
    except Exception:
        LOG.exception('Payment service failed: %s', route)
        return response(503, {'message': 'Payment service is temporarily unavailable. Please retry.'}, origin)

"""Send durable customer notification jobs from the DynamoDB outbox stream."""
import logging
import os
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.types import TypeDeserializer

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)
TABLE = os.environ['CUSTOMER_NOTIFICATIONS_TABLE']
SENDER = os.environ.get('NOTIFICATION_FROM', 'Starchild <orders@starchildclo.com>')
OPERATOR = os.environ.get('NOTIFICATION_EMAIL', '')
DB = boto3.resource('dynamodb')
SES = boto3.client('ses')
DESERIALIZER = TypeDeserializer()


def money(cents):
    return f"${int(cents) / 100:.2f}"


def message(job):
    order = job['snapshot']
    kind = job['kind']
    reference = order.get('order_number') or order['order_reference']
    lines = [f"Hello {order['customer']['first_name']},", '']
    if kind in ('STRIPE_AUTHORIZED', 'OPERATOR_AUTHORIZED'):
        title = 'Payment authorized, awaiting review'
        lines += ['The checkout is awaiting an availability review. A temporary payment hold was placed; no payment has been captured.', '', 'Items:']
        lines += [f"- {i['quantity']} x {i['name']} / {i['color']} / {i['size']} ({money(i['line_total_cents'])})" for i in order['items']]
        lines += ['', f"Subtotal: {money(order['subtotal_cents'])}", f"Shipping: {money(order['shipping_cents'])}", f"Tax: {money(order['tax_cents'])}", f"Authorized total: {money(order['total_cents'])}"]
        if kind == 'OPERATOR_AUTHORIZED':
            lines += ['', 'Review availability and capture the hold in the admin.']
    elif kind == 'OPERATOR_REFUND_FAILED':
        title = 'Refund failed'
        lines += ['A Stripe refund failed. Review the order in Stripe and arrange another way to refund the customer.']
    elif kind == 'STRIPE_PAID':
        title = 'Your order is confirmed'
        lines += [f"Your order is confirmed and payment of {money(order['total_cents'])} has been captured."]
    elif kind == 'STRIPE_REFUNDED':
        title = 'Your payment was refunded'
        lines += [f"Your payment of {money(order['total_cents'])} has been refunded."]
    elif kind == 'REQUEST_RECEIVED':
        title = 'Order request received'
        lines += ['We received your order request and will review availability. No payment has been collected.', '', 'Requested items:']
        lines += [f"- {i['quantity']} x {i['name']} / {i['color']} / {i['size']} ({money(i['line_total_cents'])})" for i in order['items']]
        lines += ['', f"Estimated subtotal: {money(order['subtotal_cents'])}", f"Estimated shipping: {money(order['shipping_cents'])}", f"Estimated total: {money(order['total_cents'])}", 'We will contact you after review.']
    elif kind == 'REQUEST_DECLINED':
        title = 'Order request update'
        lines += ['We are unable to confirm your request.', f"Reason: {order['decline_reason']}"]
        if order.get('payment_provider') == 'stripe':
            lines += ['Your payment authorization has been canceled.']
    elif kind == 'ORDER_CONFIRMED':
        title = 'Your order is confirmed'
        lines += ['Your order is confirmed. Payment has not yet been recorded.', '', 'Items:']
        lines += [f"- {i['quantity']} x {i['name']} / {i['color']} / {i['size']} ({money(i['line_total_cents'])})" for i in order['items']]
        lines += ['', f"Subtotal: {money(order['subtotal_cents'])}", f"Discount: {money(order['discount_cents'])}", f"Shipping: {money(order['shipping_cents'])}", f"Tax: {money(order['tax_cents'])}", f"Total: {money(order['total_cents'])}", '', 'Payment instructions:', order['payment_instructions']]
        if order['fulfillment_method'] == 'PICKUP':
            lines += ['', f"Pickup instructions: {order['pickup_instructions']}"]
    elif kind == 'RECORD_PAYMENT':
        title = 'Payment recorded'
        lines += [f"We recorded your payment of {money(order['total_cents'])}."]
    elif kind == 'SHIP':
        title = 'Your order has shipped'
        shipment = order['shipment']
        lines += [f"Your order has shipped with {shipment['carrier']}."]
        if shipment.get('tracking'):
            lines += [f"Tracking number: {shipment['tracking']}"]
    elif kind == 'DELIVER':
        title = 'Your order was marked delivered'
        lines += ['Your order has been marked delivered.']
    elif kind == 'READY_FOR_PICKUP':
        title = 'Your order is ready for pickup'
        lines += ['Your order is ready for pickup.', f"Pickup instructions: {order['pickup_instructions']}"]
    elif kind in ('PICK_UP', 'PICKED_UP_AND_PAY'):
        title = 'Your order was picked up'
        lines += ['Your order has been marked picked up.']
        if kind == 'PICKED_UP_AND_PAY':
            lines += [f"We recorded your payment of {money(order['total_cents'])}."]
    elif kind == 'CANCEL':
        title = 'Your order was canceled'
        lines += ['Your order has been canceled.', f"Reason: {order['cancel_reason']}"]
        if order.get('refund_follow_up'):
            lines += ['Our team will follow up with you about your payment and any refund.']
    else:
        raise ValueError('Unknown notification kind')
    lines += ['', f'Reference: {reference}', '', 'Starchild']
    return f'{title} — {reference}', '\n'.join(lines)


def process(notification_id):
    table = DB.Table(TABLE)
    job = table.get_item(Key={'notification_id': notification_id}, ConsistentRead=True).get('Item')
    if not job or job.get('status') == 'SENT':
        return
    try:
        subject, body = message(job)
        result = SES.send_email(Source=SENDER, Destination={'ToAddresses': [OPERATOR if job['kind'].startswith('OPERATOR_') else job['snapshot']['customer']['email']]},
                                Message={'Subject': {'Data': subject, 'Charset': 'UTF-8'}, 'Body': {'Text': {'Data': body, 'Charset': 'UTF-8'}}})
        table.update_item(Key={'notification_id': notification_id}, UpdateExpression='SET #s = :sent, message_id = :id, updated_at = :at REMOVE last_error',
                          ExpressionAttributeNames={'#s': 'status'}, ExpressionAttributeValues={':sent': 'SENT', ':id': result['MessageId'], ':at': datetime.now(timezone.utc).isoformat()})
    except Exception as exc:
        LOG.exception('Customer notification failed: %s', notification_id)
        table.update_item(Key={'notification_id': notification_id}, UpdateExpression='SET #s = :failed, last_error = :error, updated_at = :at ADD attempts :one',
                          ExpressionAttributeNames={'#s': 'status'}, ExpressionAttributeValues={':failed': 'FAILED', ':error': type(exc).__name__, ':at': datetime.now(timezone.utc).isoformat(), ':one': 1})
        raise


def lambda_handler(event, _context):
    failures = []
    for record in event.get('Records', []):
        image = record.get('dynamodb', {}).get('NewImage', {})
        if record.get('eventName') != 'INSERT' and not (record.get('eventName') == 'MODIFY' and image.get('status', {}).get('S') == 'PENDING'):
            continue
        notification_id = DESERIALIZER.deserialize(image['notification_id'])
        try:
            process(notification_id)
        except Exception:
            failures.append({'itemIdentifier': record['dynamodb']['SequenceNumber']})
            break
    return {'batchItemFailures': failures}

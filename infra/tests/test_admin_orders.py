import importlib.util
import json
import os
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import MagicMock, patch
from types import SimpleNamespace
from uuid import uuid4

from boto3.dynamodb.types import TypeDeserializer
from botocore.exceptions import ClientError

sys.path.insert(0, str(Path(__file__).parents[1] / 'src/inventory'))
import inventory

spec = importlib.util.spec_from_file_location('admin_orders_handler', Path(__file__).parents[1] / 'src/lambda/admin_orders/lambda_function.py')
handler = importlib.util.module_from_spec(spec)
with patch.dict(os.environ, {'REQUESTS_TABLE': 'requests-test', 'CONFIRMED_ORDERS_TABLE': 'confirmed-test', 'PRODUCTS_TABLE': 'products-test', 'ALLOWED_ORIGINS': 'https://store.example', 'CUSTOMER_NOTIFICATIONS_TABLE': 'notifications-test', 'PAYMENT_INSTRUCTIONS': 'Pay by bank transfer.'}):
    spec.loader.exec_module(handler)
deserializer = TypeDeserializer()


def unwire(value):
    return {k: deserializer.deserialize(v) for k, v in value.items()}


def conflict():
    return ClientError({'Error': {'Code': 'TransactionCanceledException', 'Message': 'conditional conflict'}}, 'TransactWriteItems')


class FakeTable:
    def __init__(self, key):
        self.key = key
        self.items = {}

    def identity(self, item):
        return tuple(item[k] for k in self.key)

    def get_item(self, Key, **_):
        value = self.items.get(self.identity(Key))
        return {'Item': deepcopy(value)} if value else {}

    def update_item(self, Key, **kwargs):
        current = self.items.get(self.identity(Key))
        if not current or current.get('review_status', 'PENDING') != 'PENDING' or current.get('order_id'):
            raise ClientError({'Error': {'Code': 'ConditionalCheckFailedException'}}, 'UpdateItem')
        values = kwargs['ExpressionAttributeValues']
        current.update(review_status=values[':declined'], reviewed_at=values[':at'], reviewed_by=values[':actor'], decline_reason=values[':reason'])
        return {'Attributes': deepcopy(current)}


class FakeDatabase:
    def __init__(self):
        self.tables = {'requests-test': FakeTable(('submission_id',)), 'products-test': FakeTable(('slug',)), 'confirmed-test': FakeTable(('pk', 'sk')), 'notifications-test': FakeTable(('notification_id',))}
        self.fail_next = False

    def Table(self, name):
        return self.tables[name]

    def transact(self, actions):
        # Validate all conditions against the same pre-write snapshot first.
        if self.fail_next:
            self.fail_next = False
            raise conflict()
        for entry in actions:
            operation, data = next(iter(entry.items()))
            table = self.Table(data['TableName'])
            values = unwire(data.get('ExpressionAttributeValues', {}))
            if operation == 'Put':
                item = unwire(data['Item'])
                existing = table.items.get(table.identity(item))
                if data.get('ConditionExpression', '').startswith('attribute_not_exists(') and existing:
                    raise conflict()
                if '#version = :expected' == data.get('ConditionExpression') and (not existing or existing['version'] != values[':expected']):
                    raise conflict()
            elif operation == 'Update':
                current = table.items.get(table.identity(unwire(data['Key'])))
                if data['TableName'] == 'products-test':
                    if not current or current.get('inventory') != values[':original']:
                        raise conflict()
                    if ':active' in values and (current.get('catalog_status') != values[':active'] or current.get('colors') != values[':colors'] or current.get('sizes') != values[':sizes']):
                        raise conflict()
                    if ':name' in values and (current.get('name') != values[':name'] or current.get('price_cents') != values[':price']):
                        raise conflict()
                    continue
                if not current or current.get('order_id') or current.get('review_status', 'PENDING') != 'PENDING':
                    raise conflict()
            elif operation == 'ConditionCheck':
                current = table.items.get(table.identity(unwire(data['Key'])))
                if not current or current.get('catalog_status') != values[':active'] or any(current.get(field) != values[token] for field, token in [('name', ':name'), ('price_cents', ':price'), ('colors', ':colors'), ('sizes', ':sizes')]):
                    raise conflict()
        for entry in actions:
            operation, data = next(iter(entry.items()))
            table = self.Table(data['TableName'])
            if operation == 'Put':
                item = unwire(data['Item'])
                table.items[table.identity(item)] = deepcopy(item)
            elif operation == 'Update':
                item = table.items[table.identity(unwire(data['Key']))]
                values = unwire(data['ExpressionAttributeValues'])
                if data['TableName'] == 'products-test':
                    item['inventory'] = deepcopy(values[':updated'])
                elif ':converted' in values:
                    item.update(review_status=values[':converted'], order_id=values[':order'], reviewed_at=values[':at'], reviewed_by=values[':actor'])
                else:
                    item.update(review_status=values[':declined'], decline_reason=values[':reason'], reviewed_at=values[':at'], reviewed_by=values[':actor'])


class AdminOrdersTests(unittest.TestCase):
    def setUp(self):
        self.database = FakeDatabase()
        handler.DB = self.database
        self.transact_patch = patch.object(handler, 'transact', self.database.transact)
        self.transact_patch.start()
        self.addCleanup(self.transact_patch.stop)
        self.request_id = str(uuid4())
        self.request = {'submission_id': self.request_id, 'order_reference': 'SC-20260101-FFFF', 'review_status': 'PENDING', 'created_at': '2026-01-01T00:00:00+00:00',
                        'customer': {'first_name': 'Ada', 'last_name': 'L', 'email': 'a@example.com', 'phone': '555', 'address': '1 Road', 'city': 'Chicago', 'state': 'IL', 'postal_code': '60601', 'country': 'US'},
                        'items': [{'product_slug': 'tee', 'name': 'Old name', 'color': 'Black', 'size': 'M', 'quantity': 2, 'unit_price_cents': 1200, 'line_total_cents': 2400}],
                        'shipping_cents': 800, 'subtotal_cents': 2400, 'total_cents': 3200}
        self.product = {'slug': 'tee', 'name': 'New name', 'price_cents': 1500, 'catalog_status': 'ACTIVE', 'sizes': ['M'], 'colors': ['Black']}
        self.database.Table('requests-test').items[(self.request_id,)] = deepcopy(self.request)
        self.database.Table('products-test').items[('tee',)] = deepcopy(self.product)

    def payload(self, method='SHIPPING'):
        _, _, digest = handler.quote(self.request)
        return {'quoteToken': digest, 'availabilityConfirmed': True, 'fulfillmentMethod': method, 'pickupInstructions': 'Call on arrival' if method == 'PICKUP' else '', 'discountCents': 200, 'shippingCents': 0 if method == 'PICKUP' else 800, 'taxCents': 100, 'adjustmentReason': 'Agreed with customer'}

    def create(self, method='SHIPPING'):
        return handler.confirm(self.request_id, self.payload(method), 'admin-sub')

    def act(self, order, kind, **extra):
        return handler.action(order['order_id'], {'version': int(order['version']), 'operationId': str(uuid4()), 'action': kind, **extra}, 'admin-sub')

    def test_confirm_prices_snapshot_and_retries_only_once(self):
        result = self.create()
        self.assertEqual((result['subtotal_cents'], result['total_cents']), (3000, 3700))
        self.assertEqual(result['items'][0]['name'], 'New name')
        self.database.Table('products-test').items[('tee',)]['name'] = 'Later name'
        self.assertEqual(handler.get_order(result['order_id'])['items'][0]['name'], 'New name')
        retry = handler.confirm(self.request_id, {}, 'admin-sub')
        self.assertEqual(retry['order_id'], result['order_id'])
        records = self.database.Table('confirmed-test').items.values()
        self.assertEqual(sum(item['sk'] == 'META' for item in records), 1)
        self.assertEqual(sum(item['sk'].startswith('EVENT#') for item in records), 1)

    def test_missing_payment_instructions_prevents_confirmation(self):
        with patch.object(handler, 'PAYMENT_INSTRUCTIONS', ''):
            with self.assertRaises(handler.ApiError) as error:
                self.create()
        self.assertEqual(error.exception.status, 503)
        self.assertFalse(self.database.Table('notifications-test').items)

    def test_stale_quote_and_invalid_variant_do_not_convert(self):
        payload = self.payload()
        self.database.Table('products-test').items[('tee',)]['price_cents'] = 2100
        with self.assertRaises(handler.ApiError) as error:
            handler.confirm(self.request_id, payload, 'admin-sub')
        self.assertEqual(error.exception.status, 409)
        self.database.Table('products-test').items[('tee',)]['sizes'] = ['S']
        with self.assertRaises(handler.ApiError):
            handler.confirm(self.request_id, payload, 'admin-sub')
        self.assertFalse(self.database.Table('confirmed-test').items)

    def test_transaction_failure_does_not_link_request_or_create_order(self):
        payload = self.payload()
        self.database.fail_next = True
        with self.assertRaises(handler.ApiError):
            handler.confirm(self.request_id, payload, 'admin-sub')
        self.assertNotIn('order_id', handler.get_request(self.request_id))
        self.assertFalse(self.database.Table('confirmed-test').items)

    def test_decline_prevents_confirmation_and_confirmation_prevents_decline(self):
        payload = self.payload()
        handler.decline(self.request_id, {'reason': 'Unavailable'}, 'admin-sub')
        with self.assertRaises(handler.ApiError):
            handler.confirm(self.request_id, payload, 'admin-sub')
        self.database.Table('requests-test').items[(self.request_id,)] = deepcopy(self.request)
        self.create()
        with self.assertRaises(handler.ApiError):
            handler.decline(self.request_id, {'reason': 'Unavailable'}, 'admin-sub')

    def test_shipping_requires_payment_and_completes(self):
        order = self.act(self.create(), 'START_PROCESSING')
        with self.assertRaises(handler.ApiError):
            self.act(order, 'SHIP', carrier='UPS')
        order = self.act(order, 'RECORD_PAYMENT', paymentMethod='Bank transfer')
        order = self.act(order, 'SHIP', carrier='UPS', tracking='123')
        order = self.act(order, 'DELIVER')
        self.assertEqual((order['order_status'], order['fulfillment_status']), ('COMPLETED', 'DELIVERED'))
        self.assertNotIn('fulfillment_pk', handler.get_order(order['order_id']))

    def test_tracked_manual_order_reserves_then_consumes_on_shipment(self):
        key = inventory.variant_key('Black', 'M')
        self.database.Table('products-test').items[('tee',)]['inventory'] = {key: {'color': 'Black', 'size': 'M', 'onHand': 5, 'reserved': 0}}
        with patch.object(handler, 'MANUAL_INVENTORY_ENABLED', True):
            order = self.create()
            stock = self.database.Table('products-test').items[('tee',)]['inventory'][key]
            self.assertEqual((stock['onHand'], stock['reserved']), (5, 2))
            self.assertEqual(order['inventory_reservation'], 'RESERVED')
            order = self.act(order, 'START_PROCESSING')
            order = self.act(order, 'RECORD_PAYMENT', paymentMethod='Cash')
            order = self.act(order, 'SHIP', carrier='UPS')
            stock = self.database.Table('products-test').items[('tee',)]['inventory'][key]
            self.assertEqual((stock['onHand'], stock['reserved']), (3, 0))
            self.assertEqual(order['inventory_reservation'], 'CONSUMED')

    def test_tracked_manual_cancellation_releases_stock(self):
        key = inventory.variant_key('Black', 'M')
        self.database.Table('products-test').items[('tee',)]['inventory'] = {key: {'color': 'Black', 'size': 'M', 'onHand': 5, 'reserved': 0}}
        with patch.object(handler, 'MANUAL_INVENTORY_ENABLED', True):
            order = self.act(self.create(), 'CANCEL', reason='Changed mind')
            stock = self.database.Table('products-test').items[('tee',)]['inventory'][key]
            self.assertEqual((stock['onHand'], stock['reserved']), (5, 0))
            self.assertEqual(order['inventory_reservation'], 'RELEASED')

    def test_tracked_pickup_consumes_stock_when_payment_and_handoff_complete(self):
        key = inventory.variant_key('Black', 'M')
        self.database.Table('products-test').items[('tee',)]['inventory'] = {key: {'color': 'Black', 'size': 'M', 'onHand': 5, 'reserved': 0}}
        with patch.object(handler, 'MANUAL_INVENTORY_ENABLED', True):
            order = self.act(self.create('PICKUP'), 'START_PROCESSING')
            order = self.act(order, 'READY_FOR_PICKUP')
            order = self.act(order, 'PICKED_UP_AND_PAY', paymentMethod='Cash')
        stock = self.database.Table('products-test').items[('tee',)]['inventory'][key]
        self.assertEqual((stock['onHand'], stock['reserved']), (3, 0))
        self.assertEqual(order['inventory_reservation'], 'CONSUMED')

    def test_tracked_manual_confirmation_rejects_untracked_stock(self):
        with patch.object(handler, 'MANUAL_INVENTORY_ENABLED', True), self.assertRaises(handler.ApiError) as error:
            self.create()
        self.assertEqual(error.exception.status, 409)
        self.assertNotIn('order_id', handler.get_request(self.request_id))

    def test_failed_confirmation_transaction_leaves_stock_untouched(self):
        key = inventory.variant_key('Black', 'M')
        self.database.Table('products-test').items[('tee',)]['inventory'] = {key: {'color': 'Black', 'size': 'M', 'onHand': 5, 'reserved': 0}}
        self.database.fail_next = True
        with patch.object(handler, 'MANUAL_INVENTORY_ENABLED', True), self.assertRaises(handler.ApiError):
            self.create()
        self.assertEqual(self.database.Table('products-test').items[('tee',)]['inventory'][key]['reserved'], 0)
        self.assertNotIn('order_id', handler.get_request(self.request_id))

    def test_concurrent_stock_change_blocks_confirmation(self):
        key = inventory.variant_key('Black', 'M')
        product = self.database.Table('products-test').items[('tee',)]
        product['inventory'] = {key: {'color': 'Black', 'size': 'M', 'onHand': 2, 'reserved': 0}}
        def competing_transaction(actions):
            product['inventory'][key]['reserved'] = 2
            self.database.transact(actions)
        with patch.object(handler, 'MANUAL_INVENTORY_ENABLED', True), patch.object(handler, 'transact', competing_transaction), self.assertRaises(handler.ApiError) as error:
            self.create()
        self.assertEqual(error.exception.status, 409)
        self.assertNotIn('order_id', handler.get_request(self.request_id))
        self.assertEqual(product['inventory'][key]['reserved'], 2)

    def test_retrying_tracked_cancellation_releases_once(self):
        key = inventory.variant_key('Black', 'M')
        self.database.Table('products-test').items[('tee',)]['inventory'] = {key: {'color': 'Black', 'size': 'M', 'onHand': 5, 'reserved': 0}}
        with patch.object(handler, 'MANUAL_INVENTORY_ENABLED', True):
            order = self.create()
            payload = {'version': 1, 'operationId': str(uuid4()), 'action': 'CANCEL', 'reason': 'Changed mind'}
            handler.action(order['order_id'], payload, 'admin-sub')
            handler.action(order['order_id'], payload, 'admin-sub')
        stock = self.database.Table('products-test').items[('tee',)]['inventory'][key]
        self.assertEqual((stock['onHand'], stock['reserved']), (5, 0))

    def test_pickup_cash_and_paid_cancellation(self):
        order = self.act(self.create('PICKUP'), 'START_PROCESSING')
        order = self.act(order, 'READY_FOR_PICKUP')
        order = self.act(order, 'PICKED_UP_AND_PAY', paymentMethod='Cash')
        self.assertEqual((order['order_status'], order['payment_status']), ('COMPLETED', 'PAID'))
        self.database.Table('requests-test').items[(self.request_id,)] = deepcopy(self.request)
        second = self.act(self.create(), 'RECORD_PAYMENT', paymentMethod='Cash')
        canceled = self.act(second, 'CANCEL', reason='Customer request')
        self.assertTrue(canceled['refund_follow_up'])
        self.assertEqual(canceled['payment_status'], 'PAID')

    def test_concurrency_and_payment_operation_idempotency(self):
        order = self.create()
        payload = {'version': 1, 'operationId': str(uuid4()), 'action': 'RECORD_PAYMENT', 'paymentMethod': 'Cash'}
        updated = handler.action(order['order_id'], payload, 'admin')
        retried = handler.action(order['order_id'], payload, 'admin')
        self.assertEqual(updated['version'], retried['version'])
        with self.assertRaises(handler.ApiError):
            handler.action(order['order_id'], {**payload, 'paymentMethod': 'Card'}, 'admin')
        with self.assertRaises(handler.ApiError):
            self.act(order, 'START_PROCESSING')
        events = [x for x in self.database.Table('confirmed-test').items.values() if x['sk'].startswith('EVENT#')]
        self.assertEqual(len(events), 2)
        self.assertEqual(len(self.database.Table('notifications-test').items), 2)

    def test_endpoint_requires_admin_and_authenticated_actor(self):
        request = {'routeKey': 'GET /admin/orders', 'headers': {'origin': 'https://store.example'}}
        self.assertEqual(handler.lambda_handler(request, None)['statusCode'], 403)
        request['requestContext'] = {'authorizer': {'jwt': {'claims': {'cognito:groups': '["starchild-admin"]'}}}}
        self.assertEqual(handler.lambda_handler(request, None)['statusCode'], 403)
        request['requestContext']['authorizer']['jwt']['claims'] = {'cognito:groups': '["not-starchild-admin"]', 'sub': 'abc'}
        self.assertEqual(handler.lambda_handler(request, None)['statusCode'], 403)

    def test_authorized_request_detail_returns_server_pricing_preview(self):
        event = {'routeKey': 'GET /admin/order-requests/{id}', 'pathParameters': {'id': self.request_id},
                 'requestContext': {'authorizer': {'jwt': {'claims': {'cognito:groups': '["starchild-admin"]', 'sub': 'actor'}}}}}
        result = handler.lambda_handler(event, None)
        self.assertEqual(result['statusCode'], 200)
        self.assertEqual(json.loads(result['body'])['preview']['subtotal_cents'], 3000)

    def test_rejects_incomplete_or_wrong_partition_cursor(self):
        cursor = handler.cursor_encode({'pk': 'ORDER#other', 'sk': 'META'}, 'events:one')
        with self.assertRaises(handler.ApiError):
            handler.cursor_decode(cursor, 'events:one', {'pk', 'sk'}, ('pk', 'ORDER#one'))
        with self.assertRaises(handler.ApiError):
            handler.cursor_decode(cursor, 'events:one', {'pk', 'sk', 'index_sort'})

    def test_stripe_confirmation_uses_authorized_snapshot_and_idempotent_capture(self):
        request = self.database.Table('requests-test').items[(self.request_id,)]
        request.update(payment_provider='stripe', payment_status='AUTHORIZED', payment_intent_id='pi_test',
                       checkout_session_id='cs_test', capture_before=2000000000, tax_cents=100, total_cents=3300)
        intent = SimpleNamespace(retrieve=MagicMock(return_value={'status': 'requires_capture', 'amount_capturable': 3300}), capture=MagicMock())
        stripe = SimpleNamespace(PaymentIntent=intent)
        with patch.object(handler, 'stripe_lock'), patch.object(handler, 'stripe_service', return_value=(stripe, lambda x: x)):
            order = handler.confirm(self.request_id, {'availabilityConfirmed': True}, 'admin')
            self.assertEqual(order['total_cents'], 3300)
            self.assertEqual(order['items'][0]['name'], 'Old name')
            self.assertEqual(order['payment_status'], 'PENDING')
            handler.confirm(self.request_id, {}, 'admin')
        self.assertEqual(intent.capture.call_count, 2)
        self.assertEqual(intent.capture.call_args.kwargs['idempotency_key'], 'capture-' + order['order_id'])
        with self.assertRaises(handler.ApiError):
            self.act(order, 'RECORD_PAYMENT', paymentMethod='Cash')
        with self.assertRaises(handler.ApiError):
            self.act(order, 'CANCEL', reason='Unavailable')

    def test_expired_stripe_authorization_cannot_be_confirmed(self):
        request = self.database.Table('requests-test').items[(self.request_id,)]
        request.update(payment_provider='stripe', payment_status='AUTHORIZED', payment_intent_id='pi_test',
                       checkout_session_id='cs_test', capture_before=1, tax_cents=0, total_cents=3200)
        stripe = SimpleNamespace(PaymentIntent=SimpleNamespace(retrieve=MagicMock(return_value={'status': 'canceled', 'amount_capturable': 0})))
        with patch.object(handler, 'stripe_lock'), patch.object(handler, 'stripe_service', return_value=(stripe, lambda x: x)):
            with self.assertRaises(handler.ApiError) as error:
                handler.confirm(self.request_id, {'availabilityConfirmed': True}, 'admin')
        self.assertEqual(error.exception.status, 409)
        self.assertNotIn('order_id', handler.get_request(self.request_id))

    def test_cursor_scope_validation(self):
        cursor = handler.cursor_encode({'pk': 'ORDER#abc', 'sk': 'META'}, 'one')
        self.assertEqual(handler.cursor_decode(cursor, 'one')['sk'], 'META')
        with self.assertRaises(handler.ApiError):
            handler.cursor_decode(cursor, 'two')

if __name__ == '__main__':
    unittest.main()

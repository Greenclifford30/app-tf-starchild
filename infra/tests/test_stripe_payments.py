import importlib.util
import json
import os
import sys
import tempfile
import zipfile
import unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

from boto3.dynamodb.types import TypeDeserializer

ROOT = Path(__file__).parents[1]
# Exercise the same committed dependency bundle and helper sources used by remote runs.
_ARTIFACT_DIR = tempfile.TemporaryDirectory(prefix='starchild-payment-tests-')
with zipfile.ZipFile(ROOT / 'artifacts/stripe-python-3.13-arm64.zip') as artifact:
    artifact.extractall(_ARTIFACT_DIR.name)
sys.path.insert(0, str(Path(_ARTIFACT_DIR.name) / 'python'))
sys.path.insert(0, str(ROOT / 'src/payment_layer'))
validation_spec = importlib.util.spec_from_file_location('order_validation', ROOT / 'src/lambda/create_order/lambda_function.py')
validation_module = importlib.util.module_from_spec(validation_spec)
sys.modules['order_validation'] = validation_module
validation_spec.loader.exec_module(validation_module)
deserializer = TypeDeserializer()

class Table:
    def __init__(self, key):
        self.key = key
        self.items = {}
    def get_item(self, Key, **kwargs):
        item = self.items.get(tuple(Key[k] for k in self.key))
        return {'Item': deepcopy(item)} if item else {}
    def put_item(self, Item, **kwargs):
        self.items[tuple(Item[k] for k in self.key)] = deepcopy(Item)
    def update_item(self, Key, **kwargs):
        item = self.items[tuple(Key[k] for k in self.key)]
        values = kwargs['ExpressionAttributeValues']
        if ':session' in values:
            item.update(checkout_status='OPEN', checkout_session_id=values[':session'])
        elif ':failed' in values:
            item['payment_status'] = 'FAILED'

class Database:
    def __init__(self):
        self.tables = {'requests': Table(('submission_id',)), 'orders': Table(('pk', 'sk')), 'notifications': Table(('notification_id',))}
    def Table(self, name):
        return self.tables[name]

class Transaction:
    def __init__(self, db):
        self.db = db
    def transact_write_items(self, TransactItems):
        for action in TransactItems:
            if 'Put' not in action:
                continue
            put = action['Put']
            item = {k: deserializer.deserialize(v) for k, v in put['Item'].items()}
            self.db.Table(put['TableName']).put_item(Item=item)

with patch.dict(os.environ, {'REQUESTS_TABLE': 'requests', 'CONFIRMED_ORDERS_TABLE': 'orders', 'CUSTOMER_NOTIFICATIONS_TABLE': 'notifications', 'STRIPE_APPAREL_TAX_CODE': 'txcd_123', 'ALLOWED_ORIGINS': 'https://shop.example', 'AWS_EC2_METADATA_DISABLED': 'true'}), patch('boto3.resource'), patch('boto3.client'):
    spec = importlib.util.spec_from_file_location('stripe_payment_handler', ROOT / 'src/lambda/payments/lambda_function.py')
    handler = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(handler)

class StripePaymentsTests(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        handler.DB = self.db
        handler.DYNAMO = Transaction(self.db)
        self.attempt = str(uuid4())
        self.items = [{'product_slug': 'tee', 'name': 'Tee', 'color': 'Black', 'size': 'M', 'quantity': 2, 'unit_price_cents': 1500, 'line_total_cents': 3000}]
        self.stripe = SimpleNamespace(checkout=SimpleNamespace(Session=SimpleNamespace(create=MagicMock(return_value={'id': 'cs_test', 'client_secret': 'secret'}), retrieve=MagicMock())), PaymentIntent=SimpleNamespace(retrieve=MagicMock()), Refund=SimpleNamespace(retrieve=MagicMock()))
        self.client = patch.object(handler, 'client', return_value=(self.stripe, 'whsec_test'))
        self.validation = patch.object(handler.validation, '_validate_items', return_value=self.items)
        self.client.start(); self.validation.start()
        self.addCleanup(self.client.stop); self.addCleanup(self.validation.stop)
        self.payload = {'attemptId': self.attempt, 'items': [{'productSlug': 'tee', 'color': 'Black', 'size': 'M', 'quantity': 2}]}

    def create(self):
        return handler.create_session(self.payload, 'https://shop.example')

    def authorize(self):
        self.create()
        self.stripe.checkout.Session.retrieve.return_value = {'id': 'cs_test', 'metadata': {'starchild_attempt_id': self.attempt}, 'currency': 'usd', 'amount_subtotal': 3000, 'amount_total': 4075,
            'total_details': {'amount_tax': 275}, 'automatic_tax': {'status': 'complete'},
            'customer_details': {'email': 'buyer@example.com', 'phone': '555'},
            'collected_information': {'shipping_details': {'name': 'Ada Lovelace', 'address': {'line1': '1 Road', 'city': 'Chicago', 'state': 'IL', 'postal_code': '60601', 'country': 'US'}}},
            'payment_intent': {'id': 'pi_test', 'metadata': {'starchild_attempt_id': self.attempt}, 'status': 'requires_capture', 'amount_capturable': 4075, 'latest_charge': {'payment_method_details': {'card': {'capture_before': 2000000000}}}}}
        handler.authorize('cs_test')

    def test_dependency_artifact_contains_arm64_libraries_and_no_project_helpers(self):
        with zipfile.ZipFile(ROOT / 'artifacts/stripe-python-3.13-arm64.zip') as artifact:
            names = artifact.namelist()
            self.assertIn('python/stripe/__init__.py', names)
            self.assertNotIn('python/starchild_stripe.py', names)
            self.assertNotIn('python/order_validation.py', names)
            for name in (entry for entry in names if entry.endswith('.so')):
                header = artifact.read(name)[:20]
                self.assertEqual(header[:4], b'\x7fELF')
                self.assertEqual(int.from_bytes(header[18:20], 'little'), 183, name)

    def test_checkout_prices_are_server_derived_and_retry_is_idempotent(self):
        self.create()
        self.stripe.checkout.Session.retrieve.return_value = {'id': 'cs_test', 'status': 'open', 'client_secret': 'secret'}
        self.create()
        self.assertEqual(self.stripe.checkout.Session.create.call_count, 1)
        self.stripe.checkout.Session.retrieve.assert_called_once_with('cs_test')
        options = self.stripe.checkout.Session.create.call_args.kwargs
        self.assertEqual(options['line_items'][0]['price_data']['unit_amount'], 1500)
        self.assertEqual(options['shipping_options'][0]['shipping_rate_data']['fixed_amount']['amount'], 800)
        self.assertEqual(options['payment_intent_data']['capture_method'], 'manual')
        self.assertNotIn('payment_method_types', options)
        self.assertEqual(options['idempotency_key'], 'checkout-v2-' + self.attempt)
        with self.assertRaises(handler.BadRequest):
            handler.create_session({**self.payload, 'items': []}, 'https://shop.example')

    def test_existing_open_session_is_reused_after_checkout_configuration_change(self):
        self.create()
        self.stripe.checkout.Session.create.reset_mock()
        self.stripe.checkout.Session.retrieve.return_value = {'id': 'cs_test', 'status': 'open', 'client_secret': 'original-secret'}
        result = self.create()
        self.assertEqual(result['clientSecret'], 'original-secret')
        self.stripe.checkout.Session.create.assert_not_called()

    def test_completed_existing_session_is_not_recreated(self):
        self.create()
        self.stripe.checkout.Session.retrieve.return_value = {'id': 'cs_test', 'status': 'complete', 'client_secret': None}
        with self.assertRaises(handler.BadRequest):
            self.create()
        self.assertEqual(self.stripe.checkout.Session.create.call_count, 1)

    def test_authorization_stores_tax_and_replay_does_not_duplicate_notifications(self):
        self.authorize(); handler.authorize('cs_test')
        saved = self.db.Table('requests').items[(self.attempt,)]
        self.assertEqual((saved['payment_status'], saved['total_cents'], saved['tax_cents']), ('AUTHORIZED', 4075, 275))
        self.assertEqual(len(self.db.Table('notifications').items), 2)

    def test_status_requires_the_matching_stripe_session(self):
        self.authorize()
        self.assertEqual(handler.status(self.attempt, 'cs_test')['status'], 'AUTHORIZED')
        with self.assertRaises(handler.BadRequest):
            handler.status(self.attempt, 'cs_different')

    def test_wrong_total_never_creates_a_reviewable_request(self):
        self.create()
        self.stripe.checkout.Session.retrieve.return_value = {'metadata': {'starchild_attempt_id': self.attempt}, 'currency': 'usd', 'amount_subtotal': 3000, 'amount_total': 1, 'payment_intent': {'metadata': {'starchild_attempt_id': self.attempt}, 'status': 'requires_capture', 'amount_capturable': 1}}
        with self.assertRaises(ValueError): handler.authorize('cs_test')
        self.assertNotIn('review_status', self.db.Table('requests').items[(self.attempt,)])

    def test_refund_pending_is_not_overwritten_by_capture_webhook(self):
        self.authorize()
        req = self.db.Table('requests').items[(self.attempt,)]; req['order_id'] = 'order'
        order = {'pk': 'ORDER#order', 'sk': 'META', 'order_id': 'order', 'payment_intent_id': 'pi_test', 'payment_status': 'REFUND_PENDING', 'total_cents': 4075, 'version': 2}
        self.db.Table('orders').put_item(Item=order)
        self.stripe.PaymentIntent.retrieve.return_value = {'id': 'pi_test', 'metadata': {'starchild_attempt_id': self.attempt}, 'status': 'succeeded', 'amount_received': 4075}
        handler.reconcile_intent('pi_test')
        self.assertEqual(self.db.Table('orders').items[('ORDER#order', 'META')]['payment_status'], 'REFUND_PENDING')

    def test_refund_requires_a_succeeded_stripe_refund(self):
        self.authorize()
        req = self.db.Table('requests').items[(self.attempt,)]; req['order_id'] = 'order'
        order = {'pk': 'ORDER#order', 'sk': 'META', 'order_id': 'order', 'payment_intent_id': 'pi_test', 'payment_status': 'REFUND_PENDING', 'total_cents': 4075, 'version': 2, 'refund_follow_up': True}
        self.db.Table('orders').put_item(Item=order)
        self.stripe.PaymentIntent.retrieve.return_value = {'metadata': {'starchild_attempt_id': self.attempt}}
        self.stripe.Refund.retrieve.return_value = {'id': 're_test', 'payment_intent': 'pi_test', 'amount': 4075, 'status': 'pending'}
        handler.reconcile_refund('re_test')
        self.assertEqual(self.db.Table('orders').items[('ORDER#order', 'META')]['payment_status'], 'REFUND_PENDING')
        self.stripe.Refund.retrieve.return_value['status'] = 'succeeded'
        handler.reconcile_refund('re_test')
        self.assertEqual(self.db.Table('orders').items[('ORDER#order', 'META')]['payment_status'], 'REFUNDED')
        self.stripe.Refund.retrieve.return_value['status'] = 'failed'
        handler.reconcile_refund('re_test')
        self.assertEqual(self.db.Table('orders').items[('ORDER#order', 'META')]['payment_status'], 'REFUND_FAILED')

    def test_real_stripe_objects_are_converted_recursively(self):
        import stripe
        from starchild_stripe import plain
        value = stripe.StripeObject.construct_from({'payment_intent': {'id': 'pi_test'}}, 'sk_test')
        self.assertEqual(plain(value), {'payment_intent': {'id': 'pi_test'}})

    def test_payment_failure_before_authorization_is_not_a_webhook_error(self):
        self.create()
        self.stripe.PaymentIntent.retrieve.return_value = {'id': 'pi_test', 'metadata': {'starchild_attempt_id': self.attempt}, 'status': 'requires_payment_method'}
        handler.reconcile_intent('pi_test', ignore_unlinked=True)
        self.assertNotIn('payment_status', self.db.Table('requests').items[(self.attempt,)])

    def test_captured_payment_is_recorded_once(self):
        self.authorize()
        req = self.db.Table('requests').items[(self.attempt,)]; req['order_id'] = 'order'
        order = {'pk': 'ORDER#order', 'sk': 'META', 'order_id': 'order', 'payment_intent_id': 'pi_test', 'payment_status': 'PENDING', 'total_cents': 4075, 'version': 1}
        self.db.Table('orders').put_item(Item=order)
        self.stripe.PaymentIntent.retrieve.return_value = {'id': 'pi_test', 'metadata': {'starchild_attempt_id': self.attempt}, 'status': 'succeeded', 'amount_received': 4075}
        handler.reconcile_intent('pi_test'); handler.reconcile_intent('pi_test')
        self.assertEqual(self.db.Table('orders').items[('ORDER#order', 'META')]['payment_status'], 'PAID')
        self.assertIn(('ORDER#order#STRIPE_PAID',), self.db.Table('notifications').items)

    def test_unrelated_account_payment_is_ignored(self):
        self.stripe.PaymentIntent.retrieve.return_value = {'id': 'pi_other', 'metadata': {}, 'status': 'succeeded'}
        handler.reconcile_intent('pi_other')
        self.assertFalse(self.db.Table('requests').items)

    def test_invalid_signature_is_rejected(self):
        import stripe
        self.stripe.Webhook = stripe.Webhook
        self.stripe.error = stripe.error
        result = handler.lambda_handler({'routeKey': 'POST /stripe/webhook', 'headers': {'stripe-signature': 't=1,v1=bad'}, 'body': '{}'}, None)
        self.assertEqual(result['statusCode'], 400)

if __name__ == '__main__': unittest.main()

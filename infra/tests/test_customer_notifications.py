import importlib.util
import os
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from botocore.exceptions import ClientError

spec = importlib.util.spec_from_file_location('customer_notifications_handler', Path(__file__).parents[1] / 'src/lambda/customer_notifications/lambda_function.py')
handler = importlib.util.module_from_spec(spec)
with patch.dict(os.environ, {'CUSTOMER_NOTIFICATIONS_TABLE': 'notifications-test', 'AWS_DEFAULT_REGION': 'us-east-1', 'AWS_ACCESS_KEY_ID': 'test', 'AWS_SECRET_ACCESS_KEY': 'test'}):
    spec.loader.exec_module(handler)


class Table:
    def __init__(self, job):
        self.job = deepcopy(job)
        self.updates = []

    def get_item(self, **kwargs):
        return {'Item': deepcopy(self.job)}

    def update_item(self, **kwargs):
        values = kwargs['ExpressionAttributeValues']
        self.job['status'] = values.get(':sent', values.get(':failed'))
        self.updates.append(kwargs)


class Ses:
    def __init__(self, fail=False):
        self.fail = fail
        self.sent = []

    def send_email(self, **kwargs):
        if self.fail:
            raise ClientError({'Error': {'Code': 'MessageRejected'}}, 'SendEmail')
        self.sent.append(kwargs)
        return {'MessageId': 'message-1'}


class NotificationTests(unittest.TestCase):
    def setUp(self):
        self.order = {'order_reference': 'REQUEST-1', 'order_number': 'ORDER-1', 'customer': {'first_name': 'Ada', 'email': 'ada@example.com'},
                      'items': [{'quantity': 2, 'name': 'Tee', 'color': 'Black', 'size': 'M', 'line_total_cents': 3000}],
                      'subtotal_cents': 3000, 'discount_cents': 100, 'shipping_cents': 500, 'tax_cents': 100, 'total_cents': 3500,
                      'payment_instructions': 'Pay by transfer', 'fulfillment_method': 'PICKUP', 'pickup_instructions': 'Call ahead',
                      'shipment': {'carrier': 'UPS', 'tracking': '123'}, 'cancel_reason': 'Requested', 'decline_reason': 'Unavailable', 'refund_follow_up': True}

    def test_all_customer_messages_include_correct_details(self):
        examples = {'REQUEST_RECEIVED': 'No payment has been collected', 'REQUEST_DECLINED': 'Unavailable',
                    'ORDER_CONFIRMED': 'Pay by transfer', 'RECORD_PAYMENT': '$35.00', 'SHIP': '123',
                    'DELIVER': 'marked delivered', 'READY_FOR_PICKUP': 'Call ahead', 'PICK_UP': 'picked up',
                    'PICKED_UP_AND_PAY': 'recorded your payment', 'CANCEL': 'follow up'}
        for kind, expected in examples.items():
            with self.subTest(kind=kind):
                subject, body = handler.message({'kind': kind, 'snapshot': self.order})
                self.assertIn('ORDER-1', subject)
                self.assertIn(expected, body)
        self.assertNotIn('refund has been', handler.message({'kind': 'CANCEL', 'snapshot': self.order})[1])

    def test_failure_is_recorded_and_retry_succeeds_without_resending_sent_job(self):
        table = Table({'notification_id': 'job-1', 'kind': 'SHIP', 'status': 'PENDING', 'snapshot': self.order})
        ses = Ses(fail=True)
        with patch.object(handler, 'DB') as database, patch.object(handler, 'SES', ses):
            database.Table.return_value = table
            with self.assertLogs(handler.LOG, level='ERROR'):
                with self.assertRaises(ClientError):
                    handler.process('job-1')
            self.assertEqual(table.job['status'], 'FAILED')
            ses.fail = False
            handler.process('job-1')
            handler.process('job-1')
            self.assertEqual(table.job['status'], 'SENT')
            self.assertEqual(len(ses.sent), 1)
            self.assertEqual(ses.sent[0]['Destination']['ToAddresses'], ['ada@example.com'])

    def test_stream_reports_failed_sequence(self):
        record = {'eventName': 'INSERT', 'dynamodb': {'NewImage': {'notification_id': {'S': 'job-1'}}, 'SequenceNumber': '42'}}
        with patch.object(handler, 'process', side_effect=RuntimeError('failure')):
            self.assertEqual(handler.lambda_handler({'Records': [record]}, None), {'batchItemFailures': [{'itemIdentifier': '42'}]})


if __name__ == '__main__':
    unittest.main()

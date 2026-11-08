import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('order_backfill', Path(__file__).parents[1] / 'scripts/backfill_order_requests.py')
backfill = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backfill)

class Table:
    def __init__(self):
        self.items = {
            'one': {'submission_id': 'one', 'created_at': '2026-01-01'},
            'two': {'submission_id': 'two', 'created_at': '2026-01-02', 'review_status': 'DECLINED'},
            'three': {'submission_id': 'three', 'created_at': '2026-01-03', 'order_id': 'order-id'},
        }
        self.fail_page = True

    def scan(self, **kwargs):
        if kwargs.get('ExclusiveStartKey'):
            if self.fail_page:
                self.fail_page = False
                raise RuntimeError('interrupted')
            return {'Items': [dict(self.items['two']), dict(self.items['three'])]}
        return {'Items': [dict(self.items['one'])], 'LastEvaluatedKey': {'submission_id': 'one'}}

    def update_item(self, Key, ExpressionAttributeValues, **_):
        item = self.items[Key['submission_id']]
        item.setdefault('review_status', ExpressionAttributeValues[':status'])
        item['review_sort'] = ExpressionAttributeValues[':sort']

class BackfillTests(unittest.TestCase):
    def test_resume_and_preserve_existing_review(self):
        table = Table()
        with tempfile.TemporaryDirectory() as directory:
            checkpoint = Path(directory) / 'checkpoint.json'
            with self.assertRaises(RuntimeError):
                backfill.backfill(table, checkpoint, 1)
            self.assertEqual(json.loads(checkpoint.read_text()), {'submission_id': 'one'})
            self.assertEqual(backfill.backfill(table, checkpoint, 1), 2)
            self.assertFalse(checkpoint.exists())
            self.assertEqual(table.items['one']['review_status'], 'PENDING')
            self.assertEqual(table.items['two']['review_status'], 'DECLINED')
            self.assertEqual(table.items['three']['review_status'], 'CONVERTED')
            self.assertEqual(backfill.backfill(table, checkpoint, 1), 0)

if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Add review-index attributes to pre-existing requests without overwriting reviews.

The cursor is an opaque JSON DynamoDB key; save --checkpoint between runs. The
script is safe to rerun, including while the administration API is active.
"""
import argparse
import json
from pathlib import Path

import boto3
from botocore.exceptions import ClientError


def backfill(table, checkpoint=None, page_size=100):
    key = json.loads(checkpoint.read_text()) if checkpoint and checkpoint.exists() else None
    changed = 0
    while True:
        args = {'Limit': page_size, 'ProjectionExpression': 'submission_id, created_at, review_status, review_sort, order_id'}
        if key:
            args['ExclusiveStartKey'] = key
        result = table.scan(**args)
        for item in result.get('Items', []):
            if item.get('review_sort'):
                continue
            status = item.get('review_status') or ('CONVERTED' if item.get('order_id') else 'PENDING')
            sort = f"{item.get('created_at', '1970-01-01T00:00:00+00:00')}#{item['submission_id']}"
            try:
                table.update_item(Key={'submission_id': item['submission_id']},
                    UpdateExpression='SET review_status = if_not_exists(review_status, :status), review_sort = :sort',
                    ConditionExpression='attribute_exists(submission_id) AND attribute_not_exists(review_sort)',
                    ExpressionAttributeValues={':status': status, ':sort': sort})
                changed += 1
            except ClientError as exc:
                if exc.response.get('Error', {}).get('Code') != 'ConditionalCheckFailedException':
                    raise
        key = result.get('LastEvaluatedKey')
        if checkpoint:
            if key:
                checkpoint.write_text(json.dumps(key))
            elif checkpoint.exists():
                checkpoint.unlink()
        if not key:
            return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--table', required=True)
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--page-size', type=int, default=100, choices=range(1, 1001), metavar='1..1000')
    args = parser.parse_args()
    count = backfill(boto3.resource('dynamodb').Table(args.table), args.checkpoint, args.page_size)
    print(f'Indexed {count} order requests.')


if __name__ == '__main__':
    main()

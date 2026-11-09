"""Shared Stripe client. Secrets are fetched at runtime, never placed in Terraform state."""
import json
import os

import boto3
import stripe

_CLIENT = None

def client():
    global _CLIENT
    if _CLIENT is None:
        arn = os.environ.get('STRIPE_SECRET_ARN', '')
        if not arn:
            raise RuntimeError('Stripe secret is not configured')
        secret = json.loads(boto3.client('secretsmanager').get_secret_value(SecretId=arn)['SecretString'])
        stripe.api_key = secret['secret_key']
        stripe.api_version = '2026-10-28.endive'
        _CLIENT = (stripe, secret['webhook_secret'])
    return _CLIENT

def plain(obj):
    if hasattr(obj, 'to_dict'):
        return obj.to_dict()
    return obj.to_dict_recursive() if hasattr(obj, 'to_dict_recursive') else obj

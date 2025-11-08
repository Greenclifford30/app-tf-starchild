import json
import os

def lambda_handler(event, context):
    """
    Users API Lambda function
    Handles GET and POST requests for user management
    """
    
    # Get environment variables
    environment = os.environ.get('ENVIRONMENT', 'unknown')
    table_name = os.environ.get('TABLE_NAME', 'users')
    
    # Extract information from the event
    http_method = event.get('httpMethod', 'UNKNOWN')
    path = event.get('path', '/')
    
    # Handle different HTTP methods
    if http_method == 'GET':
        response_body = handle_get_users(environment, table_name)
    elif http_method == 'POST':
        request_body = json.loads(event.get('body', '{}'))
        response_body = handle_create_user(request_body, environment, table_name)
    else:
        response_body = {
            'error': f'Method {http_method} not supported',
            'supported_methods': ['GET', 'POST']
        }
        status_code = 405
    
    return {
        'statusCode': status_code if 'status_code' in locals() else 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,OPTIONS,POST,PUT,DELETE'
        },
        'body': json.dumps(response_body)
    }

def handle_get_users(environment, table_name):
    """Handle GET request to retrieve users"""
    return {
        'message': 'Users retrieved successfully',
        'environment': environment,
        'table': table_name,
        'users': [
            {'id': 1, 'name': 'John Doe', 'email': 'john@example.com'},
            {'id': 2, 'name': 'Jane Smith', 'email': 'jane@example.com'}
        ],
        'count': 2
    }

def handle_create_user(request_body, environment, table_name):
    """Handle POST request to create a new user"""
    
    # Validate request body
    if not request_body.get('name') or not request_body.get('email'):
        return {
            'error': 'Missing required fields: name and email',
            'received': request_body
        }
    
    # Simulate user creation
    new_user = {
        'id': 3,  # In a real implementation, this would be generated
        'name': request_body['name'],
        'email': request_body['email'],
        'created_at': '2024-01-01T00:00:00Z'
    }
    
    return {
        'message': 'User created successfully',
        'environment': environment,
        'table': table_name,
        'user': new_user
    }
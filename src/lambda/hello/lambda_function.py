import json
import os

def lambda_handler(event, context):
    """
    Simple Hello World Lambda function
    """
    
    # Get environment variables
    environment = os.environ.get('ENVIRONMENT', 'unknown')
    
    # Extract information from the event
    http_method = event.get('httpMethod', 'UNKNOWN')
    path = event.get('path', '/')
    
    # Create response
    response_body = {
        'message': 'Hello from Starchild API!',
        'environment': environment,
        'method': http_method,
        'path': path,
        'timestamp': context.aws_request_id
    }
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'GET,OPTIONS,POST,PUT,DELETE'
        },
        'body': json.dumps(response_body)
    }
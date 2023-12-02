import json
import boto3
from botocore.exceptions import ClientError

s3 = boto3.client('s3')
bucket_name = '${BucketName}'

def lambda_handler(event, context):
    user_id = event.get('queryStringParameters', {}).get('uid')
    if not user_id:
        return {
            'statusCode': 400,
            'body': json.dumps('Bad Request - Missing required parameters')
        }
    # Fetch all messages for the given email from S3
    try:
        messages = get_messages_from_s3(user_id)

        return {
            'statusCode': 200,
            'body': json.dumps(messages)
        }
    except ClientError as e:
        print(f"Error fetching messages from S3: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps('Internal Server Error')
        }

def get_messages_from_s3(id):
    prefix = f'USER#{id}/'

    # List objects in the S3 bucket for the given user
    response = s3.list_objects_v2(
        Bucket=bucket_name,
        Prefix=prefix
    )

    # Extract message content from each S3 object
    messages = []
    for obj in response.get('Contents', []):
        print(obj)
        message_key = obj['Key']
        message_date = message_key.split('/')[1]  # Extract date from the key
        message_content = get_message_content_from_s3(bucket_name, message_key)
        messages.append({
            'key': message_key,
            'date': message_date,
            'content': message_content
        })

    return messages

def get_message_content_from_s3(bucket_name, message_key):
    # Get the content of the S3 object (message)
    response = s3.get_object(
        Bucket=bucket_name,
        Key=message_key
    )

    # Read and return the content of the S3 object
    content = response['Body'].read().decode('utf-8')
    return content
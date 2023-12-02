import json
import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime
from datetime import date

ses = boto3.client('ses')
dynamodb = boto3.client('dynamodb')
s3_client = boto3.client('s3')
table_name = '${DynamoDBTableName}'
bucket= '${BucketName}'
today = date.today()
timestamp = str(int(datetime.timestamp(datetime.now())))

def lambda_handler(event, context):

    # Parse the JSON body from the request
    try:
        body = json.loads(event['body'])
        senderId = body.get('uid')
        contactId = body.get('contactId')
        message = body.get('message')
        subject = body.get('subject')
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps('Bad Request - Invalid JSON')
        }

    # Validate the presence of required parameters
    if not message or not subject or not senderId or not contactId:
        return {
            'statusCode': 400,
            'body': json.dumps('Bad Request - Missing required parameters')
        }
    
    # Send email using SES
    try:
        # get recipient email from db
        dbresponse = dynamodb.get_item(
            TableName=table_name,
            Key={
                'PK': {'S': 'UCONTACT#'+senderId},
                'SK': {'S': 'CONTACT#'+contactId}
            }
        )
        
        recipient_email = dbresponse.get('Item', {}).get('email', {}).get('S', [])
        
        # get sender email from db
        dbresponse = dynamodb.get_item(
            TableName=table_name,
            Key={
                'PK': {'S': 'USER#'+senderId},
                'SK': {'S': 'USER#'+senderId}
            }
        )
        
        sender_email = dbresponse.get('Item', {}).get('email', {}).get('S', [])
        
        # Send Email
        response = ses.send_email(
            Source=sender_email,
            Destination={
                'ToAddresses': [recipient_email],
            },
            Message={
                'Subject': {'Data': subject},
                'Body': {'Text': {'Data': message}},
            }
        )
        mid = response['MessageId']
        print(f"Email sent. Message ID: {response['MessageId']}")
        
        # Put message in S3
        s3_object_key = f'USER#{senderId}/{today}/MSG#{mid}.txt'
        s3_client.put_object(Bucket=bucket, Key=s3_object_key, Body=message)
        print(f"Message stored in S3. Key: {s3_object_key}")
        
        # Store message metadata in DynamoDB
        dynamodb.put_item(
            TableName=table_name,
            Item={
                'PK': {'S': 'UMSG#'+senderId},
                'SK': {'S': 'MSG#'+mid},
                'recepientId': {'S': contactId},
                'date': {'S': str(today)},
                'timestamp': {'S': timestamp},
                'key': {'S': s3_object_key}
            }
        )
        print(f"Metadata stored in DynamoDB.")
        
        return {
            'statusCode': 200,
            'body': json.dumps('Email sent successfully')
        }
    
    except ClientError as e:
        print(f"Error sending email: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps('Internal Server Error')
        }
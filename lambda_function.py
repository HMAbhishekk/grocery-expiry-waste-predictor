import json
import boto3
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
sns = boto3.client('sns', region_name='us-east-1')

grocery_table = dynamodb.Table('GroceryItems')
usage_table = dynamodb.Table('UsageHistory')

SNS_ARN = "arn:aws:sns:us-east-1:861330780609:grocery-expiry-alerts"

def lambda_handler(event, context):
    # Handle CORS preflight
    if event.get('httpMethod') == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'POST, OPTIONS'
            },
            'body': ''
        }

    # Parse body from API Gateway
    if 'body' in event and event['body']:
        try:
            body = json.loads(event['body'])
        except:
            body = event
    else:
        body = event

    action = body.get('action', '')
    if action == 'add_item':
        return add_grocery_item(body)
    elif action == 'predict_waste':
        return predict_waste(body)
    elif action == 'get_items':
        return get_all_items(body)
    elif action == 'check_expiry':
        return check_expiry_alerts(body)
    else:
        return build_response(400, 'Invalid action: ' + action)

def add_grocery_item(event):
    item_id = str(uuid.uuid4())[:8]
    purchase_date = datetime.utcnow().isoformat()
    expiry_date = (datetime.utcnow() +
                   timedelta(days=int(event.get('expiry_days', 7)))).isoformat()
    grocery_table.put_item(Item={
        'userId': event.get('userId', 'user1'),
        'itemId': item_id,
        'itemName': event.get('itemName', ''),
        'quantity': event.get('quantity', '1'),
        'purchaseDate': purchase_date,
        'expiryDate': expiry_date,
        'expiryDays': int(event.get('expiry_days', 7)),
        'category': event.get('category', 'general'),
        'status': 'active'
    })
    return build_response(200,
        "Added " + event.get('itemName', '') + " successfully!",
        {'itemId': item_id})

def predict_waste(event):
    user_id = event.get('userId', 'user1')
    item_name = event.get('itemName', '')
    expiry_days = int(event.get('expiry_days', 7))

    past_items = grocery_table.query(
        KeyConditionExpression='userId = :uid',
        ExpressionAttributeValues={':uid': user_id}
    )
    items_list = [
        i['itemName'] + " - " + i['status']
        for i in past_items.get('Items', [])
    ]
    history_text = '\n'.join(items_list) if items_list else "No history yet"

    prompt = """You are a grocery waste prediction AI.
User wants to buy: """ + item_name + """
Expiry in: """ + str(expiry_days) + """ days
User grocery history:
""" + history_text + """

Respond ONLY in this exact JSON format, no extra text, no markdown:
{
  "waste_probability": <number 0-100>,
  "prediction": "<will use / might waste / likely to waste>",
  "reason": "<one sentence reason>",
  "recipes": ["<recipe 1>", "<recipe 2>", "<recipe 3>"],
  "tip": "<one smart tip to avoid waste>",
  "alert_days_before": <number>
}"""

    bedrock_response = bedrock.invoke_model(
        modelId='amazon.nova-micro-v1:0',
        body=json.dumps({
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ],
            "inferenceConfig": {
                "maxTokens": 500,
                "temperature": 0.3
            }
        }),
        contentType='application/json',
        accept='application/json'
    )

    response_body = json.loads(bedrock_response['body'].read())
    result_text = response_body['output']['message']['content'][0]['text']

    result_text = result_text.strip()
    start = result_text.find('{')
    end = result_text.rfind('}') + 1
    if start != -1 and end > start:
        result_text = result_text[start:end]

    result_text = result_text.strip()
    prediction = json.loads(result_text)
    return build_response(200, 'Prediction ready!', prediction)

def get_all_items(event):
    user_id = event.get('userId', 'user1')
    items = grocery_table.query(
        KeyConditionExpression='userId = :uid',
        ExpressionAttributeValues={':uid': user_id}
    )
    now = datetime.utcnow()
    result = []
    for item in items.get('Items', []):
        expiry = datetime.fromisoformat(item['expiryDate'])
        days_left = (expiry - now).days
        item['daysLeft'] = days_left
        item['urgency'] = (
            'critical' if days_left <= 1 else
            'warning' if days_left <= 3 else
            'good'
        )
        result.append(item)
    result.sort(key=lambda x: x['daysLeft'])
    return build_response(200, 'Items fetched!', {'items': result})

def check_expiry_alerts(event):
    user_id = event.get('userId', 'user1')
    items = grocery_table.query(
        KeyConditionExpression='userId = :uid',
        ExpressionAttributeValues={':uid': user_id}
    )
    now = datetime.utcnow()
    alerts_sent = []
    for item in items.get('Items', []):
        expiry = datetime.fromisoformat(item['expiryDate'])
        days_left = (expiry - now).days
        if days_left <= 2:
            message = "GROCERY EXPIRY ALERT!\nItem: " + item['itemName'] + "\nDays Left: " + str(days_left) + " day(s)\nExpires: " + item['expiryDate'][:10] + "\nUse it today to avoid waste!"
            sns.publish(
                TopicArn=SNS_ARN,
                Message=message,
                Subject=item['itemName'] + " expires in " + str(days_left) + " day(s)!"
            )
            alerts_sent.append(item['itemName'])
    return build_response(200,
        "Alerts sent for: " + ', '.join(alerts_sent),
        {'alertsSent': alerts_sent})

def build_response(status, message, data=None):
    body = {'message': message}
    if data:
        body['data'] = data
    return {
        'statusCode': status,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Methods': 'POST, OPTIONS',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(body, default=str)
    }
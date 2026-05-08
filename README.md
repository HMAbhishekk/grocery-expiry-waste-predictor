# 🥦 AI Grocery Expiry Waste Predictor

An AI-powered grocery expiry waste prediction system built on AWS Free Tier.

## Project Overview
This system predicts food waste before it happens and automatically 
alerts users when groceries are about to expire.

## AWS Services Used
- **Amazon Bedrock** (Nova Micro) — AI waste prediction & recipe generation
- **AWS Lambda** — Serverless backend logic (Python 3.12)
- **Amazon DynamoDB** — NoSQL database for grocery storage
- **API Gateway** — REST API connecting frontend to Lambda
- **Amazon SNS** — Automated email expiry alerts
- **Amazon S3** — Static frontend dashboard hosting
- **AWS IAM** — Roles and permissions management

## Features
- Predicts waste probability (0-100%) using AI
- Generates 3 personalized recipes for expiring items
- Sends automated email alerts 2 days before expiry
- Live dashboard with Critical/Warning/Good urgency levels
- Auto-refreshes every 30 seconds
- 100% serverless — runs on AWS Free Tier ($0 cost)

## Architecture
User Dashboard (S3)
↓
API Gateway (REST API)
↓
Lambda Function (Python 3.12)
↓
Amazon Bedrock Nova Micro (AI Prediction)
↓
DynamoDB (Storage) + SNS (Email Alerts

## Setup Instructions
1. Create IAM role with required permissions
2. Create DynamoDB tables: GroceryItems and UsageHistory
3. Create SNS topic and subscribe your email
4. Deploy Lambda function with the provided code
5. Create API Gateway with POST method
6. Host index.html on S3 static website

## Internship Project
- Domain: AI/ML & Cloud Computing
- Platform: AWS Free Tier
- Runtime: Python 3.12
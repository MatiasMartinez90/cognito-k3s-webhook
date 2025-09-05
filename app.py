import os
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, Any

import psycopg2
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv

# Load .env file if exists (development only)
load_dotenv()

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'info').upper()
logging.basicConfig(level=getattr(logging, log_level))
logger = logging.getLogger(__name__)

# App configuration from environment variables
APP_TITLE = os.getenv('APP_TITLE', 'Cognito K3s Webhook')
APP_DESCRIPTION = os.getenv('APP_DESCRIPTION', 'FastAPI microservice for handling Cognito PostConfirmation events')
APP_VERSION = os.getenv('APP_VERSION', '1.0.0')

app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION
)

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'postgresql-service.postgresql'),
    'port': int(os.getenv('DB_PORT', '5432')),
    'database': os.getenv('DB_NAME', 'agent'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password')
}

# App configuration
USERS_TABLE = os.getenv('USERS_TABLE', 'users')
DEFAULT_PROVIDER = os.getenv('DEFAULT_PROVIDER', 'google')
TRIGGER_SOURCE = os.getenv('TRIGGER_SOURCE', 'PostConfirmation_ConfirmSignUp')

# Test configuration
TEST_USER_POOL_ID = os.getenv('TEST_USER_POOL_ID', 'us-east-1_MeClCiUAC')
TEST_REGION = os.getenv('TEST_REGION', 'us-east-1')

class CognitoEvent(BaseModel):
    version: str
    region: str
    userPoolId: str
    userName: str
    callerContext: Dict[str, Any]
    triggerSource: str
    request: Dict[str, Any]
    response: Dict[str, Any]

def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

def create_user_in_database(cognito_user_id: str, email: str, name: str, picture_url: str):
    """Create user in PostgreSQL database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert user into database
        insert_query = f"""
        INSERT INTO {USERS_TABLE} (id, cognito_user_id, email, name, picture_url, provider, created_at, updated_at, is_active, onboarding_completed, preferences)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (cognito_user_id) DO UPDATE SET
            email = EXCLUDED.email,
            name = EXCLUDED.name,
            picture_url = EXCLUDED.picture_url,
            updated_at = EXCLUDED.updated_at
        """
        
        user_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        cursor.execute(insert_query, (
            user_id,
            cognito_user_id,
            email,
            name,
            picture_url,
            DEFAULT_PROVIDER,
            now,
            now,
            True,
            False,
            '{}'
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info(f"User created successfully: {email} ({cognito_user_id})")
        return user_id
        
    except Exception as e:
        logger.error(f"Error creating user in database: {e}")
        if conn:
            conn.rollback()
            conn.close()
        raise HTTPException(status_code=500, detail=f"Error creating user: {str(e)}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Cognito K3s Webhook is running",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/health")
async def health_check():
    """Detailed health check including database connectivity"""
    try:
        # Test database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }

@app.post("/cognito-webhook")
async def cognito_post_confirmation(request: Request):
    """Handle Cognito PostConfirmation webhook"""
    try:
        # Get raw request body
        body = await request.body()
        event_data = json.loads(body.decode('utf-8'))
        
        logger.info(f"Received Cognito event: {event_data.get('triggerSource')}")
        
        # Validate this is a PostConfirmation event
        if event_data.get('triggerSource') != TRIGGER_SOURCE:
            logger.warning(f"Ignoring non-PostConfirmation event: {event_data.get('triggerSource')}")
            return {"statusCode": 200, "body": "Event ignored"}
        
        # Extract user information
        cognito_user_id = event_data.get('userName', '')
        user_attributes = event_data.get('request', {}).get('userAttributes', {})
        
        email = user_attributes.get('email', '')
        name = user_attributes.get('name', '')
        picture_url = user_attributes.get('picture', '')
        
        if not email or not cognito_user_id:
            raise HTTPException(status_code=400, detail="Missing required user data")
        
        # Create user in database
        user_id = create_user_in_database(cognito_user_id, email, name, picture_url)
        
        logger.info(f"Successfully processed PostConfirmation for user: {email}")
        
        return {
            "statusCode": 200,
            "body": {
                "message": "User created successfully",
                "user_id": user_id,
                "email": email
            }
        }
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in request: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    except Exception as e:
        logger.error(f"Error processing Cognito event: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/test-webhook")
async def test_webhook():
    """Test endpoint to simulate a Cognito PostConfirmation event"""
    test_event = {
        "version": "1",
        "region": TEST_REGION,
        "userPoolId": TEST_USER_POOL_ID,
        "userName": "test-user-123",
        "triggerSource": TRIGGER_SOURCE,
        "request": {
            "userAttributes": {
                "email": "test@example.com",
                "name": "Test User",
                "picture": "https://example.com/pic.jpg"
            }
        },
        "response": {}
    }
    
    try:
        user_id = create_user_in_database(
            test_event['userName'],
            test_event['request']['userAttributes']['email'],
            test_event['request']['userAttributes']['name'],
            test_event['request']['userAttributes']['picture']
        )
        
        return {
            "message": "Test webhook executed successfully",
            "user_id": user_id,
            "test_data": test_event
        }
    except Exception as e:
        logger.error(f"Test webhook failed: {e}")
        raise HTTPException(status_code=500, detail=f"Test failed: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        log_level="info"
    )
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from google.auth.transport import requests
from google.oauth2 import id_token
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from openai import AzureOpenAI
from dotenv import load_dotenv
import os
import logging
import uvicorn
from google.oauth2 import id_token
from google.auth.transport import requests

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()
GOOGLE_CLIENT_ID = os.environ['GOOGLE_CLIENT_ID']

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    token = credentials.credentials
    try:
        # Verify the token
        logger.info(token)
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), GOOGLE_CLIENT_ID)
        logger.info(idinfo)
        
        logger.info("verified token")
        logger.info(idinfo['iss'])
        logger.info(idinfo['aud'])

        if idinfo['iss'] != 'accounts.google.com':
            raise ValueError('Wrong issuer.')
        logger.info("verified issuer")

        if idinfo['aud'] != GOOGLE_CLIENT_ID:
            raise ValueError('Could not verify audience.')
        logger.info("verified audience")

        return idinfo
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))

@app.get("/")
async def root():
    return {"message": "sanity check"}

class Query(BaseModel):
    prompt: str
    shortcode: int
    temperature: float 

@app.post("/query")
async def query(query: Query, user=Depends(verify_token)):
    # Initialize LLM client
    client = AzureOpenAI(
        api_key = os.environ['OPENAI_API_KEY'],  
        api_version = os.environ['API_VERSION'],
        azure_endpoint = os.environ['azure_endpoint'],
        organization = str(query.shortcode)
    )
    
    response = client.chat.completions.create(
        model = os.environ['model'],
        messages = [
            {"role": "user", "content": query.prompt}
        ],
        temperature = query.temperature,
        stop = None
    )

    response = response.choices[0].message.content
    logger.info(response)
    return response

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5001)


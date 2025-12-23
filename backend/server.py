from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import ConfigDict, Field
from typing import List
import uuid
from datetime import datetime, timezone
import json
import whois
import asyncio
import random
import re

# Import custom modules
from schemas import BrandEvaluationRequest, BrandEvaluationResponse, StatusCheck, StatusCheckCreate
from prompts import SYSTEM_PROMPT
from visibility import check_visibility

# Import Emergent Integration
try:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
except ImportError:
    logging.error("emergentintegrations not found. Ensure it is installed.")
    LlmChat = None

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'rightname_db')]

# Initialize LLM Chat
EMERGENT_KEY = os.environ.get('EMERGENT_LLM_KEY')
if not EMERGENT_KEY:
    logging.warning("EMERGENT_LLM_KEY not found in .env")

# Create the main app
app = FastAPI()

# Router
api_router = APIRouter(prefix="/api")

def check_domain_availability(brand_name: str) -> str:
    domain = f"{brand_name.lower().replace(' ', '')}.com"
    try:
        w = whois.whois(domain)
        if w.domain_name or w.creation_date:
            return f"{domain}: TAKEN (Registered). Use this FACT. Do not say it might be available."
        else:
            return f"{domain}: LIKELY AVAILABLE (No whois record found)."
    except Exception as e:
        error_str = str(e).lower()
        if "no match for" in error_str or "not found" in error_str:
            return f"{domain}: AVAILABLE (No whois record found). Use this FACT."
        else:
            return f"{domain}: CHECK FAILED (Error: {str(e)}). Assume TAKEN to be safe."

def clean_json_string(s):
    """
    Cleans and fixes invalid control characters from JSON string before parsing.
    Properly escapes control characters that break JSON parsing.
    """
    # Remove BOM and other invisible characters
    s = s.replace('\ufeff', '')
    
    # Remove control characters (0-8, 11, 12, 14-31) but keep newlines (\n=10) and tabs (\t=9) and carriage return (\r=13)
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)
    
    return s

def repair_json(s):
    """
    Attempts to repair common JSON syntax errors produced by LLMs.
    """
    # Remove trailing commas before } or ]
    s = re.sub(r',(\s*[}\]])', r'\1', s)
    
    # Fix missing commas between } and " (common LLM error)
    # Pattern: }\n   " or }  " should become },\n   " 
    s = re.sub(r'\}(\s*)"', r'},\1"', s)
    
    # Fix missing commas between ] and " 
    s = re.sub(r'\](\s*)"', r'],\1"', s)
    
    # Fix missing commas between strings: "value"\n  "key"
    s = re.sub(r'"(\s*\n\s*)"([a-zA-Z_])', r'",\1"\2', s)
    
    return s

@api_router.get("/")
async def root():
    return {"message": "RightName API is running"}

@api_router.post("/evaluate", response_model=BrandEvaluationResponse)
async def evaluate_brands(request: BrandEvaluationRequest):
    if LlmChat and EMERGENT_KEY:
        llm_chat = LlmChat(
            api_key=EMERGENT_KEY,
            session_id=f"rightname_{uuid.uuid4()}",
            system_message=SYSTEM_PROMPT
        ).with_model("openai", "gpt-4o")
    else:
        raise HTTPException(status_code=500, detail="LLM Integration not initialized (Check EMERGENT_LLM_KEY)")
    
    # 1. Check Domains
    domain_statuses = []
    for brand in request.brand_names:
        status = check_domain_availability(brand)
        domain_statuses.append(f"- {brand}: {status}")
    domain_context = "\n".join(domain_statuses)

    # 2. Check Visibility
    visibility_data = []
    for brand in request.brand_names:
        vis = check_visibility(brand)
        visibility_data.append(f"BRAND: {brand}")
        visibility_data.append("GOOGLE TOP RESULTS:")
        for res in vis['google'][:10]:
            visibility_data.append(f"  - {res}")
        visibility_data.append("APP STORE RESULTS:")
        for res in vis['apps'][:5]:
            visibility_data.append(f"  - {res}")
        visibility_data.append("---")
    
    visibility_context = "\n".join(visibility_data)
    
    # Construct User Message
    user_prompt = f"""
    Evaluate the following brands:
    Brands: {request.brand_names}
    Category: {request.category}
    Positioning: {request.positioning}
    Market Scope: {request.market_scope}
    Target Countries: {request.countries}

    REAL-TIME DOMAIN AVAILABILITY DATA (DO NOT HALLUCINATE):
    {domain_context}
    INSTRUCTION: Use the above domain data for 'domain_analysis'.

    REAL-TIME SEARCH & APP STORE VISIBILITY DATA:
    {visibility_context}
    INSTRUCTION: Use the above visibility data to populate 'visibility_analysis'.
    - If the top result is a verified brand, open-source framework, or movie title, set 'warning_triggered' to true and explain why in 'warning_reason'.
    - List the top found brands/apps in the JSON fields.
    """
    
    max_retries = 3
    last_error = None
    
    for attempt in range(max_retries):
        try:
            user_message = UserMessage(text=user_prompt)
            response = await llm_chat.send_message(user_message)
            
            content = ""
            if hasattr(response, 'text'):
                content = response.text
            elif isinstance(response, str):
                content = response
            else:
                content = str(response)
            
            # Extract JSON from markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                parts = content.split("```")
                if len(parts) >= 2:
                    content = parts[1]
                    if content.startswith("json"):
                        content = content[4:]
            
            # Sanitization
            content = content.strip()
            
            # Try direct parsing first
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # Apply cleaning and repair
                logging.info("Direct JSON parsing failed, applying cleanup and repair...")
                content = clean_json_string(content)
                content = repair_json(content)
                try:
                    data = json.loads(content)
                except json.JSONDecodeError as je:
                    # Log the problematic content for debugging (context around error)
                    error_pos = je.pos if hasattr(je, 'pos') else 0
                    start = max(0, error_pos - 100)
                    end = min(len(content), error_pos + 100)
                    logging.error(f"JSON Parse Error at position {error_pos}: {je.msg}")
                    logging.error(f"Context around error: ...{repr(content[start:end])}...")
                    raise
            
            evaluation = BrandEvaluationResponse(**data)
            
            doc = evaluation.model_dump()
            doc['created_at'] = datetime.now(timezone.utc).isoformat()
            doc['request'] = request.model_dump()
            await db.evaluations.insert_one(doc)
            
            return evaluation
            
        except Exception as e:
            last_error = e
            error_msg = str(e)
            
            if "Budget has been exceeded" in error_msg:
                logging.error(f"LLM Budget Exceeded: {error_msg}")
                raise HTTPException(status_code=402, detail="Emergent Key Budget Exceeded. Please add credits.")
            
            # Retry on 502/Gateway/Service errors AND JSON/Validation errors
            if any(x in error_msg for x in ["502", "BadGateway", "ServiceUnavailable", "Expecting", "JSON", "validation error", "control character"]):
                wait_time = (2 ** attempt) + random.uniform(0, 1)
                logging.warning(f"LLM Error (Attempt {attempt+1}/{max_retries}): {error_msg}. Retrying in {wait_time:.2f}s...")
                await asyncio.sleep(wait_time)
                continue
            
            logging.error(f"LLM Error: {error_msg}")
            break
            
    raise HTTPException(status_code=500, detail=f"Analysis failed: {str(last_error)}")

# Status Routes
@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    doc = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    await db.status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find({}, {"_id": 0}).to_list(1000)
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    return status_checks

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

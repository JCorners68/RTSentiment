# OpenAPI & Swagger with FastAPI: The ultimate implementation playbook

This implementation plan provides a comprehensive guide to integrating OpenAPI and Swagger tools with a FastAPI backend for an RTSentiment analysis project. By following this plan, you'll create a robust, well-documented API that streamlines collaboration between frontend and backend teams while setting up proper authentication, schema evolution handling, and CI/CD automation.

## Project architecture fundamentals

FastAPI provides built-in OpenAPI/Swagger support, but implementing it correctly requires careful planning. Start with a modular project structure that scales as your API grows:

```
rtsentiment/
├── app/                      # Main application package
│   ├── __init__.py
│   ├── main.py               # Application entry point
│   ├── core/                 # Core modules
│   │   ├── __init__.py
│   │   ├── config.py         # App configuration
│   │   ├── security.py       # Authentication and security
│   ├── api/                  # API routes by version
│   │   ├── __init__.py
│   │   ├── v1/               # Version 1 of the API
│   │   │   ├── __init__.py
│   │   │   ├── api.py        # Main router for v1
│   │   │   └── endpoints/    # Endpoints grouped by resource
│   ├── models/               # Pydantic models
│   ├── schemas/              # SQLAlchemy ORM models
│   ├── services/             # Business logic
├── tests/                    # Tests directory
├── .env                      # Environment variables
├── .spectral.yaml            # OpenAPI validation rules
├── ci/                       # CI/CD configuration files
└── README.md                 # Project documentation
```

## FastAPI core setup with OpenAPI metadata

The main application requires proper OpenAPI configuration to generate comprehensive documentation:

```python
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.api import api_router as api_router_v1
from app.core.config import settings

app = FastAPI(
    title="RTSentiment API",
    description="""
    RTSentiment provides real-time sentiment analysis for text.
    
    ## Features
    
    * **Sentiment Analysis**: Get sentiment scores for text inputs
    * **Batch Processing**: Process multiple texts at once
    * **Historical Analysis**: Track sentiment changes over time
    """,
    version="1.0.0",
    openapi_url="/api/openapi.json",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    terms_of_service="https://example.com/terms/",
    contact={
        "name": "RTSentiment API Support",
        "url": "https://example.com/contact/",
        "email": "api@rtsentiment.com",
    },
    license_info={
        "name": "Apache 2.0",
        "url": "https://www.apache.org/licenses/LICENSE-2.0.html",
    },
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include router with API version prefix
app.include_router(api_router_v1, prefix=settings.API_V1_STR)

# Root endpoint
@app.get("/", tags=["Health"])
async def root():
    """Health check endpoint."""
    return {"status": "healthy", "api_version": "1.0.0"}
```

## Defining data models with Pydantic for rich documentation

Pydantic models are **crucial** for OpenAPI documentation quality. Include detailed field descriptions and examples:

```python
# app/models/sentiment.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class SentimentRequest(BaseModel):
    text: str = Field(
        ..., 
        description="The text to analyze for sentiment",
        min_length=1,
        max_length=10000,
        examples=["I really enjoyed the product, it works great!"]
    )
    language: Optional[str] = Field(
        "en", 
        description="ISO 639-1 language code (defaults to English)",
        examples=["en", "es", "fr"]
    )
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text": "This is a positive statement and I'm happy about it!",
                    "language": "en"
                }
            ]
        }
    }

class SentimentScore(BaseModel):
    positive: float = Field(..., description="Positive sentiment score (0-1)", ge=0, le=1)
    neutral: float = Field(..., description="Neutral sentiment score (0-1)", ge=0, le=1)
    negative: float = Field(..., description="Negative sentiment score (0-1)", ge=0, le=1)
    compound: float = Field(..., description="Compound sentiment score (-1 to 1)", ge=-1, le=1)

class SentimentResponse(BaseModel):
    text: str = Field(..., description="Original text that was analyzed")
    language: str = Field(..., description="Language the text was analyzed in")
    sentiment: SentimentScore = Field(..., description="Sentiment analysis scores")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
```

## Creating endpoints with rich OpenAPI annotations

Each endpoint should include comprehensive OpenAPI annotations that document expected responses and examples:

```python
# app/api/v1/endpoints/sentiment.py
from fastapi import APIRouter, HTTPException, Body
from typing import List, Annotated
from app.models.sentiment import SentimentRequest, SentimentResponse, SentimentScore
from app.services.sentiment_service import SentimentService

router = APIRouter()
sentiment_service = SentimentService()

@router.post(
    "/analyze",
    response_model=SentimentResponse,
    status_code=200,
    summary="Analyze text sentiment",
    description="Analyzes the sentiment of the provided text and returns sentiment scores.",
    responses={
        200: {
            "description": "Successful sentiment analysis",
            "content": {
                "application/json": {
                    "examples": {
                        "positive": {
                            "summary": "Positive sentiment example",
                            "value": {
                                "text": "I love this product! It's amazing.",
                                "language": "en",
                                "sentiment": {
                                    "positive": 0.75,
                                    "neutral": 0.25,
                                    "negative": 0.0,
                                    "compound": 0.85
                                },
                                "processing_time_ms": 12.5
                            }
                        },
                        "negative": {
                            "summary": "Negative sentiment example",
                            "value": {
                                "text": "This is terrible, I'm very disappointed.",
                                "language": "en",
                                "sentiment": {
                                    "positive": 0.0,
                                    "neutral": 0.2,
                                    "negative": 0.8,
                                    "compound": -0.75
                                },
                                "processing_time_ms": 10.2
                            }
                        }
                    }
                }
            }
        },
        400: {"description": "Invalid input"},
        422: {"description": "Validation error"},
        500: {"description": "Internal server error"}
    }
)
async def analyze_sentiment(
    request: Annotated[
        SentimentRequest,
        Body(
            description="Text to analyze for sentiment",
            openapi_examples={
                "simple": {
                    "summary": "Basic sentiment analysis request",
                    "description": "A simple request with just the text to analyze",
                    "value": {"text": "I'm enjoying learning about FastAPI!"}
                },
                "with_language": {
                    "summary": "Sentiment analysis with specific language",
                    "description": "Specify a language for more accurate analysis",
                    "value": {"text": "Me gusta este producto", "language": "es"}
                }
            }
        )
    ]
) -> SentimentResponse:
    """
    Analyze the sentiment of a text string.
    
    Returns sentiment scores including positive, negative, neutral, and compound values.
    """
    try:
        result = sentiment_service.analyze(request.text, request.language)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")
```

## Swagger UI configuration and customization

Enhance the default Swagger UI to improve developer experience:

```python
# app/core/config.py
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "RTSentiment API"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "https://rtsentiment.com"]
    
    # Swagger UI customization
    SWAGGER_UI_PARAMETERS = {
        "deepLinking": True,
        "persistAuthorization": True,
        "displayOperationId": True,
        "defaultModelsExpandDepth": 3,
        "defaultModelExpandDepth": 3,
        "docExpansion": "list",
        "syntaxHighlight.theme": "monokai"
    }
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
```

For deeper customization, replace the default Swagger UI with a custom implementation:

```python
# In app/main.py
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Custom Swagger UI
@app.get("/custom-docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{app.title} - API Documentation",
        oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
        swagger_favicon_url="/static/favicon.png",
        swagger_ui_parameters=settings.SWAGGER_UI_PARAMETERS
    )
```

## Authentication integration with OpenAPI/Swagger

### Setting up Google Sign-In

```python
# app/core/security.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.core.config import settings
import os

# JWT settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", settings.SECRET_KEY)
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2 scheme for OpenAPI
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://accounts.google.com/o/oauth2/auth",
    tokenUrl="https://oauth2.googleapis.com/token",
)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    # Here you would typically look up the user in your database
    # For example purposes, we'll just return the email
    return {"email": email}
```

### Setting up Azure AD B2C

```python
# app/core/azure_auth.py
from fastapi import FastAPI, Depends
from fastapi_azure_auth import SingleTenantAzureAuthorizationCodeBearer
from fastapi_azure_auth.user import User as AzureUser
import os

# Azure AD B2C configuration
TENANT_NAME = os.getenv("TENANT_NAME")
APP_CLIENT_ID = os.getenv("APP_CLIENT_ID")
OPENAPI_CLIENT_ID = os.getenv("OPENAPI_CLIENT_ID")

# OAuth2 scheme for Azure AD B2C
azure_scheme = SingleTenantAzureAuthorizationCodeBearer(
    app_client_id=APP_CLIENT_ID,
    tenant_id=f"{TENANT_NAME}.onmicrosoft.com",
    scopes={
        f"api://{APP_CLIENT_ID}/user_impersonation": "Access API",
    }
)

# Add to FastAPI app
def configure_azure_auth(app: FastAPI):
    app.swagger_ui_init_oauth = {
        "usePkceWithAuthorizationCodeGrant": True,
        "clientId": OPENAPI_CLIENT_ID,
    }

# Use this in your endpoints
async def get_current_azure_user(user: AzureUser = Depends(azure_scheme)):
    return user
```

### Documenting authentication in OpenAPI

Configure custom OpenAPI schema to document authentication methods:

```python
# app/main.py (add to existing code)
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Define security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "GoogleOAuth2": {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": "https://accounts.google.com/o/oauth2/auth",
                    "tokenUrl": "https://oauth2.googleapis.com/token",
                    "scopes": {
                        "openid": "OpenID Connect",
                        "email": "Email access",
                        "profile": "Profile access"
                    }
                }
            }
        },
        "AzureAD": {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": f"https://{TENANT_NAME}.b2clogin.com/{TENANT_NAME}.onmicrosoft.com/B2C_1_signupsignin/oauth2/v2.0/authorize",
                    "tokenUrl": f"https://{TENANT_NAME}.b2clogin.com/{TENANT_NAME}.onmicrosoft.com/B2C_1_signupsignin/oauth2/v2.0/token",
                    "scopes": {
                        f"api://{APP_CLIENT_ID}/user_impersonation": "Access API"
                    }
                }
            }
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    # Apply security requirement to all endpoints
    openapi_schema["security"] = [{"BearerAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

## Database integration with PostgreSQL and Apache Iceberg

### PostgreSQL configuration with SQLAlchemy

```python
# app/schemas/database.py
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
from datetime import datetime

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/sentiment_db")
engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### Database models

```python
# app/schemas/models.py
from app.schemas.database import Base
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime

class SentimentModel(Base):
    __tablename__ = "sentiment_analysis"
    
    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    source = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    sentiment_score = Column(Float, nullable=True, index=True)
    confidence = Column(Float, nullable=True)
    
    # Create indexes for common queries
    __table_args__ = (
        Index('idx_sentiment_source_date', source, created_at),
        Index('idx_sentiment_score_confidence', sentiment_score, confidence),
    )
    
    # Relationship to historical data
    history = relationship("SentimentHistoryModel", back_populates="original", uselist=False)

class SentimentHistoryModel(Base):
    __tablename__ = "sentiment_history"
    
    id = Column(Integer, primary_key=True, index=True)
    original_id = Column(Integer, ForeignKey("sentiment_analysis.id"))
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False)
    sentiment_score = Column(Float, nullable=True)
    
    # Relationship to current data
    original = relationship("SentimentModel", back_populates="history")
```

### Apache Iceberg integration

```python
# app/services/iceberg_service.py
import os
from pyiceberg.catalog import load_catalog
from pyiceberg.schema import Schema
from pyiceberg.types import NestedField, StringType, TimestampType, FloatType, IntegerType
from pyiceberg.partitioning import PartitionSpec, PartitionField
from pyiceberg.transforms import MonthTransform
import pyarrow as pa
from datetime import datetime, timedelta

# Configure PyIceberg
os.environ["PYICEBERG_HOME"] = os.path.join(os.getcwd(), "iceberg_config")

class IcebergService:
    def __init__(self):
        self.catalog = self._get_iceberg_catalog()
        self.table = self._initialize_table()
    
    def _get_iceberg_catalog(self):
        return load_catalog(
            "sentiment_catalog",
            **{
                "type": "rest",
                "uri": os.getenv("ICEBERG_REST_URI", "http://localhost:8181"),
                "warehouse": os.getenv("ICEBERG_WAREHOUSE", "s3://sentiment-warehouse"),
                "s3.endpoint": os.getenv("S3_ENDPOINT", "http://localhost:9000"),
                "s3.access-key-id": os.getenv("AWS_ACCESS_KEY_ID", "minioadmin"),
                "s3.secret-access-key": os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
            }
        )
    
    def _initialize_table(self):
        # Define schema
        schema = Schema(
            NestedField(1, "id", IntegerType(), required=True),
            NestedField(2, "text", StringType(), required=True),
            NestedField(3, "created_at", TimestampType(), required=True),
            NestedField(4, "sentiment_score", FloatType(), required=True),
            NestedField(5, "confidence", FloatType(), required=False),
            NestedField(6, "source", StringType(), required=False)
        )
        
        # Define partitioning by month
        partition_spec = PartitionSpec(
            PartitionField(
                source_id=3,  # created_at field
                field_id=1000,
                transform=MonthTransform(),
                name="month"
            )
        )
        
        # Create table if it doesn't exist
        if "sentiment_history" not in self.catalog.list_tables("default"):
            self.catalog.create_table(
                identifier="default.sentiment_history",
                schema=schema,
                partition_spec=partition_spec
            )
        
        return self.catalog.load_table("default.sentiment_history")
    
    def archive_old_data(self, sentiment_records, days_old=30):
        """Archive older sentiment data to Iceberg"""
        if not sentiment_records:
            return 0
        
        # Convert to Arrow Table
        data = {
            "id": [r.id for r in sentiment_records],
            "text": [r.text for r in sentiment_records],
            "created_at": [r.created_at for r in sentiment_records],
            "sentiment_score": [r.sentiment_score for r in sentiment_records],
            "confidence": [r.confidence for r in sentiment_records],
            "source": [r.source for r in sentiment_records]
        }
        
        arrow_table = pa.Table.from_pydict(data)
        
        # Write to Iceberg
        self.table.append(arrow_table)
        
        return len(sentiment_records)
    
    def get_historical_data(self, year, month):
        """Retrieve historical data from a specific month"""
        # Create filter for the specific month
        filter_expr = f"month = '{year}-{month:02d}'"
        
        # Use Arrow to read filtered data
        return self.table.scan(where=filter_expr).to_arrow()
```

## Schema evolution and API versioning

### Path-based versioning for APIs

Implemented through the project structure with `/api/v1/` and `/api/v2/` paths.

### Backward-compatible schema evolution

```python
# Example of evolving a model while maintaining backward compatibility
# app/models/sentiment_v2.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from app.models.sentiment import SentimentScore

class SentimentScoreV2(SentimentScore):
    # Keep all the original fields for backward compatibility
    # Add new fields
    topics: Optional[List[str]] = Field(
        None,
        description="Detected topics in the text",
    )
    entities: Optional[Dict[str, float]] = Field(
        None,
        description="Named entities detected in text with confidence scores",
    )

class SentimentResponseV2(BaseModel):
    # Keep all required fields from v1
    text: str = Field(..., description="Original text that was analyzed")
    language: str = Field(..., description="Language the text was analyzed in")
    sentiment: SentimentScoreV2 = Field(..., description="Enhanced sentiment analysis scores")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    # Add new optional fields
    sentiment_explanation: Optional[str] = Field(
        None,
        description="Natural language explanation of sentiment analysis",
    )
```

### Alembic for database schema migration

```python
# Install alembic first: pip install alembic
# Initialize: alembic init alembic

# alembic/env.py
from sqlalchemy import engine_from_config, pool
from logging.config import fileConfig
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

config = context.config
fileConfig(config.config_file_name)

from app.schemas.models import Base
target_metadata = Base.metadata

# Create a new migration:
# alembic revision --autogenerate -m "Add confidence field"

# Apply migrations:
# alembic upgrade head
```

### Apache Iceberg schema evolution

```python
# app/services/iceberg_service.py (add to existing class)
def evolve_schema(self):
    """Update the Iceberg schema to include a new field"""
    with self.table.update_schema() as update:
        update.add_column(
            path="sentiment_explanation",
            field_type=StringType()
        )
```

## CI/CD pipeline for documentation automation

### Extract OpenAPI specification script

```python
# tools/extract-openapi.py
#!/usr/bin/env python3
"""
Extract OpenAPI schema from a FastAPI application.
"""

import argparse
import json
import sys
import yaml
from importlib import import_module
from pathlib import Path

def extract_openapi(app_import_string, app_dir=None, output_file=None):
    """
    Extract OpenAPI schema from a FastAPI application.
    
    Args:
        app_import_string: Import string to the FastAPI app (e.g., "main:app")
        app_dir: Directory containing the app (optional)
        output_file: Output file for the OpenAPI schema
    """
    if app_dir:
        sys.path.insert(0, app_dir)
    
    module_name, app_name = app_import_string.split(":", 1)
    module = import_module(module_name)
    app = getattr(module, app_name)
    
    openapi = app.openapi()
    
    if output_file:
        extension = Path(output_file).suffix.lower()
        with open(output_file, "w") as f:
            if extension == ".json":
                json.dump(openapi, f, indent=2)
            else:  # Default to YAML
                yaml.dump(openapi, f, default_flow_style=False)
    else:
        print(json.dumps(openapi, indent=2))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("app", help="App import string. Eg. 'main:app'")
    parser.add_argument("--app-dir", help="Directory containing the app")
    parser.add_argument(
        "--out", help="Output file ending in .json or .yaml", default="openapi.json"
    )
    
    args = parser.parse_args()
    extract_openapi(args.app, args.app_dir, args.out)
```

### OpenAPI validation with Spectral

Create a `.spectral.yaml` file with validation rules:

```yaml
# .spectral.yaml
extends: ["spectral:oas", "spectral:asyncapi"]
rules:
  operation-description:
    description: "Every operation should have a description."
    given: "$.paths.*[?( @property === 'get' || @property === 'put' || @property === 'post' || @property === 'delete' || @property === 'options' || @property === 'head' || @property === 'patch' || @property === 'trace' )]"
    then:
      field: description
      function: truthy
  
  operation-tag-defined:
    description: "Operation tags should be defined in global tags."
    given: "$.paths.*[?( @property === 'get' || @property === 'put' || @property === 'post' || @property === 'delete' || @property === 'options' || @property === 'head' || @property === 'patch' || @property === 'trace' )]"
    then:
      field: tags
      function: schema
      functionOptions:
        schema:
          type: array
          items:
            type: string
```

### GitHub Actions CI/CD Configuration

```yaml
# .github/workflows/api-docs.yml
name: API Documentation

on:
  push:
    branches: [ main ]
    paths:
      - 'app/**/*.py'
      - 'requirements.txt'
  pull_request:
    branches: [ main ]
    paths:
      - 'app/**/*.py'
      - 'requirements.txt'

jobs:
  build-and-deploy-docs:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest
      
      - name: Run API server in background
        run: |
          uvicorn app.main:app --host 127.0.0.1 --port 8000 &
          sleep 5  # Give the server time to start
      
      - name: Extract OpenAPI specification
        run: |
          python tools/extract-openapi.py "app.main:app" --out openapi.json
      
      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
      
      - name: Install Spectral
        run: npm install -g @stoplight/spectral-cli
      
      - name: Lint OpenAPI specification
        run: spectral lint openapi.json --ruleset .spectral.yaml
      
      - name: Install Redocly CLI
        run: npm install -g @redocly/cli
      
      - name: Generate API documentation
        run: redocly build-docs openapi.json -o docs/
      
      - name: Test examples
        run: python tools/test_examples.py openapi.json http://localhost:8000
      
      - name: Deploy to GitHub Pages
        if: github.ref == 'refs/heads/main'
        uses: JamesIves/github-pages-deploy-action@v4
        with:
          folder: docs
          branch: gh-pages
```

### Script for testing API examples

```python
# tools/test_examples.py
import json
import sys
import requests
import yaml

def test_openapi_examples(openapi_file, base_url):
    # Load OpenAPI spec
    with open(openapi_file) as f:
        if openapi_file.endswith('.yaml') or openapi_file.endswith('.yml'):
            spec = yaml.safe_load(f)
        else:
            spec = json.load(f)
    
    failures = []
    
    # Test paths and operations
    for path, path_item in spec.get('paths', {}).items():
        for method, operation in path_item.items():
            if method not in ['get', 'post', 'put', 'delete', 'patch']:
                continue
            
            # Find examples in request body
            request_body = operation.get('requestBody', {})
            request_content = request_body.get('content', {})
            
            for media_type, media_obj in request_content.items():
                if 'example' in media_obj:
                    example_data = media_obj['example']
                    api_path = base_url + path
                    
                    # Replace path parameters
                    for param in operation.get('parameters', []):
                        if param.get('in') == 'path' and 'example' in param:
                            placeholder = f"{{{param['name']}}}"
                            api_path = api_path.replace(placeholder, str(param['example']))
                    
                    # Make the request
                    try:
                        if method == 'get':
                            response = requests.get(api_path)
                        elif method == 'post':
                            response = requests.post(api_path, json=example_data)
                        elif method == 'put':
                            response = requests.put(api_path, json=example_data)
                        elif method == 'delete':
                            response = requests.delete(api_path)
                        elif method == 'patch':
                            response = requests.patch(api_path, json=example_data)
                        
                        if response.status_code >= 400:
                            failures.append(f"Failed {method.upper()} {api_path}: {response.status_code}")
                    except Exception as e:
                        failures.append(f"Error testing {method.upper()} {api_path}: {str(e)}")
    
    return failures

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python test_examples.py openapi.json http://localhost:8000")
        sys.exit(1)
    
    failures = test_openapi_examples(sys.argv[1], sys.argv[2])
    
    if failures:
        print("Example tests failed:")
        for failure in failures:
            print(f"- {failure}")
        sys.exit(1)
    else:
        print("All example tests passed!")
```

## Local development workflow configuration

Set up a Taskfile to standardize development tasks:

```yaml
# Taskfile.yml
version: '3'

tasks:
  install:
    desc: Install dependencies
    cmds:
      - pip install -r requirements.txt
      - npm install -g @stoplight/spectral-cli @redocly/cli

  run:
    desc: Run the FastAPI application
    cmds:
      - uvicorn app.main:app --reload

  extract-openapi:
    desc: Extract OpenAPI specification
    cmds:
      - python tools/extract-openapi.py "app.main:app" --out openapi.json

  lint-openapi:
    desc: Validate OpenAPI specification
    deps: [extract-openapi]
    cmds:
      - spectral lint openapi.json --ruleset .spectral.yaml

  generate-docs:
    desc: Generate API documentation
    deps: [extract-openapi]
    cmds:
      - mkdir -p docs
      - redocly build-docs openapi.json -o docs/

  test:
    desc: Run tests
    cmds:
      - pytest

  migrate:
    desc: Run database migrations
    cmds:
      - alembic upgrade head

  all:
    desc: Run all tasks
    deps: [install, lint-openapi, generate-docs, test, migrate]
```

## Best practices for frontend/backend collaboration

1. **Early API mockups**: Create OpenAPI specifications before implementation to get frontend team feedback.

2. **Shared type definitions**: Generate TypeScript types from OpenAPI schemas for frontend:

```bash
# Generate TypeScript interface definitions
npx openapi-typescript openapi.json -o src/types/api.ts
```

3. **Interactive documentation**: Maintain up-to-date Swagger UI documentation with realistic examples.

4. **Example request/response pairs**: Include example request/response pairs in OpenAPI documentation.

5. **Real-time collaboration**: Use Swagger Editor for collaborative API design sessions.

6. **Versioned documentation**: Maintain versioned documentation with changelog between versions.

7. **Automated testing**: Test frontend against documentation examples to catch integration issues early.

## Conclusion

This implementation plan provides a comprehensive approach to integrating OpenAPI and Swagger tools with FastAPI for a RTSentiment analysis project. The plan follows modern best practices for API documentation, authentication, database integration, schema evolution, and CI/CD automation.

By implementing these patterns, you'll create a robust, well-documented API that streamlines collaboration between frontend and backend teams while ensuring your API documentation stays current as your codebase evolves. The PostgreSQL and Apache Iceberg integration provides a solid foundation for handling real-time sentiment analysis with effective historical data management.

Remember that good documentation is an ongoing process. Continuously improve your OpenAPI specifications, keep examples up-to-date, and use the CI/CD pipeline to ensure documentation quality as your API evolves.
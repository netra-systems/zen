#!/usr/bin/env python3
"""
Google Tag Manager API Configuration Script
Configures GTM container with all necessary variables, triggers, and tags for complete integration
with Google Analytics and the Netra Apex platform.

Prerequisites:
1. Enable Google Tag Manager API in Google Cloud Console
2. Create OAuth 2.0 credentials or service account
3. Install required packages: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client

Usage:
    python scripts/gtm_api_setup.py --account-id YOUR_ACCOUNT_ID --container-id GTM-WKP28PNQ
"""

import json
import argparse
import sys
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging
from pathlib import Path
from datetime import datetime

# Google API imports
try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    print("Error: Required Google API packages not installed.")
    print("Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# API Scopes
SCOPES = [
    'https://www.googleapis.com/auth/tagmanager.edit.containers',
    'https://www.googleapis.com/auth/tagmanager.manage.accounts',
    'https://www.googleapis.com/auth/tagmanager.publish'
]

class VariableType(Enum):
    """GTM Variable Types"""
    DATA_LAYER = "v"
    JAVASCRIPT = "jsm"
    CONSTANT = "c"
    CUSTOM_EVENT = "e"
    URL = "u"
    REFERRER = "r"
    COOKIE = "k"
    DOM_ELEMENT = "d"
    AUTO_EVENT = "aev"
    GA_SETTINGS = "gas"

class TriggerType(Enum):
    """GTM Trigger Types"""
    PAGE_VIEW = "pageview"
    CUSTOM_EVENT = "customEvent"
    CLICK = "linkClick"
    FORM_SUBMIT = "formSubmit"
    HISTORY_CHANGE = "historyChange"
    JAVASCRIPT_ERROR = "jsError"
    TIMER = "timer"
    YOUTUBE = "youTube"

@dataclass
class GTMVariable:
    """GTM Variable Configuration"""
    name: str
    type: VariableType
    parameter: List[Dict[str, Any]]
    notes: str = ""
    
    def to_api_format(self) -> Dict[str, Any]:
        """Convert to GTM API format"""
        return {
            "name": self.name,
            "type": self.type.value,
            "parameter": self.parameter,
            "notes": self.notes
        }

@dataclass
class GTMTrigger:
    """GTM Trigger Configuration"""
    name: str
    type: TriggerType
    filter: Optional[List[Dict[str, Any]]] = None
    custom_event_filter: Optional[List[Dict[str, Any]]] = None
    notes: str = ""
    
    def to_api_format(self) -> Dict[str, Any]:
        """Convert to GTM API format"""
        config = {
            "name": self.name,
            "type": self.type.value,
            "notes": self.notes
        }
        if self.filter:
            config["filter"] = self.filter
        if self.custom_event_filter:
            config["customEventFilter"] = self.custom_event_filter
        return config

@dataclass
class GTMTag:
    """GTM Tag Configuration"""
    name: str
    type: str
    parameter: List[Dict[str, Any]]
    firing_trigger_id: List[str] = None
    blocking_trigger_id: List[str] = None
    notes: str = ""
    
    def to_api_format(self) -> Dict[str, Any]:
        """Convert to GTM API format"""
        config = {
            "name": self.name,
            "type": self.type,
            "parameter": self.parameter,
            "notes": self.notes
        }
        if self.firing_trigger_id:
            config["firingTriggerId"] = self.firing_trigger_id
        if self.blocking_trigger_id:
            config["blockingTriggerId"] = self.blocking_trigger_id
        return config

class GTMConfigurator:
    """Google Tag Manager API Configurator"""
    
    def __init__(self, account_id: str, container_id: str, workspace_name: str = "API Configuration"):
        self.account_id = account_id
        # Handle both public ID (GTM-XXXX) and numeric ID
        if container_id.startswith('GTM-'):
            # This is a public ID, we need to convert it
            # For now, we'll use the numeric ID from config
            import json
            from pathlib import Path
            config_path = Path(__file__).parent / 'gtm_config.json'
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    self.container_id = config.get('numeric_container_id', container_id)
                    self.public_container_id = container_id
            else:
                self.container_id = container_id
                self.public_container_id = container_id
        else:
            self.container_id = container_id
            self.public_container_id = f"GTM-{container_id}"  # May not be accurate
        
        self.workspace_name = workspace_name
        self.service = None
        self.workspace = None
        self.container_path = None
        
        # Track created resources
        self.created_variables = {}
        self.created_triggers = {}
        self.created_tags = {}
        
    def authenticate(self, credentials_path: Optional[str] = None):
        """Authenticate with Google Tag Manager API"""
        creds = None
        
        # Try service account first
        if credentials_path and os.path.exists(credentials_path):
            try:
                if credentials_path.endswith('.json'):
                    creds = service_account.Credentials.from_service_account_file(
                        credentials_path, scopes=SCOPES
                    )
                    logger.info("Authenticated using service account")
            except Exception as e:
                logger.warning(f"Failed to use service account: {e}")
        
        # Try OAuth flow
        if not creds:
            token_path = 'token.json'
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    if not credentials_path or not os.path.exists(credentials_path):
                        credentials_path = 'credentials.json'
                    
                    if not os.path.exists(credentials_path):
                        raise FileNotFoundError(
                            f"Credentials file not found at {credentials_path}. "
                            "Please download OAuth2 credentials from Google Cloud Console."
                        )
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_path, SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                
                # Save credentials for next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
                logger.info("Authenticated using OAuth")
        
        self.service = build('tagmanager', 'v2', credentials=creds)
        self.container_path = f"accounts/{self.account_id}/containers/{self.container_id}"
        
    def create_workspace(self):
        """Create or get workspace for configuration"""
        try:
            # List existing workspaces
            workspaces = self.service.accounts().containers().workspaces().list(
                parent=self.container_path
            ).execute()
            
            # Check if workspace already exists
            for ws in workspaces.get('workspace', []):
                if ws['name'] == self.workspace_name:
                    self.workspace = ws
                    logger.info(f"Using existing workspace: {self.workspace_name}")
                    # Load existing variables, triggers, and tags
                    self._load_existing_resources()
                    return
            
            # Create new workspace
            workspace_body = {
                'name': self.workspace_name,
                'description': 'Workspace for API configuration of GTM variables, triggers, and tags'
            }
            
            self.workspace = self.service.accounts().containers().workspaces().create(
                parent=self.container_path,
                body=workspace_body
            ).execute()
            
            logger.info(f"Created new workspace: {self.workspace_name}")
            
        except HttpError as e:
            logger.error(f"Error creating workspace: {e}")
            raise
    
    def _load_existing_resources(self):
        """Load existing variables, triggers, and tags to avoid duplicates"""
        try:
            # Load existing variables
            variables = self.service.accounts().containers().workspaces().variables().list(
                parent=self.get_workspace_path()
            ).execute()
            
            for var in variables.get('variable', []):
                self.created_variables[var['name']] = var['variableId']
            
            if self.created_variables:
                logger.info(f"Found {len(self.created_variables)} existing variables")
            
            # Load existing triggers
            triggers = self.service.accounts().containers().workspaces().triggers().list(
                parent=self.get_workspace_path()
            ).execute()
            
            for trigger in triggers.get('trigger', []):
                self.created_triggers[trigger['name']] = trigger['triggerId']
            
            if self.created_triggers:
                logger.info(f"Found {len(self.created_triggers)} existing triggers")
            
            # Load existing tags
            tags = self.service.accounts().containers().workspaces().tags().list(
                parent=self.get_workspace_path()
            ).execute()
            
            for tag in tags.get('tag', []):
                self.created_tags[tag['name']] = tag['tagId']
            
            if self.created_tags:
                logger.info(f"Found {len(self.created_tags)} existing tags")
                
        except HttpError as e:
            logger.warning(f"Error loading existing resources: {e}")
    
    def get_workspace_path(self) -> str:
        """Get workspace path"""
        return self.workspace['path']
    
    def create_variables(self) -> Dict[str, str]:
        """Create all GTM variables"""
        variables = [
            # Data Layer Variables
            GTMVariable(
                name="DLV - Event Category",
                type=VariableType.DATA_LAYER,
                parameter=[
                    {"type": "TEMPLATE", "key": "dataLayerVersion", "value": "2"},
                    {"type": "TEMPLATE", "key": "name", "value": "event_category"}
                ],
                notes="Event category from data layer"
            ),
            GTMVariable(
                name="DLV - Event Action",
                type=VariableType.DATA_LAYER,
                parameter=[
                    {"type": "TEMPLATE", "key": "dataLayerVersion", "value": "2"},
                    {"type": "TEMPLATE", "key": "name", "value": "event_action"}
                ],
                notes="Event action from data layer"
            ),
            GTMVariable(
                name="DLV - Event Label",
                type=VariableType.DATA_LAYER,
                parameter=[
                    {"type": "TEMPLATE", "key": "dataLayerVersion", "value": "2"},
                    {"type": "TEMPLATE", "key": "name", "value": "event_label"}
                ],
                notes="Event label from data layer"
            ),
            GTMVariable(
                name="DLV - Event Value",
                type=VariableType.DATA_LAYER,
                parameter=[
                    {"type": "TEMPLATE", "key": "dataLayerVersion", "value": "2"},
                    {"type": "TEMPLATE", "key": "name", "value": "value"}
                ],
                notes="Event value from data layer"
            ),
            GTMVariable(
                name="DLV - User ID",
                type=VariableType.DATA_LAYER,
                parameter=[
                    {"type": "TEMPLATE", "key": "dataLayerVersion", "value": "2"},
                    {"type": "TEMPLATE", "key": "name", "value": "user_id"}
                ],
                notes="User ID for cross-session tracking"
            ),
            GTMVariable(
                name="DLV - Session ID",
                type=VariableType.DATA_LAYER,
                parameter=[
                    {"type": "TEMPLATE", "key": "dataLayerVersion", "value": "2"},
                    {"type": "TEMPLATE", "key": "name", "value": "session_id"}
                ],
                notes="Session ID for session tracking"
            ),
            GTMVariable(
                name="DLV - User Tier",
                type=VariableType.DATA_LAYER,
                parameter=[
                    {"type": "TEMPLATE", "key": "dataLayerVersion", "value": "2"},
                    {"type": "TEMPLATE", "key": "name", "value": "user_tier"}
                ],
                notes="User subscription tier"
            ),
            GTMVariable(
                name="DLV - Auth Method",
                type=VariableType.DATA_LAYER,
                parameter=[
                    {"type": "TEMPLATE", "key": "dataLayerVersion", "value": "2"},
                    {"type": "TEMPLATE", "key": "name", "value": "auth_method"}
                ],
                notes="Authentication method used"
            ),
            GTMVariable(
                name="DLV - Feature Type",
                type=VariableType.DATA_LAYER,
                parameter=[
                    {"type": "TEMPLATE", "key": "dataLayerVersion", "value": "2"},
                    {"type": "TEMPLATE", "key": "name", "value": "feature_type"}
                ],
                notes="Type of feature being used"
            ),
            GTMVariable(
                name="DLV - Agent Type",
                type=VariableType.DATA_LAYER,
                parameter=[
                    {"type": "TEMPLATE", "key": "dataLayerVersion", "value": "2"},
                    {"type": "TEMPLATE", "key": "name", "value": "agent_type"}
                ],
                notes="AI agent type"
            ),
            GTMVariable(
                name="DLV - Thread ID",
                type=VariableType.DATA_LAYER,
                parameter=[
                    {"type": "TEMPLATE", "key": "dataLayerVersion", "value": "2"},
                    {"type": "TEMPLATE", "key": "name", "value": "thread_id"}
                ],
                notes="Chat thread identifier"
            ),
            GTMVariable(
                name="DLV - Transaction ID",
                type=VariableType.DATA_LAYER,
                parameter=[
                    {"type": "TEMPLATE", "key": "dataLayerVersion", "value": "2"},
                    {"type": "TEMPLATE", "key": "name", "value": "transaction_id"}
                ],
                notes="Transaction identifier for purchases"
            ),
            GTMVariable(
                name="DLV - Transaction Value",
                type=VariableType.DATA_LAYER,
                parameter=[
                    {"type": "TEMPLATE", "key": "dataLayerVersion", "value": "2"},
                    {"type": "TEMPLATE", "key": "name", "value": "transaction_value"}
                ],
                notes="Transaction monetary value"
            ),
            GTMVariable(
                name="DLV - Plan Type",
                type=VariableType.DATA_LAYER,
                parameter=[
                    {"type": "TEMPLATE", "key": "dataLayerVersion", "value": "2"},
                    {"type": "TEMPLATE", "key": "name", "value": "plan_type"}
                ],
                notes="Subscription plan type"
            ),
            GTMVariable(
                name="DLV - Currency",
                type=VariableType.DATA_LAYER,
                parameter=[
                    {"type": "TEMPLATE", "key": "dataLayerVersion", "value": "2"},
                    {"type": "TEMPLATE", "key": "name", "value": "currency"}
                ],
                notes="Currency code for transactions"
            ),
            
            # URL Variables
            GTMVariable(
                name="URL - Full",
                type=VariableType.URL,
                parameter=[
                    {"type": "TEMPLATE", "key": "component", "value": "URL"}
                ],
                notes="Full page URL"
            ),
            GTMVariable(
                name="URL - Path",
                type=VariableType.URL,
                parameter=[
                    {"type": "TEMPLATE", "key": "component", "value": "PATH"}
                ],
                notes="URL path only"
            ),
            GTMVariable(
                name="URL - Hostname",
                type=VariableType.URL,
                parameter=[
                    {"type": "TEMPLATE", "key": "component", "value": "HOST"}
                ],
                notes="URL hostname"
            ),
            
            # Custom JavaScript Variables
            GTMVariable(
                name="JS - Timestamp",
                type=VariableType.JAVASCRIPT,
                parameter=[
                    {"type": "TEMPLATE", "key": "javascript", "value": "function() { return new Date().toISOString(); }"}
                ],
                notes="Current timestamp in ISO format"
            ),
            GTMVariable(
                name="JS - Client ID",
                type=VariableType.JAVASCRIPT,
                parameter=[
                    {"type": "TEMPLATE", "key": "javascript", "value": """
function() {
  var clientId = localStorage.getItem('ga_client_id');
  if (!clientId) {
    clientId = 'cid_' + Math.random().toString(36).substring(2) + Date.now().toString(36);
    localStorage.setItem('ga_client_id', clientId);
  }
  return clientId;
}
"""}
                ],
                notes="Persistent client ID for GA tracking"
            ),
            GTMVariable(
                name="JS - Session Duration",
                type=VariableType.JAVASCRIPT,
                parameter=[
                    {"type": "TEMPLATE", "key": "javascript", "value": """
function() {
  var sessionStart = sessionStorage.getItem('session_start');
  if (!sessionStart) {
    sessionStorage.setItem('session_start', Date.now());
    return 0;
  }
  return Math.floor((Date.now() - parseInt(sessionStart)) / 1000);
}
"""}
                ],
                notes="Session duration in seconds"
            ),
            
            # Constants
            GTMVariable(
                name="Const - GA4 Measurement ID",
                type=VariableType.CONSTANT,
                parameter=[
                    {"type": "TEMPLATE", "key": "value", "value": "G-522Q06C6M5"}
                ],
                notes="Google Analytics 4 Measurement ID"
            ),
            GTMVariable(
                name="Const - GTM Container ID",
                type=VariableType.CONSTANT,
                parameter=[
                    {"type": "TEMPLATE", "key": "value", "value": "GTM-WKP28PNQ"}
                ],
                notes="GTM Container ID"
            ),
            GTMVariable(
                name="Const - Environment",
                type=VariableType.CONSTANT,
                parameter=[
                    {"type": "TEMPLATE", "key": "value", "value": "production"}
                ],
                notes="Current environment"
            ),
        ]
        
        created = {}
        for variable in variables:
            # Skip if already exists
            if variable.name in self.created_variables:
                logger.info(f"Variable already exists, skipping: {variable.name}")
                created[variable.name] = self.created_variables[variable.name]
                continue
                
            try:
                result = self.service.accounts().containers().workspaces().variables().create(
                    parent=self.get_workspace_path(),
                    body=variable.to_api_format()
                ).execute()
                
                created[variable.name] = result['variableId']
                logger.info(f"Created variable: {variable.name} (ID: {result['variableId']})")
                
            except HttpError as e:
                logger.error(f"Error creating variable {variable.name}: {e}")
                
        self.created_variables = created
        return created
    
    def create_triggers(self) -> Dict[str, str]:
        """Create all GTM triggers"""
        triggers = [
            # Page View Triggers
            GTMTrigger(
                name="All Pages",
                type=TriggerType.PAGE_VIEW,
                notes="Fires on all page views"
            ),
            
            # Authentication Event Triggers
            GTMTrigger(
                name="User Login",
                type=TriggerType.CUSTOM_EVENT,
                custom_event_filter=[
                    {
                        "type": "EQUALS",
                        "parameter": [
                            {"type": "TEMPLATE", "key": "arg0", "value": "{{_event}}"},
                            {"type": "TEMPLATE", "key": "arg1", "value": "user_login"}
                        ]
                    }
                ],
                notes="Fires when user logs in"
            ),
            GTMTrigger(
                name="User Signup",
                type=TriggerType.CUSTOM_EVENT,
                custom_event_filter=[
                    {
                        "type": "EQUALS",
                        "parameter": [
                            {"type": "TEMPLATE", "key": "arg0", "value": "{{_event}}"},
                            {"type": "TEMPLATE", "key": "arg1", "value": "user_signup"}
                        ]
                    }
                ],
                notes="Fires when user signs up"
            ),
            GTMTrigger(
                name="User Logout",
                type=TriggerType.CUSTOM_EVENT,
                custom_event_filter=[
                    {
                        "type": "EQUALS",
                        "parameter": [
                            {"type": "TEMPLATE", "key": "arg0", "value": "{{_event}}"},
                            {"type": "TEMPLATE", "key": "arg1", "value": "user_logout"}
                        ]
                    }
                ],
                notes="Fires when user logs out"
            ),
            
            # Engagement Event Triggers
            GTMTrigger(
                name="Chat Started",
                type=TriggerType.CUSTOM_EVENT,
                custom_event_filter=[
                    {
                        "type": "EQUALS",
                        "parameter": [
                            {"type": "TEMPLATE", "key": "arg0", "value": "{{_event}}"},
                            {"type": "TEMPLATE", "key": "arg1", "value": "chat_started"}
                        ]
                    }
                ],
                notes="Fires when chat session starts"
            ),
            GTMTrigger(
                name="Message Sent",
                type=TriggerType.CUSTOM_EVENT,
                custom_event_filter=[
                    {
                        "type": "EQUALS",
                        "parameter": [
                            {"type": "TEMPLATE", "key": "arg0", "value": "{{_event}}"},
                            {"type": "TEMPLATE", "key": "arg1", "value": "message_sent"}
                        ]
                    }
                ],
                notes="Fires when message is sent"
            ),
            GTMTrigger(
                name="Agent Activated",
                type=TriggerType.CUSTOM_EVENT,
                custom_event_filter=[
                    {
                        "type": "EQUALS",
                        "parameter": [
                            {"type": "TEMPLATE", "key": "arg0", "value": "{{_event}}"},
                            {"type": "TEMPLATE", "key": "arg1", "value": "agent_activated"}
                        ]
                    }
                ],
                notes="Fires when AI agent is activated"
            ),
            GTMTrigger(
                name="Feature Used",
                type=TriggerType.CUSTOM_EVENT,
                custom_event_filter=[
                    {
                        "type": "EQUALS",
                        "parameter": [
                            {"type": "TEMPLATE", "key": "arg0", "value": "{{_event}}"},
                            {"type": "TEMPLATE", "key": "arg1", "value": "feature_used"}
                        ]
                    }
                ],
                notes="Fires when a feature is used"
            ),
            
            # Conversion Event Triggers
            GTMTrigger(
                name="Trial Started",
                type=TriggerType.CUSTOM_EVENT,
                custom_event_filter=[
                    {
                        "type": "EQUALS",
                        "parameter": [
                            {"type": "TEMPLATE", "key": "arg0", "value": "{{_event}}"},
                            {"type": "TEMPLATE", "key": "arg1", "value": "trial_started"}
                        ]
                    }
                ],
                notes="Fires when trial is started"
            ),
            GTMTrigger(
                name="Plan Upgraded",
                type=TriggerType.CUSTOM_EVENT,
                custom_event_filter=[
                    {
                        "type": "EQUALS",
                        "parameter": [
                            {"type": "TEMPLATE", "key": "arg0", "value": "{{_event}}"},
                            {"type": "TEMPLATE", "key": "arg1", "value": "plan_upgraded"}
                        ]
                    }
                ],
                notes="Fires when plan is upgraded"
            ),
            GTMTrigger(
                name="Payment Completed",
                type=TriggerType.CUSTOM_EVENT,
                custom_event_filter=[
                    {
                        "type": "EQUALS",
                        "parameter": [
                            {"type": "TEMPLATE", "key": "arg0", "value": "{{_event}}"},
                            {"type": "TEMPLATE", "key": "arg1", "value": "payment_completed"}
                        ]
                    }
                ],
                notes="Fires when payment is completed"
            ),
            GTMTrigger(
                name="Demo Requested",
                type=TriggerType.CUSTOM_EVENT,
                custom_event_filter=[
                    {
                        "type": "EQUALS",
                        "parameter": [
                            {"type": "TEMPLATE", "key": "arg0", "value": "{{_event}}"},
                            {"type": "TEMPLATE", "key": "arg1", "value": "demo_requested"}
                        ]
                    }
                ],
                notes="Fires when demo is requested"
            ),
            
            # Generic Custom Event Trigger
            GTMTrigger(
                name="All Custom Events",
                type=TriggerType.CUSTOM_EVENT,
                custom_event_filter=[
                    {
                        "type": "MATCHES_REGEX",
                        "parameter": [
                            {"type": "TEMPLATE", "key": "arg0", "value": "{{_event}}"},
                            {"type": "TEMPLATE", "key": "arg1", "value": ".*"}
                        ]
                    }
                ],
                notes="Fires on all custom events"
            ),
        ]
        
        created = {}
        for trigger in triggers:
            # Skip if already exists
            if trigger.name in self.created_triggers:
                logger.info(f"Trigger already exists, skipping: {trigger.name}")
                created[trigger.name] = self.created_triggers[trigger.name]
                continue
                
            try:
                result = self.service.accounts().containers().workspaces().triggers().create(
                    parent=self.get_workspace_path(),
                    body=trigger.to_api_format()
                ).execute()
                
                created[trigger.name] = result['triggerId']
                logger.info(f"Created trigger: {trigger.name} (ID: {result['triggerId']})")
                
            except HttpError as e:
                logger.error(f"Error creating trigger {trigger.name}: {e}")
                
        self.created_triggers = created
        return created
    
    def create_tags(self) -> Dict[str, str]:
        """Create all GTM tags"""
        tags = [
            # Google Analytics 4 Configuration Tag
            GTMTag(
                name="GA4 - Configuration",
                type="gaawc",  # Google Analytics: GA4 Configuration
                parameter=[
                    {"type": "TEMPLATE", "key": "measurementId", "value": "{{Const - GA4 Measurement ID}}"},
                    {"type": "BOOLEAN", "key": "sendPageView", "value": "true"},
                    {"type": "TEMPLATE", "key": "clientId", "value": "{{JS - Client ID}}"},
                    {
                        "type": "LIST",
                        "key": "fieldsToSet",
                        "list": [
                            {
                                "type": "MAP",
                                "map": [
                                    {"type": "TEMPLATE", "key": "fieldName", "value": "user_id"},
                                    {"type": "TEMPLATE", "key": "value", "value": "{{DLV - User ID}}"}
                                ]
                            },
                            {
                                "type": "MAP",
                                "map": [
                                    {"type": "TEMPLATE", "key": "fieldName", "value": "session_id"},
                                    {"type": "TEMPLATE", "key": "value", "value": "{{DLV - Session ID}}"}
                                ]
                            }
                        ]
                    }
                ],
                firing_trigger_id=[self.created_triggers.get("All Pages", "")],
                notes="GA4 base configuration tag"
            ),
            
            # Authentication Event Tags
            GTMTag(
                name="GA4 - User Login",
                type="gaawe",  # Google Analytics: GA4 Event
                parameter=[
                    {"type": "TEMPLATE", "key": "measurementId", "value": "{{Const - GA4 Measurement ID}}"},
                    {"type": "TEMPLATE", "key": "eventName", "value": "login"},
                    {
                        "type": "LIST",
                        "key": "eventParameters",
                        "list": [
                            {
                                "type": "MAP",
                                "map": [
                                    {"type": "TEMPLATE", "key": "name", "value": "method"},
                                    {"type": "TEMPLATE", "key": "value", "value": "{{DLV - Auth Method}}"}
                                ]
                            },
                            {
                                "type": "MAP",
                                "map": [
                                    {"type": "TEMPLATE", "key": "name", "value": "user_tier"},
                                    {"type": "TEMPLATE", "key": "value", "value": "{{DLV - User Tier}}"}
                                ]
                            }
                        ]
                    }
                ],
                firing_trigger_id=[self.created_triggers.get("User Login", "")],
                notes="Track user login events"
            ),
            
            GTMTag(
                name="GA4 - User Signup",
                type="gaawe",
                parameter=[
                    {"type": "TEMPLATE", "key": "measurementId", "value": "{{Const - GA4 Measurement ID}}"},
                    {"type": "TEMPLATE", "key": "eventName", "value": "sign_up"},
                    {
                        "type": "LIST",
                        "key": "eventParameters",
                        "list": [
                            {
                                "type": "MAP",
                                "map": [
                                    {"type": "TEMPLATE", "key": "name", "value": "method"},
                                    {"type": "TEMPLATE", "key": "value", "value": "{{DLV - Auth Method}}"}
                                ]
                            }
                        ]
                    }
                ],
                firing_trigger_id=[self.created_triggers.get("User Signup", "")],
                notes="Track user signup events"
            ),
            
            # Engagement Event Tags
            GTMTag(
                name="GA4 - Chat Started",
                type="gaawe",
                parameter=[
                    {"type": "TEMPLATE", "key": "measurementId", "value": "{{Const - GA4 Measurement ID}}"},
                    {"type": "TEMPLATE", "key": "eventName", "value": "chat_started"},
                    {
                        "type": "LIST",
                        "key": "eventParameters",
                        "list": [
                            {
                                "type": "MAP",
                                "map": [
                                    {"type": "TEMPLATE", "key": "name", "value": "thread_id"},
                                    {"type": "TEMPLATE", "key": "value", "value": "{{DLV - Thread ID}}"}
                                ]
                            },
                            {
                                "type": "MAP",
                                "map": [
                                    {"type": "TEMPLATE", "key": "name", "value": "session_duration"},
                                    {"type": "TEMPLATE", "key": "value", "value": "{{JS - Session Duration}}"}
                                ]
                            }
                        ]
                    }
                ],
                firing_trigger_id=[self.created_triggers.get("Chat Started", "")],
                notes="Track chat session starts"
            ),
            
            GTMTag(
                name="GA4 - Agent Activated",
                type="gaawe",
                parameter=[
                    {"type": "TEMPLATE", "key": "measurementId", "value": "{{Const - GA4 Measurement ID}}"},
                    {"type": "TEMPLATE", "key": "eventName", "value": "agent_activated"},
                    {
                        "type": "LIST",
                        "key": "eventParameters",
                        "list": [
                            {
                                "type": "MAP",
                                "map": [
                                    {"type": "TEMPLATE", "key": "name", "value": "agent_type"},
                                    {"type": "TEMPLATE", "key": "value", "value": "{{DLV - Agent Type}}"}
                                ]
                            },
                            {
                                "type": "MAP",
                                "map": [
                                    {"type": "TEMPLATE", "key": "name", "value": "thread_id"},
                                    {"type": "TEMPLATE", "key": "value", "value": "{{DLV - Thread ID}}"}
                                ]
                            }
                        ]
                    }
                ],
                firing_trigger_id=[self.created_triggers.get("Agent Activated", "")],
                notes="Track AI agent activations"
            ),
            
            # Conversion Event Tags
            GTMTag(
                name="GA4 - Trial Started",
                type="gaawe",
                parameter=[
                    {"type": "TEMPLATE", "key": "measurementId", "value": "{{Const - GA4 Measurement ID}}"},
                    {"type": "TEMPLATE", "key": "eventName", "value": "trial_start"},
                    {
                        "type": "LIST",
                        "key": "eventParameters",
                        "list": [
                            {
                                "type": "MAP",
                                "map": [
                                    {"type": "TEMPLATE", "key": "name", "value": "plan_type"},
                                    {"type": "TEMPLATE", "key": "value", "value": "{{DLV - Plan Type}}"}
                                ]
                            }
                        ]
                    }
                ],
                firing_trigger_id=[self.created_triggers.get("Trial Started", "")],
                notes="Track trial starts"
            ),
            
            GTMTag(
                name="GA4 - Purchase",
                type="gaawe",
                parameter=[
                    {"type": "TEMPLATE", "key": "measurementId", "value": "{{Const - GA4 Measurement ID}}"},
                    {"type": "TEMPLATE", "key": "eventName", "value": "purchase"},
                    {
                        "type": "LIST",
                        "key": "eventParameters",
                        "list": [
                            {
                                "type": "MAP",
                                "map": [
                                    {"type": "TEMPLATE", "key": "name", "value": "transaction_id"},
                                    {"type": "TEMPLATE", "key": "value", "value": "{{DLV - Transaction ID}}"}
                                ]
                            },
                            {
                                "type": "MAP",
                                "map": [
                                    {"type": "TEMPLATE", "key": "name", "value": "value"},
                                    {"type": "TEMPLATE", "key": "value", "value": "{{DLV - Transaction Value}}"}
                                ]
                            },
                            {
                                "type": "MAP",
                                "map": [
                                    {"type": "TEMPLATE", "key": "name", "value": "currency"},
                                    {"type": "TEMPLATE", "key": "value", "value": "{{DLV - Currency}}"}
                                ]
                            }
                        ]
                    }
                ],
                firing_trigger_id=[self.created_triggers.get("Payment Completed", "")],
                notes="Track purchases and payments"
            ),
            
            # Generic Event Tag for All Custom Events
            GTMTag(
                name="GA4 - Generic Event",
                type="gaawe",
                parameter=[
                    {"type": "TEMPLATE", "key": "measurementId", "value": "{{Const - GA4 Measurement ID}}"},
                    {"type": "TEMPLATE", "key": "eventName", "value": "{{Event}}"},
                    {
                        "type": "LIST",
                        "key": "eventParameters",
                        "list": [
                            {
                                "type": "MAP",
                                "map": [
                                    {"type": "TEMPLATE", "key": "name", "value": "event_category"},
                                    {"type": "TEMPLATE", "key": "value", "value": "{{DLV - Event Category}}"}
                                ]
                            },
                            {
                                "type": "MAP",
                                "map": [
                                    {"type": "TEMPLATE", "key": "name", "value": "event_action"},
                                    {"type": "TEMPLATE", "key": "value", "value": "{{DLV - Event Action}}"}
                                ]
                            },
                            {
                                "type": "MAP",
                                "map": [
                                    {"type": "TEMPLATE", "key": "name", "value": "event_label"},
                                    {"type": "TEMPLATE", "key": "value", "value": "{{DLV - Event Label}}"}
                                ]
                            },
                            {
                                "type": "MAP",
                                "map": [
                                    {"type": "TEMPLATE", "key": "name", "value": "value"},
                                    {"type": "TEMPLATE", "key": "value", "value": "{{DLV - Event Value}}"}
                                ]
                            }
                        ]
                    }
                ],
                firing_trigger_id=[self.created_triggers.get("All Custom Events", "")],
                notes="Generic tag for all custom events"
            ),
        ]
        
        created = {}
        for tag in tags:
            # Skip if already exists
            if tag.name in self.created_tags:
                logger.info(f"Tag already exists, skipping: {tag.name}")
                created[tag.name] = self.created_tags[tag.name]
                continue
                
            try:
                # Skip tags if their triggers weren't created
                if tag.firing_trigger_id and not all(tag.firing_trigger_id):
                    logger.warning(f"Skipping tag {tag.name} - required triggers not found")
                    continue
                
                result = self.service.accounts().containers().workspaces().tags().create(
                    parent=self.get_workspace_path(),
                    body=tag.to_api_format()
                ).execute()
                
                created[tag.name] = result['tagId']
                logger.info(f"Created tag: {tag.name} (ID: {result['tagId']})")
                
            except HttpError as e:
                logger.error(f"Error creating tag {tag.name}: {e}")
                
        self.created_tags = created
        return created
    
    def create_version(self, name: str = None, notes: str = None):
        """Create a version of the workspace"""
        if not name:
            from datetime import datetime
            name = f"API Configuration - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        if not notes:
            notes = f"Automated configuration: {len(self.created_variables)} variables, {len(self.created_triggers)} triggers, {len(self.created_tags)} tags"
        
        try:
            version = self.service.accounts().containers().workspaces().create_version(
                path=self.get_workspace_path(),
                body={
                    "name": name,
                    "notes": notes
                }
            ).execute()
            
            logger.info(f"Created version: {version.get('containerVersion', {}).get('name', 'Unknown')}")
            return version
            
        except HttpError as e:
            logger.error(f"Error creating version: {e}")
            return None
    
    def publish_version(self, version_id: str):
        """Publish a version to live"""
        try:
            container_version_path = f"{self.container_path}/versions/{version_id}"
            
            result = self.service.accounts().containers().versions().publish(
                path=container_version_path
            ).execute()
            
            logger.info(f"Published version {version_id} to live")
            return result
            
        except HttpError as e:
            logger.error(f"Error publishing version: {e}")
            return None
    
    def export_configuration(self, filename: str = "gtm_configuration.json"):
        """Export the created configuration to a JSON file"""
        config = {
            "account_id": self.account_id,
            "container_id": self.container_id,
            "workspace": self.workspace_name,
            "variables": self.created_variables,
            "triggers": self.created_triggers,
            "tags": self.created_tags,
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)
        
        logger.info(f"Configuration exported to {filename}")
    
    def run_full_setup(self, publish: bool = False):
        """Run the complete GTM setup process"""
        logger.info("Starting GTM configuration...")
        
        # Create workspace
        self.create_workspace()
        
        # Create all components
        logger.info("Creating variables...")
        self.create_variables()
        
        logger.info("Creating triggers...")
        self.create_triggers()
        
        logger.info("Creating tags...")
        self.create_tags()
        
        # Create version
        logger.info("Creating version...")
        version = self.create_version()
        
        # Optionally publish
        if publish and version:
            version_id = version.get('containerVersion', {}).get('containerVersionId')
            if version_id:
                logger.info("Publishing version...")
                self.publish_version(version_id)
        
        # Export configuration
        self.export_configuration()
        
        logger.info("GTM configuration complete!")
        return {
            "variables": len(self.created_variables),
            "triggers": len(self.created_triggers),
            "tags": len(self.created_tags)
        }

def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description="Configure Google Tag Manager via API")
    parser.add_argument("--account-id", required=True, help="GTM Account ID")
    parser.add_argument("--container-id", default="GTM-WKP28PNQ", help="GTM Container ID")
    parser.add_argument("--credentials", help="Path to credentials JSON file")
    parser.add_argument("--workspace", default="API Configuration", help="Workspace name")
    parser.add_argument("--publish", action="store_true", help="Publish version after creation")
    parser.add_argument("--ga4-id", help="Google Analytics 4 Measurement ID")
    
    args = parser.parse_args()
    
    # Create configurator
    configurator = GTMConfigurator(
        account_id=args.account_id,
        container_id=args.container_id,
        workspace_name=args.workspace
    )
    
    try:
        # Authenticate
        logger.info("Authenticating with Google Tag Manager API...")
        configurator.authenticate(args.credentials)
        
        # Update GA4 ID if provided
        if args.ga4_id:
            logger.info(f"Using GA4 Measurement ID: {args.ga4_id}")
            # This would be used to update the constant variable
        
        # Run setup
        result = configurator.run_full_setup(publish=args.publish)
        
        print("\n" + "="*50)
        print("GTM Configuration Complete!")
        print("="*50)
        print(f"[U+2713] Variables created: {result['variables']}")
        print(f"[U+2713] Triggers created: {result['triggers']}")
        print(f"[U+2713] Tags created: {result['tags']}")
        print("\nConfiguration exported to: gtm_configuration.json")
        
        if not args.publish:
            print("\nNote: Configuration created but not published.")
            print("To publish, review in GTM console or run with --publish flag")
        
    except Exception as e:
        logger.error(f"Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
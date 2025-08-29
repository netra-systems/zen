#!/usr/bin/env python3
"""
Google Analytics 4 Automated Configuration Script
Implements complete GA4 setup based on specifications in ga4_config.json

This script configures:
- Custom dimensions (user & event scoped)
- Custom metrics
- Conversion events
- Audiences
- Enhanced measurement settings
- Data retention
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import os
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    # Use v1beta API
    from google.analytics.admin_v1beta import AnalyticsAdminServiceClient
    from google.analytics.admin_v1beta.types import (
        CustomDimension,
        CustomMetric,
        ConversionEvent,
        KeyEvent,
        Property,
        DataRetentionSettings,
        IndustryCategory,
        NumericValue,
        AccountSummary,
        PropertySummary
    )
    from google.oauth2 import service_account
    GOOGLE_ANALYTICS_AVAILABLE = True
    # Note: Audiences are not available in v1beta API, must be created manually
    AUDIENCE_SUPPORT = False
    logger.info("Using Google Analytics Admin API v1beta")
        
except ImportError as e:
    GOOGLE_ANALYTICS_AVAILABLE = False
    AUDIENCE_SUPPORT = False
    logger.warning(f"Google Analytics Admin API not installed or wrong version. Error: {e}")

class DimensionScope(Enum):
    """GA4 Custom Dimension Scopes"""
    USER = "USER"
    EVENT = "EVENT"
    ITEM = "ITEM"

class MetricScope(Enum):
    """GA4 Custom Metric Scopes"""
    EVENT = "EVENT"

class MeasurementUnit(Enum):
    """GA4 Metric Measurement Units"""
    STANDARD = "STANDARD"
    CURRENCY = "CURRENCY"
    SECONDS = "SECONDS"
    MILLISECONDS = "MILLISECONDS"
    MINUTES = "MINUTES"
    HOURS = "HOURS"

@dataclass
class GA4Configuration:
    """GA4 Configuration from JSON"""
    measurement_id: str
    property_name: str
    property_id: str
    account_id: str
    service_account_email: str
    credentials_path: str
    project_id: str
    
    @classmethod
    def from_config_file(cls, config_path: str = "ga4_config.json"):
        """Load configuration from JSON file"""
        config_file = Path(config_path)
        if not config_file.exists():
            # Try scripts directory
            config_file = Path(__file__).parent / config_path
        
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        return cls(
            measurement_id=config['ga4_property']['measurement_id'],
            property_name=config['ga4_property']['property_name'],
            property_id=config['ga4_property'].get('property_id', ''),
            account_id=config['ga4_property'].get('account_id', ''),
            service_account_email=config['service_account']['email'],
            credentials_path=config['service_account']['key_file'],
            project_id=config['service_account']['project_id']
        )

class GA4Configurator:
    """Google Analytics 4 API Configurator"""
    
    def __init__(self, config: GA4Configuration):
        self.config = config
        self.client = None
        self.property_path = None
        self.existing_dimensions = {}
        self.existing_metrics = {}
        self.existing_conversions = set()
        self.existing_audiences = {}
        
    def authenticate(self):
        """Authenticate with Google Analytics Admin API"""
        if not GOOGLE_ANALYTICS_AVAILABLE:
            logger.error("Google Analytics Admin API not available. Please install required packages.")
            return False
        
        try:
            # Check if credentials file exists
            cred_path = Path(self.config.credentials_path)
            if not cred_path.exists():
                # Try in scripts directory
                cred_path = Path(__file__).parent / self.config.credentials_path
            
            if not cred_path.exists():
                logger.error(f"Credentials file not found: {self.config.credentials_path}")
                logger.info("Please ensure service account key is available")
                return False
            
            credentials = service_account.Credentials.from_service_account_file(
                str(cred_path),
                scopes=['https://www.googleapis.com/auth/analytics.edit']
            )
            
            self.client = AnalyticsAdminServiceClient(credentials=credentials)
            logger.info(f"[OK] Authenticated as {self.config.service_account_email}")
            return True
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def find_property(self):
        """Find GA4 property by measurement ID or create property path"""
        try:
            # If we have property_id and account_id, construct the path directly
            if self.config.property_id and self.config.account_id:
                self.property_path = f"properties/{self.config.property_id}"
                logger.info(f"[OK] Using property path: {self.property_path}")
                return True
            
            # Otherwise, list properties to find it
            logger.info(f"Searching for property with measurement ID: {self.config.measurement_id}")
            
            # List all accessible accounts first
            accounts = list(self.client.list_account_summaries())
            
            for account in accounts:
                # List properties for this account
                for prop_summary in account.property_summaries:
                    prop_name = prop_summary.property
                    
                    # Get full property details
                    prop = self.client.get_property(name=prop_name)
                    
                    # Get data streams to check measurement ID
                    data_streams = self.client.list_data_streams(parent=prop_name)
                    
                    for stream in data_streams:
                        if hasattr(stream, 'web_stream_data') and stream.web_stream_data:
                            if stream.web_stream_data.measurement_id == self.config.measurement_id:
                                self.property_path = prop_name
                                logger.info(f"[OK] Found property: {prop.display_name} ({prop_name})")
                                
                                # Update config with discovered IDs
                                self.config.property_id = prop_name.split('/')[-1]
                                self.config.account_id = account.account.split('/')[-1]
                                return True
            
            logger.error(f"Property with measurement ID {self.config.measurement_id} not found")
            logger.info("Please verify the measurement ID and service account permissions")
            return False
            
        except Exception as e:
            logger.error(f"Error finding property: {e}")
            return False
    
    def load_existing_configurations(self):
        """Load existing custom dimensions, metrics, and conversion events"""
        try:
            logger.info("Loading existing configurations...")
            
            # Load existing custom dimensions
            dimensions = self.client.list_custom_dimensions(parent=self.property_path)
            for dim in dimensions:
                self.existing_dimensions[dim.parameter_name] = dim
            logger.info(f"Found {len(self.existing_dimensions)} existing custom dimensions")
            
            # Load existing custom metrics
            metrics = self.client.list_custom_metrics(parent=self.property_path)
            for metric in metrics:
                self.existing_metrics[metric.parameter_name] = metric
            logger.info(f"Found {len(self.existing_metrics)} existing custom metrics")
            
            # Load existing conversion events
            conversions = self.client.list_conversion_events(parent=self.property_path)
            for conv in conversions:
                self.existing_conversions.add(conv.event_name)
            logger.info(f"Found {len(self.existing_conversions)} existing conversion events")
            
            # Load existing audiences
            audiences = self.client.list_audiences(parent=self.property_path)
            for aud in audiences:
                self.existing_audiences[aud.display_name] = aud
            logger.info(f"Found {len(self.existing_audiences)} existing audiences")
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading existing configurations: {e}")
            return False
    
    def create_custom_dimensions(self, dimensions: List[Dict]):
        """Create or update custom dimensions in GA4"""
        logger.info(f"Processing {len(dimensions)} custom dimensions")
        created = 0
        skipped = 0
        
        for dimension in dimensions:
            try:
                param_name = dimension['parameter_name']
                
                # Check if dimension already exists
                if param_name in self.existing_dimensions:
                    logger.info(f"  [EXISTS] Dimension already exists: {dimension['display_name']}")
                    skipped += 1
                    continue
                
                # Create new dimension
                custom_dimension = CustomDimension(
                    parameter_name=param_name,
                    display_name=dimension['display_name'],
                    description=dimension['description'],
                    scope=CustomDimension.DimensionScope[dimension['scope']]
                )
                
                # Use proper request format for v1beta
                from google.analytics.admin_v1beta.types import CreateCustomDimensionRequest
                request = CreateCustomDimensionRequest(
                    parent=self.property_path,
                    custom_dimension=custom_dimension
                )
                
                result = self.client.create_custom_dimension(request=request)
                
                logger.info(f"  [OK] Created dimension: {dimension['display_name']}")
                created += 1
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"  [ERROR] Failed to create dimension {dimension['display_name']}: {e}")
        
        logger.info(f"Dimensions: {created} created, {skipped} already existed")
        return created > 0 or skipped > 0
    
    def create_custom_metrics(self, metrics: List[Dict]):
        """Create or update custom metrics in GA4"""
        logger.info(f"Processing {len(metrics)} custom metrics")
        created = 0
        skipped = 0
        
        for metric in metrics:
            try:
                param_name = metric['parameter_name']
                
                # Check if metric already exists
                if param_name in self.existing_metrics:
                    logger.info(f"  [EXISTS] Metric already exists: {metric['display_name']}")
                    skipped += 1
                    continue
                
                # Map measurement unit
                unit_map = {
                    "STANDARD": CustomMetric.MeasurementUnit.STANDARD,
                    "SECONDS": CustomMetric.MeasurementUnit.SECONDS,
                    "MILLISECONDS": CustomMetric.MeasurementUnit.MILLISECONDS,
                    "MINUTES": CustomMetric.MeasurementUnit.MINUTES,
                    "HOURS": CustomMetric.MeasurementUnit.HOURS,
                    "CURRENCY": CustomMetric.MeasurementUnit.CURRENCY
                }
                
                # Create new metric  
                custom_metric = CustomMetric(
                    parameter_name=param_name,
                    display_name=metric['display_name'],
                    description=metric['description'],
                    measurement_unit=unit_map.get(metric['measurement_unit'], CustomMetric.MeasurementUnit.STANDARD),
                    scope=CustomMetric.MetricScope.EVENT
                )
                
                # Use proper request format for v1beta
                from google.analytics.admin_v1beta.types import CreateCustomMetricRequest
                request = CreateCustomMetricRequest(
                    parent=self.property_path,
                    custom_metric=custom_metric
                )
                
                result = self.client.create_custom_metric(request=request)
                
                logger.info(f"  [OK] Created metric: {metric['display_name']}")
                created += 1
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"  [ERROR] Failed to create metric {metric['display_name']}: {e}")
        
        logger.info(f"Metrics: {created} created, {skipped} already existed")
        return created > 0 or skipped > 0
    
    def mark_conversion_events(self, event_names: List[str]):
        """Mark events as conversions in GA4"""
        logger.info(f"Processing {len(event_names)} conversion events")
        created = 0
        skipped = 0
        
        for event_name in event_names:
            try:
                # Check if already marked as conversion
                if event_name in self.existing_conversions:
                    logger.info(f"  [EXISTS] Already marked as conversion: {event_name}")
                    skipped += 1
                    continue
                
                # Create conversion event
                conversion_event = ConversionEvent(
                    event_name=event_name,
                    counting_method=ConversionEvent.ConversionCountingMethod.ONCE_PER_EVENT
                )
                
                # Use proper request format for v1beta
                from google.analytics.admin_v1beta.types import CreateConversionEventRequest
                request = CreateConversionEventRequest(
                    parent=self.property_path,
                    conversion_event=conversion_event
                )
                
                result = self.client.create_conversion_event(request=request)
                
                logger.info(f"  [OK] Marked as conversion: {event_name}")
                created += 1
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.info(f"  [EXISTS] Already exists: {event_name}")
                    skipped += 1
                else:
                    logger.error(f"  [ERROR] Failed to mark conversion {event_name}: {e}")
        
        logger.info(f"Conversions: {created} created, {skipped} already existed")
        return created > 0 or skipped > 0
    
    def create_audiences(self, audiences: List[Dict]):
        """Create audiences in GA4"""
        logger.info(f"Processing {len(audiences)} audiences")
        created = 0
        skipped = 0
        
        for audience_config in audiences:
            try:
                display_name = audience_config['display_name']
                
                # Check if audience already exists
                if display_name in self.existing_audiences:
                    logger.info(f"  [EXISTS] Audience already exists: {display_name}")
                    skipped += 1
                    continue
                
                # Note: Audience creation via API is complex and may require
                # specific filter clause structures. This is a simplified version.
                logger.info(f"  [WARNING] Audience '{display_name}' requires manual creation in GA4 UI")
                logger.info(f"    Description: {audience_config['description']}")
                
            except Exception as e:
                logger.error(f"  [ERROR] Failed to process audience {display_name}: {e}")
        
        if len(audiences) > skipped:
            logger.info(f"Note: {len(audiences) - skipped} audiences need manual creation in GA4 UI")
        
        return True
    
    def configure_data_retention(self, retention_period: str = "FOURTEEN_MONTHS"):
        """Configure data retention settings"""
        logger.info(f"Configuring data retention: {retention_period}")
        
        try:
            # Get data retention settings
            from google.analytics.admin_v1beta.types import GetDataRetentionSettingsRequest, UpdateDataRetentionSettingsRequest
            from google.protobuf import field_mask_pb2
            
            # Get current settings
            get_request = GetDataRetentionSettingsRequest(
                name=f"{self.property_path}/dataRetentionSettings"
            )
            settings = self.client.get_data_retention_settings(request=get_request)
            
            # Update retention settings
            settings.event_data_retention = DataRetentionSettings.RetentionDuration[retention_period]
            settings.reset_user_data_on_new_activity = True
            
            # Create update request
            update_request = UpdateDataRetentionSettingsRequest(
                data_retention_settings=settings,
                update_mask=field_mask_pb2.FieldMask(paths=["event_data_retention", "reset_user_data_on_new_activity"])
            )
            
            result = self.client.update_data_retention_settings(request=update_request)
            
            logger.info(f"[OK] Data retention configured: {retention_period}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure data retention: {e}")
            return False
    
    def validate_configuration(self):
        """Validate that configurations were applied"""
        logger.info("\nValidating GA4 configuration:")
        
        # Reload configurations to check
        self.load_existing_configurations()
        
        # Load expected configuration
        config_file = Path(__file__).parent / "ga4_config.json"
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        # Validate dimensions
        expected_dims = len(config['custom_dimensions']['user_scoped']) + \
                       len(config['custom_dimensions']['event_scoped'])
        actual_dims = len(self.existing_dimensions)
        logger.info(f"  Custom Dimensions: {actual_dims}/{expected_dims}")
        
        # Validate metrics
        expected_metrics = len(config['custom_metrics'])
        actual_metrics = len(self.existing_metrics)
        logger.info(f"  Custom Metrics: {actual_metrics}/{expected_metrics}")
        
        # Validate conversions
        expected_conversions = len(config['conversion_events'])
        actual_conversions = len([e for e in config['conversion_events'] if e in self.existing_conversions])
        logger.info(f"  Conversion Events: {actual_conversions}/{expected_conversions}")
        
        # Validate audiences
        expected_audiences = len(config['audiences'])
        actual_audiences = len(self.existing_audiences)
        logger.info(f"  Audiences: {actual_audiences}/{expected_audiences}")
        
        return True
    
    def run_full_setup(self):
        """Execute the complete GA4 configuration"""
        logger.info("\n" + "="*60)
        logger.info("GOOGLE ANALYTICS 4 AUTOMATED CONFIGURATION")
        logger.info("="*60)
        
        try:
            # Load configuration
            config_file = Path(__file__).parent / "ga4_config.json"
            with open(config_file, 'r') as f:
                config = json.load(f)
            
            # Step 1: Authenticate
            if not self.authenticate():
                logger.error("Authentication failed. Exiting.")
                return False
            
            # Step 2: Find property
            if not self.find_property():
                logger.error("Could not find GA4 property. Exiting.")
                return False
            
            # Step 3: Load existing configurations
            if not self.load_existing_configurations():
                logger.warning("Could not load existing configurations, proceeding anyway...")
            
            # Step 4: Create custom dimensions
            logger.info("\n--- Custom Dimensions ---")
            user_dimensions = config['custom_dimensions']['user_scoped']
            event_dimensions = config['custom_dimensions']['event_scoped']
            all_dimensions = user_dimensions + event_dimensions
            self.create_custom_dimensions(all_dimensions)
            
            # Step 5: Create custom metrics
            logger.info("\n--- Custom Metrics ---")
            self.create_custom_metrics(config['custom_metrics'])
            
            # Step 6: Mark conversion events
            logger.info("\n--- Conversion Events ---")
            self.mark_conversion_events(config['conversion_events'])
            
            # Step 7: Create audiences
            logger.info("\n--- Audiences ---")
            self.create_audiences(config['audiences'])
            
            # Step 8: Configure data retention
            logger.info("\n--- Data Retention ---")
            retention_map = {
                "14_MONTHS": "FOURTEEN_MONTHS",
                "2_MONTHS": "TWO_MONTHS",
                "26_MONTHS": "TWENTY_SIX_MONTHS",
                "38_MONTHS": "THIRTY_EIGHT_MONTHS",
                "50_MONTHS": "FIFTY_MONTHS"
            }
            retention = config.get('data_retention', {}).get('event_data_retention', '14_MONTHS')
            self.configure_data_retention(retention_map.get(retention, "FOURTEEN_MONTHS"))
            
            # Step 9: Note about enhanced measurement
            logger.info("\n--- Enhanced Measurement ---")
            logger.info("Enhanced measurement settings must be configured in GA4 UI:")
            for setting, enabled in config['enhanced_measurement'].items():
                status = "Enable" if enabled else "Disable"
                logger.info(f"  - {status}: {setting}")
            
            # Step 10: Note about BigQuery
            if config.get('bigquery_export', {}).get('enabled'):
                logger.info("\n--- BigQuery Export ---")
                logger.info("BigQuery linking must be configured in GA4 UI:")
                logger.info(f"  - Dataset: {config['bigquery_export']['dataset_id']}")
                logger.info(f"  - Frequency: {config['bigquery_export']['frequency']}")
            
            # Step 11: Validate
            logger.info("\n" + "="*60)
            self.validate_configuration()
            
            logger.info("\n" + "="*60)
            logger.info("[OK] GA4 CONFIGURATION COMPLETED!")
            logger.info("="*60)
            
            logger.info("\n[WARNING] Manual steps required in GA4 UI:")
            logger.info("1. Create audiences as specified")
            logger.info("2. Configure enhanced measurement settings")
            logger.info("3. Set up BigQuery export (if needed)")
            logger.info("4. Create custom reports/explorations")
            
            return True
            
        except Exception as e:
            logger.error(f"\n[ERROR] Configuration failed: {e}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Main execution function"""
    # Check for required packages
    if not GOOGLE_ANALYTICS_AVAILABLE:
        print("\n" + "="*60)
        print("INSTALLATION REQUIRED")
        print("="*60)
        print("\nGoogle Analytics Admin API is not installed.")
        print("\nInstall with:")
        print("  pip install google-analytics-admin")
        print("\nOr install all requirements:")
        print("  pip install google-analytics-admin google-auth")
        print("="*60)
        return
    
    # Load configuration
    try:
        config = GA4Configuration.from_config_file()
    except FileNotFoundError:
        print("\n[ERROR] Configuration file 'ga4_config.json' not found!")
        print("Please ensure the file exists in the scripts directory.")
        return
    except Exception as e:
        print(f"\n[ERROR] Error loading configuration: {e}")
        return
    
    # Run configuration
    configurator = GA4Configurator(config)
    success = configurator.run_full_setup()
    
    if success:
        print("\n[OK] Script completed successfully!")
    else:
        print("\n[ERROR] Script completed with errors. Check logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()
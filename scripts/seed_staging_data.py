#!/usr/bin/env python
"""
Seed staging environment with test data for comprehensive testing.
This script creates realistic test data for staging environments.
"""

import argparse
import asyncio
import hashlib
import json
import os
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

from faker import Faker

# Add project root to path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from netra_backend.app.auth_integration.auth_utils import get_password_hash
from netra_backend.app.db.database import engine, get_db
from netra_backend.app.schemas.message import MessageCreate
from netra_backend.app.schemas.optimization_request import OptimizationRequestCreate
from netra_backend.app.schemas.thread import ThreadCreate
from netra_backend.app.schemas.userbase import UserBase
from netra_backend.app.services.database.message_repository import MessageRepository
from netra_backend.app.services.database.optimization_repository import (
    OptimizationRepository,
)
from netra_backend.app.services.database.thread_repository import ThreadRepository
from netra_backend.app.services.database.user_repository import UserRepository

# Initialize Faker for realistic data generation
fake = Faker()

class StagingDataSeeder:
    """Seed staging environment with test data"""
    
    def __init__(self, pr_number: str = None):
        self.pr_number = pr_number or os.getenv("PR_NUMBER", "test")
        self.user_repo = UserRepository()
        self.thread_repo = ThreadRepository()
        self.message_repo = MessageRepository()
        self.optimization_repo = OptimizationRepository()
        self.created_data = {
            "users": [],
            "threads": [],
            "messages": [],
            "optimizations": [],
            "metrics": []
        }
    
    async def seed_all(self, config: Dict[str, Any]):
        """Seed all test data based on configuration"""
        print(f"Seeding staging data for PR #{self.pr_number}...")
        
        async with AsyncSession(engine) as db:
            # Seed users
            await self.seed_users(db, config.get("users", {}))
            
            # Seed threads and messages
            await self.seed_threads_and_messages(db, config.get("threads", {}))
            
            # Seed optimization requests
            await self.seed_optimization_requests(db, config.get("optimizations", {}))
            
            # Seed metrics and telemetry
            await self.seed_metrics(db, config.get("metrics", {}))
            
            # Commit all changes
            await db.commit()
        
        print("Staging data seeding completed successfully!")
        return self.created_data
    
    async def seed_users(self, db: AsyncSession, config: Dict):
        """Create test users with various roles"""
        user_count = config.get("count", 10)
        roles = config.get("roles", {"admin": 1, "manager": 2, "user": 7})
        print(f"Creating {user_count} test users...")
        await self._create_admin_users(db, roles.get("admin", 1))
        await self._create_manager_users(db, roles.get("manager", 2))
        await self._create_regular_users(db, roles.get("user", 7))
    
    async def _create_admin_users(self, db: AsyncSession, count: int):
        """Create admin users."""
        for i in range(count):
            user_data = self._build_admin_user_data(i)
            user = await self.user_repo.create(db, user_data)
            self.created_data["users"].append(user.id)
            print(f"  Created admin user: {user.username}")
    
    async def _create_manager_users(self, db: AsyncSession, count: int):
        """Create manager users."""
        for i in range(count):
            user_data = self._build_manager_user_data(i)
            user = await self.user_repo.create(db, user_data)
            self.created_data["users"].append(user.id)
            print(f"  Created manager user: {user.username}")
    
    async def _create_regular_users(self, db: AsyncSession, count: int):
        """Create regular users."""
        for i in range(count):
            user_data = self._build_regular_user_data(i)
            user = await self.user_repo.create(db, user_data)
            self.created_data["users"].append(user.id)
            print(f"  Created regular user: {user.username}")
    
    def _build_admin_user_data(self, index: int) -> Dict:
        """Build admin user data."""
        return {
            "email": f"admin{index+1}.pr{self.pr_number}@staging.netrasystems.ai",
            "username": f"admin{index+1}_pr{self.pr_number}", "full_name": fake.name(),
            "hashed_password": get_password_hash("TestPassword123!"), "is_active": True,
            "is_superuser": True, "role": "admin", "plan_tier": "enterprise",
            "created_at": datetime.now(timezone.utc) - timedelta(days=random.randint(30, 365)),
            "usage_quota": 100000, "usage_current": random.randint(0, 50000)
        }
    
    def _build_manager_user_data(self, index: int) -> Dict:
        """Build manager user data."""
        return {
            "email": f"manager{index+1}.pr{self.pr_number}@staging.netrasystems.ai",
            "username": f"manager{index+1}_pr{self.pr_number}", "full_name": fake.name(),
            "hashed_password": get_password_hash("TestPassword123!"), "is_active": True,
            "is_superuser": False, "role": "manager", "plan_tier": "professional",
            "created_at": datetime.now(timezone.utc) - timedelta(days=random.randint(30, 180)),
            "usage_quota": 50000, "usage_current": random.randint(0, 25000)
        }
    
    def _build_regular_user_data(self, index: int) -> Dict:
        """Build regular user data."""
        return {
            "email": f"user{index+1}.pr{self.pr_number}@staging.netrasystems.ai",
            "username": f"user{index+1}_pr{self.pr_number}", "full_name": fake.name(),
            "hashed_password": get_password_hash("TestPassword123!"), "is_active": True,
            "is_superuser": False, "role": "user",
            "created_at": datetime.now(timezone.utc) - timedelta(days=random.randint(1, 90)),
            "plan_tier": random.choice(["free", "starter", "professional"]),
            "usage_quota": random.choice([1000, 10000, 50000]), "usage_current": random.randint(0, 1000)
        }
    
    async def seed_threads_and_messages(self, db: AsyncSession, config: Dict):
        """Create threads with messages for each user"""
        threads_per_user = config.get("threads_per_user", 5)
        messages_per_thread = config.get("messages_per_thread", 10)
        
        print(f"Creating {threads_per_user} threads per user with {messages_per_thread} messages each...")
        
        sample_topics = [
            "Cost Optimization Analysis",
            "Performance Tuning",
            "Resource Allocation",
            "Model Selection",
            "Inference Optimization",
            "Batch Processing Strategy",
            "Real-time Processing",
            "GPU Utilization",
            "Memory Management",
            "Latency Reduction"
        ]
        
        for user_id in self.created_data["users"]:
            for t in range(threads_per_user):
                # Create thread
                thread_data = ThreadCreate(
                    name=f"{random.choice(sample_topics)} - Test {t+1}",
                    description=fake.sentence(),
                    user_id=user_id,
                    metadata={
                        "pr_number": self.pr_number,
                        "test_data": True,
                        "created_for": "staging"
                    }
                )
                thread = await self.thread_repo.create(db, thread_data.dict())
                self.created_data["threads"].append(thread.id)
                
                # Create messages in thread
                for m in range(messages_per_thread):
                    is_user = m % 2 == 0
                    message_data = MessageCreate(
                        thread_id=thread.id,
                        content=fake.paragraph() if is_user else f"Analysis result: {fake.sentence()}",
                        sender="user" if is_user else "assistant",
                        message_type="text",
                        metadata={
                            "test": True,
                            "sequence": m
                        }
                    )
                    message = await self.message_repo.create(db, message_data.dict())
                    self.created_data["messages"].append(message.id)
    
    def _get_optimization_configuration(self, config: Dict) -> Dict[str, Any]:
        """Get optimization seeding configuration."""
        request_count = config.get("count", 50)
        print(f"Creating {request_count} optimization requests...")
        return {
            "request_count": request_count,
            "optimization_types": ["cost_optimization", "performance_optimization", "resource_optimization", "latency_optimization", "throughput_optimization"],
            "statuses": ["pending", "processing", "completed", "failed", "cancelled"],
            "status_weights": [0.1, 0.15, 0.6, 0.1, 0.05]
        }

    def _generate_request_identifiers(self) -> Dict[str, Any]:
        """Generate user and thread identifiers for request."""
        user_id = random.choice(self.created_data["users"])
        thread_id = random.choice(self.created_data["threads"]) if self.created_data["threads"] else None
        return {"user_id": user_id, "thread_id": thread_id}

    def _generate_request_characteristics(self, opt_config: Dict) -> Dict[str, str]:
        """Generate optimization request characteristics."""
        status = random.choices(opt_config["statuses"], weights=opt_config["status_weights"])[0]
        opt_type = random.choice(opt_config["optimization_types"])
        priority = random.choice(["low", "medium", "high", "critical"])
        return {"status": status, "request_type": opt_type, "priority": priority}

    def _generate_request_parameters(self) -> Dict[str, str]:
        """Generate optimization request parameters."""
        return {
            "target_metric": random.choice(["cost", "latency", "throughput"]),
            "constraint": random.choice(["budget", "sla", "capacity"]),
            "optimization_level": random.choice(["basic", "advanced", "extreme"]),
            "time_window": random.choice(["hourly", "daily", "weekly", "monthly"])
        }

    def _generate_request_timestamps(self) -> Dict[str, datetime]:
        """Generate request creation and update timestamps."""
        return {
            "created_at": datetime.now(timezone.utc) - timedelta(hours=random.randint(1, 720)),
            "updated_at": datetime.now(timezone.utc) - timedelta(hours=random.randint(0, 24))
        }

    def _generate_completed_request_results(self) -> Dict[str, Any]:
        """Generate results for completed optimization requests."""
        return {
            "original_cost": random.uniform(1000, 10000),
            "optimized_cost": random.uniform(500, 8000),
            "savings_percentage": random.uniform(10, 50),
            "recommendations": [fake.sentence() for _ in range(random.randint(3, 7))],
            "implementation_steps": [fake.sentence() for _ in range(random.randint(5, 10))]
        }

    def _build_optimization_request_data(self, opt_config: Dict) -> Dict[str, Any]:
        """Build complete optimization request data structure."""
        identifiers = self._generate_request_identifiers()
        characteristics = self._generate_request_characteristics(opt_config)
        parameters = self._generate_request_parameters()
        timestamps = self._generate_request_timestamps()
        
        request_data = {**identifiers, **characteristics, "parameters": parameters, **timestamps}
        
        if characteristics["status"] == "completed":
            request_data["results"] = self._generate_completed_request_results()
            request_data["completed_at"] = datetime.now(timezone.utc) - timedelta(hours=random.randint(0, 12))
        
        return request_data

    async def _create_single_optimization_request(self, db: AsyncSession, opt_config: Dict):
        """Create a single optimization request and track it."""
        request_data = self._build_optimization_request_data(opt_config)
        optimization = await self.optimization_repo.create(db, request_data)
        self.created_data["optimizations"].append(optimization.id)

    async def seed_optimization_requests(self, db: AsyncSession, config: Dict):
        """Create optimization requests with various statuses"""
        opt_config = self._get_optimization_configuration(config)
        for i in range(opt_config["request_count"]):
            await self._create_single_optimization_request(db, opt_config)
        print(f"  Created {opt_config['request_count']} optimization requests")
    
    def _get_metric_types(self) -> List[str]:
        """Get list of supported metric types."""
        return [
            "api_latency", "model_inference_time", "token_usage", "error_rate",
            "throughput", "cost_per_request", "memory_usage", "gpu_utilization",
            "cache_hit_rate", "queue_depth"
        ]

    def _generate_metric_timestamp(self, time_range_days: int) -> datetime:
        """Generate a random timestamp within the specified range."""
        return datetime.now(timezone.utc) - timedelta(
            days=random.randint(0, time_range_days),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59)
        )

    def _generate_metric_value(self, metric_type: str) -> float:
        """Generate realistic value based on metric type."""
        value_generators = {
            "api_latency": lambda: random.gauss(150, 50),
            "model_inference_time": lambda: random.gauss(500, 150),
            "token_usage": lambda: random.randint(100, 10000),
            "error_rate": lambda: random.uniform(0, 0.05),
            "throughput": lambda: random.gauss(1000, 300),
            "cost_per_request": lambda: random.uniform(0.001, 0.1),
            "memory_usage": lambda: random.uniform(60, 95),
            "gpu_utilization": lambda: random.uniform(40, 100),
            "cache_hit_rate": lambda: random.uniform(0.7, 0.99),
            "queue_depth": lambda: random.randint(0, 1000)
        }
        return value_generators.get(metric_type, lambda: 0)()

    def _create_metric_entry(self, metric_type: str, value: float, timestamp: datetime) -> Dict:
        """Create a single metric entry with metadata."""
        return {
            "metric_type": metric_type,
            "value": value,
            "timestamp": timestamp,
            "tags": {
                "environment": "staging", "pr_number": self.pr_number,
                "region": random.choice(["us-east-1", "us-west-2", "eu-west-1"]),
                "model": random.choice(["gpt-4", "claude-3", "gemini-pro"]),
                "user_tier": random.choice(["free", "pro", "enterprise"])
            }
        }

    async def seed_metrics(self, db: AsyncSession, config: Dict):
        """Create metrics and telemetry data"""
        metric_count = config.get("count", 1000)
        time_range_days = config.get("time_range_days", 30)
        print(f"Creating {metric_count} metric data points...")
        
        metric_types = self._get_metric_types()
        metrics = []
        
        for i in range(metric_count):
            metric_type = random.choice(metric_types)
            timestamp = self._generate_metric_timestamp(time_range_days)
            value = self._generate_metric_value(metric_type)
            metrics.append(self._create_metric_entry(metric_type, value, timestamp))
        
        self.created_data["metrics"] = metrics
        print(f"  Created {metric_count} metric data points")
    
    def generate_summary(self) -> Dict:
        """Generate summary of seeded data"""
        return {
            "pr_number": self.pr_number,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": {
                "users": len(self.created_data["users"]),
                "threads": len(self.created_data["threads"]),
                "messages": len(self.created_data["messages"]),
                "optimizations": len(self.created_data["optimizations"]),
                "metrics": len(self.created_data["metrics"])
            },
            "details": {
                "user_ids": self.created_data["users"][:5],  # First 5 for reference
                "thread_ids": self.created_data["threads"][:5],
                "optimization_ids": self.created_data["optimizations"][:5]
            }
        }


async def main():
    """Main entry point for staging data seeding."""
    parser = _create_seeding_parser()
    args = parser.parse_args()
    config = await _load_or_build_config(args)
    seeder = _initialize_seeder(args)
    summary = await _execute_seeding(seeder, config)
    await _handle_output_and_summary(args, summary)

def _create_seeding_parser() -> argparse.ArgumentParser:
    """Create argument parser for seeding script."""
    parser = argparse.ArgumentParser(description="Seed staging environment with test data")
    _add_basic_arguments(parser)
    _add_data_count_arguments(parser)
    _add_output_arguments(parser)
    return parser

def _add_basic_arguments(parser: argparse.ArgumentParser):
    """Add basic configuration arguments."""
    parser.add_argument("--pr-number", type=str, help="Pull request number for this staging environment")
    parser.add_argument("--config-file", type=str, help="Path to configuration file (JSON)")

def _add_data_count_arguments(parser: argparse.ArgumentParser):
    """Add data count configuration arguments."""
    parser.add_argument("--users", type=int, default=10, help="Number of users to create")
    parser.add_argument("--threads-per-user", type=int, default=5, help="Number of threads per user")
    parser.add_argument("--messages-per-thread", type=int, default=10, help="Number of messages per thread")
    parser.add_argument("--optimizations", type=int, default=50, help="Number of optimization requests")
    parser.add_argument("--metrics", type=int, default=1000, help="Number of metric data points")

def _add_output_arguments(parser: argparse.ArgumentParser):
    """Add output configuration arguments."""
    parser.add_argument("--output", type=str, help="Output file for seed summary (JSON)")

async def _load_or_build_config(args: argparse.Namespace) -> dict:
    """Load configuration from file or build from arguments."""
    if args.config_file:
        return _load_config_from_file(args.config_file)
    else:
        return _build_config_from_args(args)

def _load_config_from_file(config_file: str) -> dict:
    """Load configuration from JSON file."""
    with open(config_file, 'r') as f:
        return json.load(f)

def _build_config_from_args(args: argparse.Namespace) -> dict:
    """Build configuration from command line arguments."""
    return {
        "users": _build_user_config(args),
        "threads": _build_thread_config(args),
        "optimizations": {"count": args.optimizations},
        "metrics": {"count": args.metrics, "time_range_days": 30}
    }

def _build_user_config(args: argparse.Namespace) -> dict:
    """Build user configuration from arguments."""
    admin_count = max(1, args.users // 10)
    manager_count = max(2, args.users // 5)
    user_count = args.users - admin_count - manager_count
    return {
        "count": args.users,
        "roles": {"admin": admin_count, "manager": manager_count, "user": user_count}
    }

def _build_thread_config(args: argparse.Namespace) -> dict:
    """Build thread configuration from arguments."""
    return {
        "threads_per_user": args.threads_per_user,
        "messages_per_thread": args.messages_per_thread
    }

def _initialize_seeder(args: argparse.Namespace) -> StagingDataSeeder:
    """Initialize staging data seeder."""
    return StagingDataSeeder(pr_number=args.pr_number)

async def _execute_seeding(seeder: StagingDataSeeder, config: dict) -> dict:
    """Execute data seeding and return summary."""
    await seeder.seed_all(config)
    return seeder.generate_summary()

async def _handle_output_and_summary(args: argparse.Namespace, summary: dict):
    """Handle output file writing and summary printing."""
    _save_summary_if_requested(args, summary)
    _print_comprehensive_summary(summary)

def _save_summary_if_requested(args: argparse.Namespace, summary: dict):
    """Save summary to file if output path specified."""
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"Seed summary saved to: {args.output}")

def _print_comprehensive_summary(summary: dict):
    """Print comprehensive summary of seeded data."""
    print("\n" + "="*60)
    print("STAGING DATA SEED SUMMARY")
    print("="*60)
    _print_summary_header(summary)
    _print_data_counts(summary)
    print("="*60)

def _print_summary_header(summary: dict):
    """Print summary header information."""
    print(f"PR Number: {summary['pr_number']}")
    print(f"Timestamp: {summary['timestamp']}")
    print("\nData Created:")

def _print_data_counts(summary: dict):
    """Print individual data type counts."""
    for key, count in summary['summary'].items():
        print(f"  {key.capitalize()}: {count}")


if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python
"""
Seed staging environment with test data for comprehensive testing.
This script creates realistic test data for staging environments.
"""

import os
import sys
import json
import argparse
import asyncio
import random
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
from faker import Faker

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.db.database import get_db, engine
from app.schemas.userbase import UserBase
from app.schemas.thread import ThreadCreate
from app.schemas.message import MessageCreate
from app.schemas.optimization_request import OptimizationRequestCreate
from app.services.database.user_repository import UserRepository
from app.services.database.thread_repository import ThreadRepository
from app.services.database.message_repository import MessageRepository
from app.services.database.optimization_repository import OptimizationRepository
from app.auth.auth_utils import get_password_hash
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

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
        roles = config.get("roles", {
            "admin": 1,
            "manager": 2,
            "user": 7
        })
        
        print(f"Creating {user_count} test users...")
        
        # Create admin users
        for i in range(roles.get("admin", 1)):
            user_data = {
                "email": f"admin{i+1}.pr{self.pr_number}@staging.netrasystems.ai",
                "username": f"admin{i+1}_pr{self.pr_number}",
                "full_name": fake.name(),
                "hashed_password": get_password_hash("TestPassword123!"),
                "is_active": True,
                "is_superuser": True,
                "role": "admin",
                "created_at": datetime.utcnow() - timedelta(days=random.randint(30, 365)),
                "plan_tier": "enterprise",
                "usage_quota": 100000,
                "usage_current": random.randint(0, 50000)
            }
            user = await self.user_repo.create(db, user_data)
            self.created_data["users"].append(user.id)
            print(f"  Created admin user: {user.username}")
        
        # Create manager users
        for i in range(roles.get("manager", 2)):
            user_data = {
                "email": f"manager{i+1}.pr{self.pr_number}@staging.netrasystems.ai",
                "username": f"manager{i+1}_pr{self.pr_number}",
                "full_name": fake.name(),
                "hashed_password": get_password_hash("TestPassword123!"),
                "is_active": True,
                "is_superuser": False,
                "role": "manager",
                "created_at": datetime.utcnow() - timedelta(days=random.randint(30, 180)),
                "plan_tier": "professional",
                "usage_quota": 50000,
                "usage_current": random.randint(0, 25000)
            }
            user = await self.user_repo.create(db, user_data)
            self.created_data["users"].append(user.id)
            print(f"  Created manager user: {user.username}")
        
        # Create regular users
        for i in range(roles.get("user", 7)):
            user_data = {
                "email": f"user{i+1}.pr{self.pr_number}@staging.netrasystems.ai",
                "username": f"user{i+1}_pr{self.pr_number}",
                "full_name": fake.name(),
                "hashed_password": get_password_hash("TestPassword123!"),
                "is_active": True,
                "is_superuser": False,
                "role": "user",
                "created_at": datetime.utcnow() - timedelta(days=random.randint(1, 90)),
                "plan_tier": random.choice(["free", "starter", "professional"]),
                "usage_quota": random.choice([1000, 10000, 50000]),
                "usage_current": random.randint(0, 1000)
            }
            user = await self.user_repo.create(db, user_data)
            self.created_data["users"].append(user.id)
            print(f"  Created regular user: {user.username}")
    
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
    
    async def seed_optimization_requests(self, db: AsyncSession, config: Dict):
        """Create optimization requests with various statuses"""
        request_count = config.get("count", 50)
        
        print(f"Creating {request_count} optimization requests...")
        
        optimization_types = [
            "cost_optimization",
            "performance_optimization",
            "resource_optimization",
            "latency_optimization",
            "throughput_optimization"
        ]
        
        statuses = ["pending", "processing", "completed", "failed", "cancelled"]
        status_weights = [0.1, 0.15, 0.6, 0.1, 0.05]
        
        for i in range(request_count):
            user_id = random.choice(self.created_data["users"])
            thread_id = random.choice(self.created_data["threads"]) if self.created_data["threads"] else None
            
            status = random.choices(statuses, weights=status_weights)[0]
            opt_type = random.choice(optimization_types)
            
            request_data = {
                "user_id": user_id,
                "thread_id": thread_id,
                "request_type": opt_type,
                "status": status,
                "priority": random.choice(["low", "medium", "high", "critical"]),
                "parameters": {
                    "target_metric": random.choice(["cost", "latency", "throughput"]),
                    "constraint": random.choice(["budget", "sla", "capacity"]),
                    "optimization_level": random.choice(["basic", "advanced", "extreme"]),
                    "time_window": random.choice(["hourly", "daily", "weekly", "monthly"])
                },
                "created_at": datetime.utcnow() - timedelta(hours=random.randint(1, 720)),
                "updated_at": datetime.utcnow() - timedelta(hours=random.randint(0, 24))
            }
            
            # Add results for completed requests
            if status == "completed":
                request_data["results"] = {
                    "original_cost": random.uniform(1000, 10000),
                    "optimized_cost": random.uniform(500, 8000),
                    "savings_percentage": random.uniform(10, 50),
                    "recommendations": [
                        fake.sentence() for _ in range(random.randint(3, 7))
                    ],
                    "implementation_steps": [
                        fake.sentence() for _ in range(random.randint(5, 10))
                    ]
                }
                request_data["completed_at"] = datetime.utcnow() - timedelta(hours=random.randint(0, 12))
            
            optimization = await self.optimization_repo.create(db, request_data)
            self.created_data["optimizations"].append(optimization.id)
        
        print(f"  Created {request_count} optimization requests")
    
    async def seed_metrics(self, db: AsyncSession, config: Dict):
        """Create metrics and telemetry data"""
        metric_count = config.get("count", 1000)
        time_range_days = config.get("time_range_days", 30)
        
        print(f"Creating {metric_count} metric data points...")
        
        metric_types = [
            "api_latency",
            "model_inference_time",
            "token_usage",
            "error_rate",
            "throughput",
            "cost_per_request",
            "memory_usage",
            "gpu_utilization",
            "cache_hit_rate",
            "queue_depth"
        ]
        
        # Generate time series data
        metrics = []
        for i in range(metric_count):
            timestamp = datetime.utcnow() - timedelta(
                days=random.randint(0, time_range_days),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            
            metric_type = random.choice(metric_types)
            
            # Generate realistic values based on metric type
            if metric_type == "api_latency":
                value = random.gauss(150, 50)  # ms
            elif metric_type == "model_inference_time":
                value = random.gauss(500, 150)  # ms
            elif metric_type == "token_usage":
                value = random.randint(100, 10000)
            elif metric_type == "error_rate":
                value = random.uniform(0, 0.05)  # 0-5%
            elif metric_type == "throughput":
                value = random.gauss(1000, 300)  # requests/min
            elif metric_type == "cost_per_request":
                value = random.uniform(0.001, 0.1)  # dollars
            elif metric_type == "memory_usage":
                value = random.uniform(60, 95)  # percentage
            elif metric_type == "gpu_utilization":
                value = random.uniform(40, 100)  # percentage
            elif metric_type == "cache_hit_rate":
                value = random.uniform(0.7, 0.99)  # ratio
            else:  # queue_depth
                value = random.randint(0, 1000)
            
            metrics.append({
                "metric_type": metric_type,
                "value": value,
                "timestamp": timestamp,
                "tags": {
                    "environment": "staging",
                    "pr_number": self.pr_number,
                    "region": random.choice(["us-east-1", "us-west-2", "eu-west-1"]),
                    "model": random.choice(["gpt-4", "claude-3", "gemini-pro"]),
                    "user_tier": random.choice(["free", "pro", "enterprise"])
                }
            })
        
        # In a real implementation, you would insert these into your metrics database
        # For now, we'll just track that we created them
        self.created_data["metrics"] = metrics
        print(f"  Created {metric_count} metric data points")
    
    def generate_summary(self) -> Dict:
        """Generate summary of seeded data"""
        return {
            "pr_number": self.pr_number,
            "timestamp": datetime.utcnow().isoformat(),
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
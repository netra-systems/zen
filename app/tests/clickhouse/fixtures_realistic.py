"""
Realistic ClickHouse Test Fixtures
Provides production-like test data for ClickHouse testing
"""

import uuid
import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import asyncio
from dataclasses import dataclass, asdict


@dataclass
class LLMEvent:
    """Realistic LLM event data"""
    timestamp: datetime
    event_id: str
    user_id: int
    workload_id: str
    model: str
    request_id: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_cents: float
    success: bool
    temperature: float
    workload_type: str
    prompt: str
    response: str
    metadata: Dict[str, Any]


@dataclass
class WorkloadMetric:
    """Realistic workload metric data"""
    timestamp: datetime
    user_id: int
    workload_id: str
    metrics: Dict[str, List[Any]]  # name, value, unit arrays
    metadata: Dict[str, Any]


@dataclass
class LogEntry:
    """Realistic log entry data"""
    timestamp: datetime
    level: str
    component: str
    message: str
    metadata: Dict[str, Any]


class RealisticDataGenerator:
    """Generate realistic test data for ClickHouse"""
    
    def __init__(self, seed: Optional[int] = None):
        if seed:
            random.seed(seed)
        
        self.models = ["gpt-4", "gpt-3.5-turbo", "claude-3-opus", "claude-3-sonnet", 
                       "gemini-pro", "gemini-ultra", "llama-70b", "mixtral-8x7b"]
        self.workload_types = ["chat", "completion", "embedding", "analysis", 
                              "rag_pipeline", "code_generation", "summarization"]
        self.components = ["api", "worker", "scheduler", "llm_manager", "agent_supervisor",
                          "websocket_handler", "database", "cache", "queue"]
        self.error_patterns = [
            "Connection timeout to {service}",
            "Rate limit exceeded for {model}",
            "Invalid response format from {component}",
            "Memory allocation failed: {size}MB requested",
            "Database connection pool exhausted",
            "Circuit breaker opened for {service}",
            "Token limit exceeded: {tokens} > {limit}",
            "Authentication failed for user {user_id}",
            "Retry limit reached for operation {op}",
            "Unexpected null value in {field}"
        ]
    
    def generate_llm_events(self, 
                           count: int, 
                           start_time: Optional[datetime] = None,
                           time_span_hours: int = 24) -> List[LLMEvent]:
        """Generate realistic LLM events"""
        if not start_time:
            start_time = datetime.now() - timedelta(hours=time_span_hours)
        
        events = []
        for i in range(count):
            # Realistic time distribution - more events during business hours
            hour_offset = random.random() * time_span_hours
            hour_of_day = (start_time + timedelta(hours=hour_offset)).hour
            
            # Business hours bias
            if 9 <= hour_of_day <= 17:
                time_offset = timedelta(hours=hour_offset)
            else:
                # Less likely during off-hours
                if random.random() > 0.3:
                    continue
                time_offset = timedelta(hours=hour_offset)
            
            timestamp = start_time + time_offset
            model = random.choice(self.models)
            workload_type = random.choice(self.workload_types)
            
            # Realistic token counts based on workload type
            if workload_type == "embedding":
                input_tokens = random.randint(50, 500)
                output_tokens = 0
            elif workload_type == "chat":
                input_tokens = random.randint(100, 1000)
                output_tokens = random.randint(50, 500)
            elif workload_type == "code_generation":
                input_tokens = random.randint(200, 2000)
                output_tokens = random.randint(100, 1500)
            else:
                input_tokens = random.randint(100, 1500)
                output_tokens = random.randint(50, 1000)
            
            # Realistic latency based on model and tokens
            base_latency = {"gpt-4": 2000, "gpt-3.5-turbo": 800, "claude-3-opus": 1500,
                           "gemini-pro": 1000}.get(model.split("-")[0], 1200)
            latency_ms = base_latency + (input_tokens + output_tokens) * 0.5 + random.uniform(-200, 500)
            
            # Cost calculation (simplified but realistic)
            input_cost_per_1k = {"gpt-4": 0.03, "gpt-3.5-turbo": 0.001, 
                                "claude-3-opus": 0.015}.get(model.split("-")[0], 0.01)
            output_cost_per_1k = input_cost_per_1k * 2
            cost_cents = (input_tokens * input_cost_per_1k + output_tokens * output_cost_per_1k) / 10
            
            # 95% success rate with realistic failures
            success = random.random() > 0.05
            
            event = LLMEvent(
                timestamp=timestamp,
                event_id=str(uuid.uuid4()),
                user_id=random.randint(1, 100),
                workload_id=f"wl_{random.randint(1000, 9999)}",
                model=model,
                request_id=str(uuid.uuid4()),
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                cost_cents=cost_cents,
                success=success,
                temperature=random.choice([0.0, 0.3, 0.5, 0.7, 1.0]),
                workload_type=workload_type,
                prompt=f"Sample prompt for {workload_type} task {i}",
                response=f"Sample response for {workload_type} task {i}" if success else "Error: Request failed",
                metadata={
                    "session_id": str(uuid.uuid4()),
                    "api_version": random.choice(["v1", "v2"]),
                    "retry_count": 0 if success else random.randint(1, 3),
                    "cache_hit": random.random() > 0.7
                }
            )
            events.append(event)
        
        return sorted(events, key=lambda x: x.timestamp)
    
    def generate_workload_metrics(self,
                                 count: int,
                                 start_time: Optional[datetime] = None,
                                 interval_seconds: int = 60) -> List[WorkloadMetric]:
        """Generate realistic workload metrics with nested arrays"""
        if not start_time:
            start_time = datetime.now() - timedelta(hours=24)
        
        metrics = []
        workload_ids = [f"wl_{random.randint(1000, 9999)}" for _ in range(10)]
        
        for i in range(count):
            timestamp = start_time + timedelta(seconds=i * interval_seconds)
            
            # Generate correlated metrics
            gpu_util = random.uniform(0, 100)
            memory_usage = 2048 + gpu_util * 50 + random.uniform(-500, 500)
            throughput = gpu_util * 10 + random.uniform(0, 50)
            latency = 100 / max(1, throughput) * 1000  # Inverse relationship
            
            # Add some anomalies
            if random.random() < 0.05:  # 5% anomaly rate
                if random.random() < 0.5:
                    gpu_util = random.uniform(95, 100)  # High GPU
                    memory_usage = random.uniform(7500, 8192)  # High memory
                else:
                    latency = random.uniform(5000, 10000)  # High latency spike
            
            metric = WorkloadMetric(
                timestamp=timestamp,
                user_id=random.randint(1, 100),
                workload_id=random.choice(workload_ids),
                metrics={
                    "name": ["gpu_utilization", "memory_usage", "throughput", "latency_ms", "cost_cents"],
                    "value": [gpu_util, memory_usage, throughput, latency, throughput * 0.01],
                    "unit": ["percent", "MB", "req/s", "ms", "cents"]
                },
                metadata={
                    "node_id": f"node_{random.randint(1, 10)}",
                    "cluster": random.choice(["prod-us-east", "prod-us-west", "prod-eu"]),
                    "version": random.choice(["1.0.0", "1.1.0", "1.2.0"])
                }
            )
            metrics.append(metric)
        
        return metrics
    
    def generate_log_entries(self,
                           count: int,
                           start_time: Optional[datetime] = None,
                           error_rate: float = 0.05) -> List[LogEntry]:
        """Generate realistic log entries with patterns"""
        if not start_time:
            start_time = datetime.now() - timedelta(hours=1)
        
        logs = []
        request_ids = [str(uuid.uuid4()) for _ in range(count // 10)]
        
        for i in range(count):
            # Exponential distribution for more realistic log timing
            time_offset = random.expovariate(1 / 60)  # Average 60 seconds between logs
            timestamp = start_time + timedelta(seconds=min(time_offset, 3600))
            
            # Determine log level with realistic distribution
            rand = random.random()
            if rand < error_rate:
                level = "ERROR"
            elif rand < error_rate * 3:
                level = "WARNING"
            elif rand < 0.3:
                level = "DEBUG"
            else:
                level = "INFO"
            
            component = random.choice(self.components)
            
            # Generate realistic messages
            if level == "ERROR":
                pattern = random.choice(self.error_patterns)
                message = pattern.format(
                    service=random.choice(["redis", "postgres", "clickhouse"]),
                    model=random.choice(self.models),
                    component=component,
                    size=random.randint(100, 8192),
                    tokens=random.randint(5000, 10000),
                    limit=4096,
                    user_id=random.randint(1, 100),
                    op=random.choice(["insert", "update", "delete", "query"]),
                    field=random.choice(["user_id", "workload_id", "metrics"])
                )
            elif level == "WARNING":
                message = random.choice([
                    f"High latency detected: {random.uniform(1000, 5000):.2f}ms",
                    f"Memory usage above threshold: {random.uniform(80, 95):.1f}%",
                    f"Retry attempt {random.randint(1, 3)} for operation",
                    f"Cache miss rate high: {random.uniform(30, 60):.1f}%",
                    f"Queue depth increasing: {random.randint(100, 1000)} messages"
                ])
            elif level == "DEBUG":
                message = random.choice([
                    f"Processing request {random.choice(request_ids)}",
                    f"Cache hit for key: {uuid.uuid4().hex[:8]}",
                    f"Database query executed in {random.uniform(1, 100):.2f}ms",
                    f"WebSocket message sent to {random.randint(1, 50)} clients",
                    f"Background task completed: {random.choice(['cleanup', 'sync', 'backup'])}"
                ])
            else:  # INFO
                message = random.choice([
                    f"Request completed successfully",
                    f"New connection from user {random.randint(1, 100)}",
                    f"Model {random.choice(self.models)} initialized",
                    f"Health check passed",
                    f"Scheduled task started: {random.choice(['metrics', 'cleanup', 'report'])}"
                ])
            
            log = LogEntry(
                timestamp=timestamp,
                level=level,
                component=component,
                message=message,
                metadata={
                    "request_id": random.choice(request_ids),
                    "user_id": random.randint(1, 100),
                    "trace_id": str(uuid.uuid4()),
                    "latency_ms": random.uniform(10, 500) if random.random() > 0.5 else None,
                    "error_code": random.choice(["ERR_001", "ERR_002", "ERR_003"]) if level == "ERROR" else None
                }
            )
            logs.append(log)
        
        return sorted(logs, key=lambda x: x.timestamp)
    
    def generate_corpus_data(self,
                           count: int,
                           workload_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Generate realistic corpus data for training"""
        if not workload_types:
            workload_types = self.workload_types
        
        corpus = []
        
        templates = {
            "chat": [
                ("How do I optimize my {model} usage?", 
                 "To optimize {model} usage, consider: 1) Batch requests, 2) Use appropriate model size, 3) Cache responses"),
                ("What's the best way to reduce latency?",
                 "Reduce latency by: 1) Using edge deployments, 2) Optimizing prompts, 3) Implementing caching"),
            ],
            "code_generation": [
                ("Generate a Python function to {task}",
                 "def {function_name}():\n    # Implementation here\n    pass"),
                ("Write a SQL query to {task}",
                 "SELECT * FROM table WHERE condition;"),
            ],
            "analysis": [
                ("Analyze the performance of {metric}",
                 "Analysis shows {metric} has {trend} trend with {insight}"),
                ("What are the optimization opportunities?",
                 "Key opportunities: 1) {opt1}, 2) {opt2}, 3) {opt3}"),
            ]
        }
        
        for i in range(count):
            workload_type = random.choice(workload_types)
            
            if workload_type in templates:
                prompt_template, response_template = random.choice(templates[workload_type])
                
                # Fill in templates with realistic values
                prompt = prompt_template.format(
                    model=random.choice(self.models),
                    task=random.choice(["process data", "analyze metrics", "generate report"]),
                    metric=random.choice(["latency", "throughput", "cost"])
                )
                
                response = response_template.format(
                    model=random.choice(self.models),
                    function_name=f"optimize_{random.choice(['performance', 'cost', 'quality'])}",
                    task="optimize performance",
                    metric="latency",
                    trend=random.choice(["increasing", "decreasing", "stable"]),
                    insight="correlation with request volume",
                    opt1="Reduce model size",
                    opt2="Implement caching",
                    opt3="Batch requests"
                )
            else:
                prompt = f"Sample {workload_type} prompt {i}"
                response = f"Sample {workload_type} response {i}"
            
            corpus.append({
                "record_id": str(uuid.uuid4()),
                "workload_type": workload_type,
                "prompt": prompt,
                "response": response,
                "metadata": {
                    "quality_score": random.uniform(0.7, 1.0),
                    "tokens": len(prompt.split()) + len(response.split()),
                    "source": random.choice(["production", "synthetic", "curated"])
                },
                "created_at": datetime.now() - timedelta(days=random.randint(0, 30))
            })
        
        return corpus


class ClickHouseTestData:
    """Manage test data for ClickHouse tests"""
    
    def __init__(self):
        self.generator = RealisticDataGenerator(seed=42)
    
    async def insert_test_data(self, client, table_type: str, count: int):
        """Insert test data into ClickHouse"""
        if table_type == "llm_events":
            data = self.generator.generate_llm_events(count)
            await self._insert_llm_events(client, data)
        elif table_type == "workload_events":
            data = self.generator.generate_workload_metrics(count)
            await self._insert_workload_metrics(client, data)
        elif table_type == "logs":
            data = self.generator.generate_log_entries(count)
            await self._insert_logs(client, data)
        elif table_type == "corpus":
            data = self.generator.generate_corpus_data(count)
            await self._insert_corpus(client, data)
    
    async def _insert_llm_events(self, client, events: List[LLMEvent]):
        """Insert LLM events into ClickHouse"""
        # Convert to dictionaries for insertion
        records = [asdict(event) for event in events]
        
        # Format timestamps
        for record in records:
            record['timestamp'] = record['timestamp'].isoformat()
            record['metadata'] = json.dumps(record['metadata'])
        
        # Batch insert
        await client.insert_data("llm_events", records)
    
    async def _insert_workload_metrics(self, client, metrics: List[WorkloadMetric]):
        """Insert workload metrics into ClickHouse"""
        records = []
        for metric in metrics:
            record = {
                'timestamp': metric.timestamp.isoformat(),
                'user_id': metric.user_id,
                'workload_id': metric.workload_id,
                'metrics.name': metric.metrics['name'],
                'metrics.value': metric.metrics['value'],
                'metrics.unit': metric.metrics['unit'],
                'metadata': json.dumps(metric.metadata)
            }
            records.append(record)
        
        await client.insert_data("workload_events", records)
    
    async def _insert_logs(self, client, logs: List[LogEntry]):
        """Insert log entries into ClickHouse"""
        records = []
        for log in logs:
            record = {
                'timestamp': log.timestamp.isoformat(),
                'level': log.level,
                'component': log.component,
                'message': log.message,
                'metadata': json.dumps(log.metadata)
            }
            records.append(record)
        
        await client.insert_data("netra_app_internal_logs", records)
    
    async def _insert_corpus(self, client, corpus: List[Dict]):
        """Insert corpus data into ClickHouse"""
        for record in corpus:
            record['metadata'] = json.dumps(record['metadata'])
            record['created_at'] = record['created_at'].isoformat()
        
        await client.insert_data("corpus_table", corpus)
    
    def get_sample_queries(self) -> Dict[str, str]:
        """Get sample queries for testing"""
        return {
            "llm_cost_by_model": """
                SELECT model, sum(cost_cents) as total_cost
                FROM llm_events
                WHERE timestamp >= now() - INTERVAL 1 DAY
                GROUP BY model
                ORDER BY total_cost DESC
            """,
            "workload_anomalies": """
                WITH baseline AS (
                    SELECT avg(arrayElement(metrics.value, 
                        arrayFirstIndex(x -> x = 'latency_ms', metrics.name))) as avg_latency
                    FROM workload_events
                    WHERE timestamp >= now() - INTERVAL 1 HOUR
                )
                SELECT * FROM workload_events
                WHERE arrayElement(metrics.value, 
                    arrayFirstIndex(x -> x = 'latency_ms', metrics.name)) > 
                    (SELECT avg_latency * 2 FROM baseline)
            """,
            "error_patterns": """
                SELECT 
                    component,
                    count() as error_count,
                    groupArray(message)[1:5] as sample_errors
                FROM netra_app_internal_logs
                WHERE level = 'ERROR'
                GROUP BY component
                ORDER BY error_count DESC
            """
        }


# Pytest fixtures
@pytest.fixture
async def clickhouse_test_data():
    """Provide test data manager"""
    return ClickHouseTestData()


@pytest.fixture
async def realistic_llm_events():
    """Generate realistic LLM events"""
    generator = RealisticDataGenerator()
    return generator.generate_llm_events(100)


@pytest.fixture
async def realistic_workload_metrics():
    """Generate realistic workload metrics"""
    generator = RealisticDataGenerator()
    return generator.generate_workload_metrics(100)


@pytest.fixture
async def realistic_logs():
    """Generate realistic log entries"""
    generator = RealisticDataGenerator()
    return generator.generate_log_entries(1000)


@pytest.fixture
async def realistic_corpus():
    """Generate realistic corpus data"""
    generator = RealisticDataGenerator()
    return generator.generate_corpus_data(50)
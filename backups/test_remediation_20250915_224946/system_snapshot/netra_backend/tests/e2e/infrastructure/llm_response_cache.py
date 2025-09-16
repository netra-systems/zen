"""
LLM Response Cache - SQLite-based caching with TTL management

Provides persistent caching for LLM responses with TTL management, statistics tracking,
and cache invalidation methods. Follows 450-line/25-line limits.
"""
import asyncio
import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

class CacheEntry(BaseModel):
    """Cache entry structure."""
    key: str
    data: Dict[str, Any]
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None

class CacheStatistics(BaseModel):
    """Cache statistics structure."""
    total_entries: int = 0
    hits: int = 0
    misses: int = 0
    expired_entries: int = 0
    total_size_bytes: int = 0
    hit_rate: float = 0.0

class LLMResponseCache:
    """SQLite-based cache for LLM responses with TTL management."""
    
    def __init__(self, db_path: Optional[str] = None, default_ttl_hours: int = 24):
        self.db_path = db_path or self._get_default_db_path()
        self.default_ttl_hours = default_ttl_hours
        self._stats = CacheStatistics()
        self._initialize_database()
        
    def _get_default_db_path(self) -> str:
        """Get default database path."""
        cache_dir = Path("app/tests/e2e/cache")
        cache_dir.mkdir(parents=True, exist_ok=True)
        return str(cache_dir / "llm_response_cache.db")
        
    def _initialize_database(self):
        """Initialize SQLite database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            self._create_cache_table(conn)
            self._create_statistics_table(conn)
            self._load_initial_statistics(conn)
            
    def _create_cache_table(self, conn: sqlite3.Connection):
        """Create cache table."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                key TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP
            )
        """)
        
    def _create_statistics_table(self, conn: sqlite3.Connection):
        """Create statistics table."""
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cache_statistics (
                id INTEGER PRIMARY KEY,
                hits INTEGER DEFAULT 0,
                misses INTEGER DEFAULT 0,
                expired_entries INTEGER DEFAULT 0
            )
        """)
        
    def _load_initial_statistics(self, conn: sqlite3.Connection):
        """Load or initialize statistics."""
        cursor = conn.execute("SELECT hits, misses, expired_entries FROM cache_statistics WHERE id = 1")
        row = cursor.fetchone()
        if row:
            self._stats.hits, self._stats.misses, self._stats.expired_entries = row
        else:
            conn.execute("INSERT INTO cache_statistics (id, hits, misses, expired_entries) VALUES (1, 0, 0, 0)")
            
    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached entry by key."""
        with sqlite3.connect(self.db_path) as conn:
            return await self._get_cached_entry(conn, key)
            
    async def _get_cached_entry(self, conn: sqlite3.Connection, key: str) -> Optional[Dict[str, Any]]:
        """Get cached entry from database."""
        cursor = conn.execute("""
            SELECT data, expires_at, access_count 
            FROM cache_entries 
            WHERE key = ? AND expires_at > ?
        """, (key, datetime.now(UTC)))
        
        row = cursor.fetchone()
        if row:
            self._update_access_stats(conn, key, row[2])
            self._stats.hits += 1
            self._update_statistics_in_db(conn)
            return json.loads(row[0])
        else:
            self._stats.misses += 1
            self._update_statistics_in_db(conn)
            return None
            
    def _update_access_stats(self, conn: sqlite3.Connection, key: str, current_count: int):
        """Update access statistics for entry."""
        conn.execute("""
            UPDATE cache_entries 
            SET access_count = ?, last_accessed = ? 
            WHERE key = ?
        """, (current_count + 1, datetime.now(UTC), key))
        
    def _update_statistics_in_db(self, conn: sqlite3.Connection):
        """Update statistics in database."""
        conn.execute("""
            UPDATE cache_statistics 
            SET hits = ?, misses = ?, expired_entries = ? 
            WHERE id = 1
        """, (self._stats.hits, self._stats.misses, self._stats.expired_entries))
        
    async def set(self, key: str, data: Dict[str, Any], ttl_hours: Optional[int] = None) -> bool:
        """Set cache entry with TTL."""
        ttl_hours = ttl_hours or self.default_ttl_hours
        expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)
        
        with sqlite3.connect(self.db_path) as conn:
            return self._insert_cache_entry(conn, key, data, expires_at)
            
    def _insert_cache_entry(self, conn: sqlite3.Connection, key: str, data: Dict[str, Any], expires_at: datetime) -> bool:
        """Insert cache entry into database."""
        try:
            conn.execute("""
                INSERT OR REPLACE INTO cache_entries 
                (key, data, created_at, expires_at, access_count, last_accessed)
                VALUES (?, ?, ?, ?, 0, NULL)
            """, (key, json.dumps(data), datetime.now(UTC), expires_at))
            return True
        except sqlite3.Error:
            return False
            
    async def delete(self, key: str) -> bool:
        """Delete specific cache entry."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
            return cursor.rowcount > 0
            
    async def clear_expired(self) -> int:
        """Clear expired entries and return count."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM cache_entries WHERE expires_at <= ?", (datetime.now(UTC),))
            expired_count = cursor.rowcount
            self._stats.expired_entries += expired_count
            self._update_statistics_in_db(conn)
            return expired_count
            
    async def clear_all(self) -> int:
        """Clear all cache entries and return count."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM cache_entries")
            total_count = cursor.fetchone()[0]
            conn.execute("DELETE FROM cache_entries")
            return total_count
            
    async def get_entries_by_pattern(self, pattern: str) -> List[str]:
        """Get cache keys matching pattern."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT key FROM cache_entries WHERE key LIKE ?", (f"%{pattern}%",))
            return [row[0] for row in cursor.fetchall()]
            
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics."""
        with sqlite3.connect(self.db_path) as conn:
            total_entries = self._get_total_entries(conn)
            total_size = self._get_total_size(conn)
            
        hit_rate = self._stats.hits / max(self._stats.hits + self._stats.misses, 1)
        
        return {
            "total_entries": total_entries,
            "hits": self._stats.hits,
            "misses": self._stats.misses,
            "expired_entries": self._stats.expired_entries,
            "hit_rate": round(hit_rate, 3),
            "total_size_bytes": total_size,
            "database_path": self.db_path
        }
        
    def _get_total_entries(self, conn: sqlite3.Connection) -> int:
        """Get total number of cache entries."""
        cursor = conn.execute("SELECT COUNT(*) FROM cache_entries WHERE expires_at > ?", (datetime.now(UTC),))
        return cursor.fetchone()[0]
        
    def _get_total_size(self, conn: sqlite3.Connection) -> int:
        """Get total cache size in bytes."""
        cursor = conn.execute("SELECT SUM(LENGTH(data)) FROM cache_entries WHERE expires_at > ?", (datetime.now(UTC),))
        result = cursor.fetchone()[0]
        return result if result else 0
        
    async def cleanup_old_entries(self, max_age_days: int = 7) -> int:
        """Clean up entries older than specified days."""
        cutoff_date = datetime.now(UTC) - timedelta(days=max_age_days)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM cache_entries WHERE created_at < ?", (cutoff_date,))
            return cursor.rowcount
            
    def reset_statistics(self):
        """Reset all statistics."""
        self._stats = CacheStatistics()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE cache_statistics SET hits = 0, misses = 0, expired_entries = 0 WHERE id = 1")
            
    def generate_cache_key(self, prompt: str, model: str, **kwargs) -> str:
        """Generate consistent cache key from parameters."""
        key_components = [prompt, model]
        key_components.extend(f"{k}:{v}" for k, v in sorted(kwargs.items()))
        content = ":".join(key_components)
        return hashlib.sha256(content.encode()).hexdigest()[:32]
        
    async def validate_cache_integrity(self) -> Dict[str, Any]:
        """Validate cache integrity and return report."""
        with sqlite3.connect(self.db_path) as conn:
            return self._perform_integrity_check(conn)
            
    def _perform_integrity_check(self, conn: sqlite3.Connection) -> Dict[str, Any]:
        """Perform integrity check on cache database."""
        issues = []
        total_entries = 0
        corrupted_entries = 0
        
        cursor = conn.execute("SELECT key, data FROM cache_entries")
        for row in cursor.fetchall():
            total_entries += 1
            try:
                json.loads(row[1])
            except json.JSONDecodeError:
                issues.append(f"Corrupted JSON data for key: {row[0]}")
                corrupted_entries += 1
                
        return {
            "total_entries": total_entries,
            "corrupted_entries": corrupted_entries,
            "issues": issues,
            "integrity_score": (total_entries - corrupted_entries) / max(total_entries, 1)
        }
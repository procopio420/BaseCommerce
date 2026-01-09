"""
Pytest configuration for integration tests.

Sets up fixtures for database and Redis connections.
"""

import os
import sys

# Add project paths to sys.path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(project_root, "packages", "basecore", "src"))
sys.path.insert(0, os.path.join(project_root, "packages", "engines_core", "src"))
sys.path.insert(0, os.path.join(project_root, "apps", "outbox-relay", "src"))
sys.path.insert(0, os.path.join(project_root, "backend"))

# Set environment variables for tests
os.environ.setdefault("DATABASE_URL", "postgresql://construcao_user:construcao_pass@localhost:5432/construcao_db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("SECRET_KEY", "test-secret-key")


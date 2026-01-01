"""Tests for src/ml_pipeline/common.py utility functions."""

import os
from unittest.mock import patch

from src.ml_pipeline.common import (
    create_directories,
    get_localstack_endpoint,
    get_mlflow_tracking_uri,
    get_postgres_connection_string,
    get_size,
    read_yaml,
)


class TestReadYaml:
    """Tests for read_yaml function."""

    def test_read_yaml(self, tmp_path):
        """Test reading a valid YAML file."""
        d = tmp_path / "configs"
        d.mkdir()
        p = d / "test.yaml"
        p.write_text("key: value")

        content = read_yaml(str(p))
        assert content == {"key": "value"}

    def test_read_yaml_nested(self, tmp_path):
        """Test reading a nested YAML file."""
        p = tmp_path / "nested.yaml"
        p.write_text("parent:\n  child: value\n  number: 42")

        content = read_yaml(str(p))
        assert content == {"parent": {"child": "value", "number": 42}}


class TestCreateDirectories:
    """Tests for create_directories function."""

    def test_create_directories(self, tmp_path):
        """Test creating directories."""
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2" / "nested"

        create_directories([str(dir1), str(dir2)])

        assert dir1.exists()
        assert dir2.exists()


class TestGetSize:
    """Tests for get_size function."""

    def test_get_size(self, tmp_path):
        """Test getting file size."""
        p = tmp_path / "test.txt"
        p.write_text("a" * 2048)  # 2KB file

        size = get_size(str(p))
        assert "2 KB" in size


class TestServiceEndpoints:
    """Tests for service endpoint functions (bare-metal mode)."""

    def test_get_localstack_endpoint_default(self):
        """Test default LocalStack endpoint."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_localstack_endpoint() == "http://localhost:4566"

    def test_get_localstack_endpoint_from_env(self):
        """Test LocalStack endpoint from environment variable."""
        with patch.dict(os.environ, {"AWS_ENDPOINT_URL": "http://custom:9000"}):
            assert get_localstack_endpoint() == "http://custom:9000"

    def test_get_mlflow_tracking_uri_default(self):
        """Test default MLflow tracking URI."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_mlflow_tracking_uri() == "http://localhost:5001"

    def test_get_mlflow_tracking_uri_from_env(self):
        """Test MLflow tracking URI from environment variable."""
        with patch.dict(os.environ, {"MLFLOW_TRACKING_URI": "http://custom:8080"}):
            assert get_mlflow_tracking_uri() == "http://custom:8080"

    def test_get_postgres_connection_string_default(self):
        """Test default PostgreSQL connection string."""
        with patch.dict(os.environ, {}, clear=True):
            conn = get_postgres_connection_string()
            assert "localhost:5432" in conn
            assert "mlflow" in conn

    def test_get_postgres_connection_string_from_env(self):
        """Test PostgreSQL connection string from environment variables."""
        env = {
            "POSTGRES_HOST": "custom-host",
            "POSTGRES_PORT": "5433",
            "POSTGRES_USER": "user",
            "POSTGRES_PASSWORD": "pass",
            "POSTGRES_DB": "mydb",
        }
        with patch.dict(os.environ, env):
            conn = get_postgres_connection_string()
            assert "custom-host:5433" in conn
            assert "user:pass" in conn
            assert "mydb" in conn

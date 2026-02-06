"""Tests to verify the redis[hiredis] dependency is installed and functional."""

import pytest


@pytest.mark.unit
class TestRedisDependency:
    def test_redis_importable(self):
        import redis

        assert hasattr(redis, "Redis")

    def test_hiredis_importable(self):
        import hiredis

        assert hasattr(hiredis, "Reader")

    def test_redis_has_hiredis_parser(self):
        from redis._parsers import _HiredisParser

        assert _HiredisParser is not None

    def test_redis_version(self):
        import redis

        major = int(redis.__version__.split(".")[0])
        assert major >= 5

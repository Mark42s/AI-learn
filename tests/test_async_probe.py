"""D4：异步并发的 3 个单测。用 asyncio.run 包同步测试函数，免装 pytest-asyncio。"""
from __future__ import annotations

import asyncio
from typing import Iterator

import pytest

from log_analyzer.async_probe import delay_server, probe, probe_serial


@pytest.fixture
def base_url() -> Iterator[str]:
    with delay_server() as base:
        yield base


def _urls(base: str, n: int = 10) -> list[str]:
    return [f"{base}/?i={i}" for i in range(n)]


def test_ten_urls_all_ok(base_url: str) -> None:
    report = asyncio.run(probe(_urls(base_url)))
    assert len(report.items) == 10
    assert report.ok == 10 and report.failed == 0
    assert all(item.status == 200 and item.error is None for item in report.items)


def test_concurrent_is_faster_than_serial(base_url: str) -> None:
    urls = _urls(base_url)
    serial = asyncio.run(probe_serial(urls))
    concurrent = asyncio.run(probe(urls, concurrency=10))
    # 10 路各等 200ms：串行约 2000ms，并发约 200ms，留足余量防 CI 抖动
    assert concurrent.total_ms < serial.total_ms * 0.5
    assert serial.ok == concurrent.ok == 10


def test_bad_url_is_reported_not_raised(base_url: str) -> None:
    urls = _urls(base_url, 3) + ["http://127.0.0.1:1/nope"]
    report = asyncio.run(probe(urls))
    assert report.ok == 3 and report.failed == 1
    assert any(item.error for item in report.items)

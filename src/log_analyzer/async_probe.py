"""D4：asyncio + httpx 并发探测。

对着 epoll 看：
    事件循环        ≈ epoll_create + while(1) epoll_wait(...)
    await           ≈ EAGAIN 之后把控制权交回 loop（唯一的让出点）
    create_task     ≈ 把 fd 注册进 epoll
    gather          ≈ 等一组 fd 全部就绪
    Semaphore(n)    ≈ 并发上限 / 连接池

默认用本地模拟服务（离线、每个请求 200ms I/O 等待）做串行 vs 并发对照；
也可以直接传任意 URL：python -m log_analyzer.async_probe <url...>
"""
from __future__ import annotations

import asyncio
import json
import sys
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Iterator

import httpx

DELAY = 0.2  # 每个请求模拟 200ms 的 I/O 等待


def _ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000


@dataclass(frozen=True, slots=True)
class ProbeItem:
    url: str
    status: int | None
    elapsed_ms: float
    error: str | None = None


@dataclass(slots=True)
class ProbeReport:
    items: list[ProbeItem] = field(default_factory=list)
    total_ms: float = 0.0
    ok: int = 0
    failed: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "total_ms": round(self.total_ms, 1),
            "ok": self.ok,
            "failed": self.failed,
            "items": [asdict(i) for i in self.items],
        }


def _report(items: list[ProbeItem], t0: float) -> ProbeReport:
    ok = sum(i.status == 200 for i in items)
    return ProbeReport(items=items, total_ms=_ms(t0), ok=ok, failed=len(items) - ok)


async def fetch_one(
    client: httpx.AsyncClient, url: str, sem: asyncio.Semaphore
) -> ProbeItem:
    """单个请求。失败不抛给 gather，而是变成一条结构化结果（延续 D3 的分流）。"""
    t0 = time.perf_counter()
    try:
        async with sem:  # 限流，防止一次打爆下游
            response = await client.get(url, timeout=5.0)
        return ProbeItem(url=url, status=response.status_code, elapsed_ms=round(_ms(t0), 1))
    except (httpx.HTTPError, OSError) as e:
        return ProbeItem(
            url=url, status=None, elapsed_ms=round(_ms(t0), 1),
            error=f"{type(e).__name__}: {e}",
        )


async def probe(urls: list[str], *, concurrency: int = 10) -> ProbeReport:
    """并发请求一组 URL，统计总耗时。"""
    t0 = time.perf_counter()
    sem = asyncio.Semaphore(concurrency)
    async with httpx.AsyncClient() as client:
        items = await asyncio.gather(
            *(fetch_one(client, url, sem) for url in urls)
        )
    return _report(list(items), t0)


async def probe_serial(urls: list[str]) -> ProbeReport:
    """串行基线：用来证明并发确实快，而不是「感觉快」。"""
    t0 = time.perf_counter()
    sem = asyncio.Semaphore(1)
    async with httpx.AsyncClient() as client:
        items = [await fetch_one(client, url, sem) for url in urls]
    return _report(items, t0)


class _DelayHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        time.sleep(DELAY)  # 故意用同步 sleep：服务端每请求一个线程，不阻塞客户端的 loop
        body = b'{"ok": true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args: object) -> None:
        pass  # 不打访问日志


@contextmanager
def delay_server() -> Iterator[str]:
    """起一个本地延迟服务，端口由 OS 分配，用完自动关。"""
    server = ThreadingHTTPServer(("127.0.0.1", 0), _DelayHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


async def _demo() -> None:
    with delay_server() as base:
        urls = [f"{base}/?i={i}" for i in range(10)]
        serial = await probe_serial(urls)
        concurrent = await probe(urls, concurrency=10)

    print("10 个 URL · 每个请求模拟 200ms I/O 等待 · 本地离线服务")
    print(f"串行基线 : {serial.total_ms:8.1f} ms   ok={serial.ok} failed={serial.failed}")
    print(f"并发(10) : {concurrent.total_ms:8.1f} ms   ok={concurrent.ok} failed={concurrent.failed}")
    print(f"加速比   : {serial.total_ms / concurrent.total_ms:8.2f} x")
    print(f"单项耗时 : {[round(i.elapsed_ms) for i in concurrent.items]} ms")


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    if args:
        report = asyncio.run(probe(args, concurrency=10))
        print(json.dumps(report.to_dict(), ensure_ascii=False, indent=2))
    else:
        asyncio.run(_demo())


if __name__ == "__main__":
    main()

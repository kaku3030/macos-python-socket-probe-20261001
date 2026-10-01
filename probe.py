#!/usr/bin/env python3
"""Generic, local-only macOS Python socket/HTTPServer probe."""

import argparse
import json
import os
import platform
import socket
import socketserver
import subprocess
import sys
import time
from http.server import HTTPServer

STEPS = {
    "raw_bind": "A",
    "tcp_server_bind": "B",
    "getfqdn": "C",
    "http_server_bind": "D",
    "getaddrinfo": "E",
    "gethostbyaddr": "F",
}
TIMEOUT_SECONDS = 15


def now():
    return time.monotonic()


def emit(kind, **fields):
    print(json.dumps({"kind": kind, "monotonic": now(), **fields}, sort_keys=True), flush=True)


def run_step(name):
    emit("stage", marker=f"{STEPS[name]}_START", step=name)
    if name == "raw_bind":
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", 0))
        finally:
            sock.close()
    elif name == "tcp_server_bind":
        server = socketserver.TCPServer(("127.0.0.1", 0), socketserver.BaseRequestHandler, bind_and_activate=False)
        try:
            server.server_bind()
        finally:
            server.server_close()
    elif name == "getfqdn":
        socket.getfqdn("127.0.0.1")
    elif name == "http_server_bind":
        server = HTTPServer(("127.0.0.1", 0), None, bind_and_activate=False)
        try:
            server.server_bind()
        finally:
            server.server_close()
    elif name == "getaddrinfo":
        socket.getaddrinfo("127.0.0.1", 0)
    elif name == "gethostbyaddr":
        socket.gethostbyaddr("127.0.0.1")
    emit("stage", marker=f"{STEPS[name]}_DONE", step=name)


def child_main(name):
    try:
        run_step(name)
    except BaseException as exc:
        emit("error", step=name, error_type=type(exc).__name__, error=str(exc))
        raise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--step", choices=STEPS)
    args = parser.parse_args()
    if args.step:
        child_main(args.step)
        return 0

    result = {
        "probe": "generic-macos-python-socket-httpserver",
        "pid": os.getpid(),
        "platform": platform.platform(),
        "python": sys.version,
        "python_implementation": platform.python_implementation(),
        "timeout_seconds": TIMEOUT_SECONDS,
        "steps": [],
    }
    emit("probe_start", **{k: v for k, v in result.items() if k != "steps"})
    for name in STEPS:
        started = now()
        completed = False
        output = ""
        error = None
        proc = subprocess.Popen(
            [sys.executable, __file__, "--step", name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            output, _ = proc.communicate(timeout=TIMEOUT_SECONDS)
            completed = proc.returncode == 0
        except subprocess.TimeoutExpired:
            proc.kill()
            output, _ = proc.communicate()
            error = "watchdog_timeout"
        elapsed = now() - started
        record = {
            "step": name,
            "label": STEPS[name],
            "completed": completed,
            "returncode": proc.returncode,
            "elapsed_seconds": elapsed,
            "watchdog": TIMEOUT_SECONDS,
            "output": output,
        }
        if error:
            record["error"] = error
        result["steps"].append(record)
        emit("step_result", **record)
    result["monotonic_end"] = now()
    with open("probe-result.json", "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
    emit("probe_end", result_file="probe-result.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

import threading


_lock = threading.Lock()
_requests = {}
_durations = {}


def record_request(method: str, status: int, seconds: float):
    key = (method, status)
    with _lock:
        _requests[key] = _requests.get(key, 0) + 1
        count, total = _durations.get(key, (0, 0.0))
        _durations[key] = (count + 1, total + seconds)


def render_metrics() -> str:
    with _lock:
        requests = dict(_requests)
        durations = dict(_durations)

    lines = ["# TYPE share_text_http_requests_total counter"]
    for (method, status), count in requests.items():
        lines.append(
            f'share_text_http_requests_total{{method="{method}",status="{status}"}} {count}'
        )

    lines.append("# TYPE share_text_http_request_duration_seconds summary")
    for (method, status), (count, total) in durations.items():
        labels = f'method="{method}",status="{status}"'
        lines.append(f'share_text_http_request_duration_seconds_count{{{labels}}} {count}')
        lines.append(f'share_text_http_request_duration_seconds_sum{{{labels}}} {total:.6f}')
    return "\n".join(lines) + "\n"

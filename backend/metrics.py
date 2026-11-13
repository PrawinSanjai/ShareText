import threading


_BUCKETS = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
_lock = threading.Lock()
_requests = {}
_durations = {}


def record_request(method: str, route: str, status: int, duration: float):
    labels = (method, route, str(status))
    with _lock:
        _requests[labels] = _requests.get(labels, 0) + 1
        count, total, buckets = _durations.get(labels, (0, 0.0, [0] * len(_BUCKETS)))
        for index, bound in enumerate(_BUCKETS):
            if duration <= bound:
                buckets[index] += 1
        _durations[labels] = (count + 1, total + duration, buckets)


def render_metrics() -> str:
    lines = [
        "# HELP share_text_http_requests_total Total HTTP requests handled by this process.",
        "# TYPE share_text_http_requests_total counter",
    ]
    with _lock:
        requests = list(_requests.items())
        durations = list(_durations.items())

    for (method, route, status), count in requests:
        lines.append(
            f'share_text_http_requests_total{{method="{method}",route="{route}",status="{status}"}} {count}'
        )

    lines.extend([
        "# HELP share_text_http_request_duration_seconds HTTP request latency in seconds.",
        "# TYPE share_text_http_request_duration_seconds histogram",
    ])
    for (method, route, status), (count, total, buckets) in durations:
        label_prefix = f'method="{method}",route="{route}",status="{status}"'
        for index, bound in enumerate(_BUCKETS):
            lines.append(
                f'share_text_http_request_duration_seconds_bucket{{{label_prefix},le="{bound:g}"}} {buckets[index]}'
            )
        lines.append(
            f'share_text_http_request_duration_seconds_bucket{{{label_prefix},le="+Inf"}} {count}'
        )
        lines.append(
            f'share_text_http_request_duration_seconds_sum{{{label_prefix}}} {total:.9f}'
        )
        lines.append(
            f'share_text_http_request_duration_seconds_count{{{label_prefix}}} {count}'
        )
    return "\n".join(lines) + "\n"

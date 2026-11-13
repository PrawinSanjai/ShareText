import http from "k6/http";
import { check } from "k6";
import { Counter } from "k6/metrics";

const baseUrl = (__ENV.BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const rate = Number(__ENV.RATE || 20);
const duration = __ENV.DURATION || "30s";
const oneTimeWinners = new Counter("one_time_successful_reads");

http.setResponseCallback(http.expectedStatuses(200, 404));

export const options = {
  scenarios: {
    create_and_read: {
      executor: "constant-arrival-rate",
      rate,
      timeUnit: "1s",
      duration,
      preAllocatedVUs: Math.max(20, rate),
      maxVUs: Math.max(100, rate * 5),
      exec: "createAndRead",
    },
    race_one_time_link: {
      executor: "constant-arrival-rate",
      startTime: "2s",
      rate: Math.max(10, rate),
      timeUnit: "1s",
      duration,
      preAllocatedVUs: Math.max(20, rate),
      maxVUs: Math.max(100, rate * 5),
      exec: "raceOneTimeLink",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<750"],
    dropped_iterations: ["count==0"],
    one_time_successful_reads: ["count==1"],
  },
};

function createOneTimeShare() {
  const response = http.post(
    `${baseUrl}/text/store`,
    JSON.stringify({ text: "concurrency-check", ttl_hours: 1, max_views: 1 }),
    { headers: { "Content-Type": "application/json" } },
  );
  check(response, {
    "share created": (res) => res.status === 200 && Boolean(res.json("text_id")),
  });
  return response.status === 200 ? response.json("text_id") : null;
}

export function setup() {
  const textId = createOneTimeShare();
  if (!textId) throw new Error("Could not create the shared one-time link for the race scenario.");
  return { textId };
}

export function createAndRead() {
  const textId = createOneTimeShare();
  if (!textId) return;

  const response = http.post(
    `${baseUrl}/text/${encodeURIComponent(textId)}/read`,
    JSON.stringify({}),
    { headers: { "Content-Type": "application/json" } },
  );
  check(response, {
    "created link is readable once": (res) => res.status === 200 && res.json("result") === "concurrency-check",
  });
}

export function raceOneTimeLink(data) {
  const response = http.post(
    `${baseUrl}/text/${encodeURIComponent(data.textId)}/read`,
    JSON.stringify({}),
    { headers: { "Content-Type": "application/json" } },
  );
  if (response.status === 200) oneTimeWinners.add(1);
  check(response, {
    "one-time link has only a valid winner or an exhausted response": (res) => res.status === 200 || res.status === 404,
  });
}

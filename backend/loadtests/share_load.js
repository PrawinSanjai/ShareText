import http from "k6/http";
import { check } from "k6";
import { Counter } from "k6/metrics";

const baseUrl = (__ENV.BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const winners = new Counter("one_time_successful_reads");

http.setResponseCallback(http.expectedStatuses(200, 404));

export const options = {
  vus: Number(__ENV.VUS || 50),
  duration: __ENV.DURATION || "30s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<750"],
    one_time_successful_reads: ["count==1"],
  },
};

function createOneTimeShare() {
  const response = http.post(
    `${baseUrl}/text/store`,
    JSON.stringify({ text: "load-test", ttl_hours: 1, max_views: 1 }),
    { headers: { "Content-Type": "application/json" } },
  );
  check(response, { "share created": (res) => res.status === 200 });
  return response.status === 200 ? response.json("text_id") : null;
}

export function setup() {
  const textId = createOneTimeShare();
  if (!textId) throw new Error("Could not create the one-time share.");
  return { textId };
}

export default function (data) {
  const ownTextId = createOneTimeShare();
  if (ownTextId) {
    const ownRead = http.post(
      `${baseUrl}/text/${encodeURIComponent(ownTextId)}/read`,
      "{}",
      { headers: { "Content-Type": "application/json" } },
    );
    check(ownRead, { "new share can be read": (res) => res.status === 200 });
  }

  const competingRead = http.post(
    `${baseUrl}/text/${encodeURIComponent(data.textId)}/read`,
    "{}",
    { headers: { "Content-Type": "application/json" } },
  );
  if (competingRead.status === 200) winners.add(1);
  check(competingRead, { "one-time link allows only a winner or exhausted read": (res) => res.status === 200 || res.status === 404 });
}

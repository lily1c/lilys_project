import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

const errorRate = new Rate('errors');

export const options = {
  stages: [
    { duration: '30s', target: 200 }, // Ramping up to Silver (200)
    { duration: '1m',  target: 500 }, // Ramping up to Gold (500)
    { duration: '30s', target: 0   }, // Cool down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // Needs to be FAST (under 500ms)
    errors: ['rate<0.002'],           // Needs to be STABLE (under 0.2%)
  },
};

const BASE_URL = 'http://localhost:5006';

const URLS = [
  'https://github.com',
  'https://google.com',
  'https://stackoverflow.com',
];

export default function () {
  http.get(`${BASE_URL}/health`);

  const res = http.post(
    `${BASE_URL}/shorten`,
    JSON.stringify({ url: URLS[Math.floor(Math.random() * URLS.length)] }),
    { headers: { 'Content-Type': 'application/json' } }
  );

  const ok = check(res, { 'status 201': (r) => r.status === 201 });
  errorRate.add(!ok);

  if (ok) {
    const shortCode = JSON.parse(res.body).short_code;
    http.get(`${BASE_URL}/${shortCode}`, { redirects: 0 });
  }

  sleep(0.5);
}

export function handleSummary(data) {
  const p95 = data.metrics.http_req_duration.values['p(95)'];
  const errPct = data.metrics.errors ? data.metrics.errors.values.rate * 100 : 0;
  const vus = data.metrics.vus_max.values.max;

  console.log('\n========================================');
  console.log('        🚀 LOAD TEST RESULTS 🚀        ');
  console.log('========================================');
  console.log(`Max VUs:        ${vus}`);
  console.log(`P95 Latency:    ${p95.toFixed(2)}ms`);
  console.log(`Error Rate:     ${errPct.toFixed(2)}%`);
  console.log('========================================');

  if (vus >= 500 && errPct < 0.2) {
    console.log('🥇 GOLD TIER ACHIEVED!');
  } else if (vus >= 200 && errPct < 1.0) {
    console.log('🥈 SILVER TIER ACHIEVED!');
  } else if (vus >= 50 && errPct < 10) {
    console.log('🥉 BRONZE TIER ACHIEVED!');
  } else {
    console.log('❌ Tier requirements not met');
  }
  console.log('========================================\n');

  return { 'stdout': '' };
}

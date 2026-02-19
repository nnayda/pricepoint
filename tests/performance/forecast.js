// ML forecast endpoint load test
//
// Simulates 10 concurrent users submitting POST /api/forecast requests
// with Wake County addresses. This endpoint geocodes the address, builds
// features, and runs the ML model, so the P95 threshold is 2000 ms.

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '2m',
  thresholds: {
    http_req_duration: ['p(95)<2000'],
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Realistic Wake County addresses for forecast requests
const ADDRESSES = [
  {
    address: '100 Clendenen Ct',
    city: 'Cary',
    state: 'NC',
    zip_code: '27513',
  },
  {
    address: '200 Fayetteville St',
    city: 'Raleigh',
    state: 'NC',
    zip_code: '27601',
  },
  {
    address: '1000 Colonnade Dr',
    city: 'Cary',
    state: 'NC',
    zip_code: '27518',
  },
  {
    address: '401 Oberlin Rd',
    city: 'Raleigh',
    state: 'NC',
    zip_code: '27605',
  },
  {
    address: '1100 Walnut St',
    city: 'Cary',
    state: 'NC',
    zip_code: '27511',
  },
  {
    address: '500 Glenwood Ave',
    city: 'Raleigh',
    state: 'NC',
    zip_code: '27603',
  },
  {
    address: '2000 Regency Pkwy',
    city: 'Cary',
    state: 'NC',
    zip_code: '27518',
  },
  {
    address: '800 NW Maynard Rd',
    city: 'Cary',
    state: 'NC',
    zip_code: '27513',
  },
];

export default function () {
  const addr = ADDRESSES[Math.floor(Math.random() * ADDRESSES.length)];

  const res = http.post(
    `${BASE_URL}/api/forecast`,
    JSON.stringify(addr),
    {
      headers: { 'Content-Type': 'application/json' },
    },
  );

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response has predicted_value': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.predicted_value !== undefined;
      } catch {
        return false;
      }
    },
  });

  // Longer think time for forecast — heavier endpoint
  sleep(Math.random() * 3 + 1);
}

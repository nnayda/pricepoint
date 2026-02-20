// Geocode endpoint load test
//
// Simulates 50 concurrent users looking up Wake County, NC addresses
// via GET /api/geocode for 2 minutes. The P95 response time threshold
// is 300 ms and the error rate must stay below 1%.

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 50,
  duration: '2m',
  thresholds: {
    http_req_duration: ['p(95)<300'],
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Realistic Wake County, NC addresses and partial queries
const QUERIES = [
  '100 Clendenen Ct, Cary, NC',
  '200 Fayetteville St, Raleigh, NC',
  '1000 Colonnade Dr, Cary, NC 27518',
  '300 E Davie St, Raleigh, NC 27601',
  '5000 Centregreen Way, Cary, NC',
  '150 Fayetteville St, Raleigh, NC 27601',
  '1100 Walnut St, Cary, NC 27511',
  '401 Oberlin Rd, Raleigh, NC 27605',
  '2000 Regency Pkwy, Cary, NC 27518',
  '500 Glenwood Ave, Raleigh, NC 27603',
  '1200 E Maynard Rd, Cary, NC 27513',
  '3000 Hillsborough St, Raleigh, NC',
  '800 NW Maynard Rd, Cary, NC 27513',
  '4325 Glenwood Ave, Raleigh, NC 27612',
  '100 Weston Pkwy, Cary, NC 27513',
];

export default function () {
  const query = QUERIES[Math.floor(Math.random() * QUERIES.length)];
  const url = `${BASE_URL}/api/geocode?q=${encodeURIComponent(query)}&limit=5`;

  const res = http.get(url);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response has results array': (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.results);
      } catch {
        return false;
      }
    },
  });

  // Simulate user think time between requests
  sleep(Math.random() * 2 + 0.5);
}

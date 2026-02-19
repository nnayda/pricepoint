// Property details endpoint load test
//
// Simulates 30 concurrent users fetching property details via
// GET /api/property for 2 minutes. Uses sample coordinates around
// the Raleigh/Cary area. P95 threshold is 500 ms.

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 30,
  duration: '2m',
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Realistic Wake County, NC coordinates with addresses
const PROPERTIES = [
  { lat: 35.7796, lon: -78.6382, address: '200 Fayetteville St, Raleigh, NC 27601' },
  { lat: 35.7915, lon: -78.7811, address: '100 Clendenen Ct, Cary, NC 27513' },
  { lat: 35.8302, lon: -78.6414, address: '4325 Glenwood Ave, Raleigh, NC 27612' },
  { lat: 35.7587, lon: -78.7747, address: '1100 Walnut St, Cary, NC 27511' },
  { lat: 35.7721, lon: -78.6389, address: '300 E Davie St, Raleigh, NC 27601' },
  { lat: 35.8101, lon: -78.7582, address: '1000 Colonnade Dr, Cary, NC 27518' },
  { lat: 35.8007, lon: -78.6603, address: '401 Oberlin Rd, Raleigh, NC 27605' },
  { lat: 35.7662, lon: -78.7419, address: '800 NW Maynard Rd, Cary, NC 27513' },
  { lat: 35.7872, lon: -78.6698, address: '500 Glenwood Ave, Raleigh, NC 27603' },
  { lat: 35.8145, lon: -78.7663, address: '2000 Regency Pkwy, Cary, NC 27518' },
];

export default function () {
  const prop = PROPERTIES[Math.floor(Math.random() * PROPERTIES.length)];
  const url =
    `${BASE_URL}/api/property` +
    `?lat=${prop.lat}&lon=${prop.lon}` +
    `&address=${encodeURIComponent(prop.address)}`;

  const res = http.get(url);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response has property object': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.property !== undefined;
      } catch {
        return false;
      }
    },
  });

  sleep(Math.random() * 2 + 0.5);
}

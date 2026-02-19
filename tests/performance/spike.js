// Spike test — sudden traffic surge across all endpoints
//
// Ramps from 0 to 100 virtual users in 30 seconds, sustains for
// 1 minute, then ramps back down over 30 seconds. Exercises all
// major API endpoints. The primary threshold is error rate < 1%.

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 100 },  // Ramp up to 100 users
    { duration: '1m', target: 100 },   // Sustain 100 users
    { duration: '30s', target: 0 },    // Ramp down to 0
  ],
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<3000'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Sample data for each endpoint
const GEOCODE_QUERIES = [
  '100 Clendenen Ct, Cary, NC',
  '200 Fayetteville St, Raleigh, NC',
  '1000 Colonnade Dr, Cary, NC 27518',
  '300 E Davie St, Raleigh, NC 27601',
  '5000 Centregreen Way, Cary, NC',
];

const PROPERTIES = [
  { lat: 35.7796, lon: -78.6382, address: '200 Fayetteville St, Raleigh, NC 27601' },
  { lat: 35.7915, lon: -78.7811, address: '100 Clendenen Ct, Cary, NC 27513' },
  { lat: 35.8302, lon: -78.6414, address: '4325 Glenwood Ave, Raleigh, NC 27612' },
];

const LOCATIONS = [
  { lat: 35.7796, lon: -78.6382 },
  { lat: 35.7915, lon: -78.7811 },
  { lat: 35.8302, lon: -78.6414 },
];

const FORECAST_ADDRS = [
  { address: '100 Clendenen Ct', city: 'Cary', state: 'NC', zip_code: '27513' },
  { address: '200 Fayetteville St', city: 'Raleigh', state: 'NC', zip_code: '27601' },
];

export default function () {
  // Randomly pick one of the four endpoint categories
  const endpoint = Math.floor(Math.random() * 4);

  switch (endpoint) {
    case 0: {
      // Geocode
      const q = GEOCODE_QUERIES[Math.floor(Math.random() * GEOCODE_QUERIES.length)];
      const res = http.get(`${BASE_URL}/api/geocode?q=${encodeURIComponent(q)}&limit=5`);
      check(res, { 'geocode: 200': (r) => r.status === 200 });
      break;
    }
    case 1: {
      // Property
      const prop = PROPERTIES[Math.floor(Math.random() * PROPERTIES.length)];
      const url =
        `${BASE_URL}/api/property` +
        `?lat=${prop.lat}&lon=${prop.lon}` +
        `&address=${encodeURIComponent(prop.address)}`;
      const res = http.get(url);
      check(res, { 'property: 200': (r) => r.status === 200 });
      break;
    }
    case 2: {
      // Crime or POIs
      const loc = LOCATIONS[Math.floor(Math.random() * LOCATIONS.length)];
      if (Math.random() < 0.5) {
        const res = http.get(
          `${BASE_URL}/api/crime?lat=${loc.lat}&lon=${loc.lon}&radius_miles=1.0&days_back=365`,
        );
        check(res, { 'crime: 200': (r) => r.status === 200 });
      } else {
        const res = http.get(
          `${BASE_URL}/api/pois?lat=${loc.lat}&lon=${loc.lon}&radius_miles=2.0`,
        );
        check(res, { 'pois: 200': (r) => r.status === 200 });
      }
      break;
    }
    case 3: {
      // Forecast
      const addr = FORECAST_ADDRS[Math.floor(Math.random() * FORECAST_ADDRS.length)];
      const res = http.post(
        `${BASE_URL}/api/forecast`,
        JSON.stringify(addr),
        { headers: { 'Content-Type': 'application/json' } },
      );
      check(res, { 'forecast: 200': (r) => r.status === 200 });
      break;
    }
  }

  sleep(Math.random() * 1.5 + 0.3);
}

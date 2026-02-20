// Spatial queries (crime and POIs) load test
//
// Simulates 20 concurrent users hitting GET /api/crime and GET /api/pois
// with coordinates in the Wake County area. These endpoints run PostGIS
// spatial queries, so the P95 threshold is a more generous 800 ms.

import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 20,
  duration: '2m',
  thresholds: {
    http_req_duration: ['p(95)<800'],
    http_req_failed: ['rate<0.01'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

// Coordinates spread across the Raleigh/Cary metro area
const LOCATIONS = [
  { lat: 35.7796, lon: -78.6382 },  // Downtown Raleigh
  { lat: 35.7915, lon: -78.7811 },  // Cary
  { lat: 35.8302, lon: -78.6414 },  // North Raleigh
  { lat: 35.7587, lon: -78.7747 },  // South Cary
  { lat: 35.7721, lon: -78.6389 },  // East Raleigh
  { lat: 35.8145, lon: -78.7663 },  // West Cary
  { lat: 35.8401, lon: -78.6827 },  // Brier Creek
  { lat: 35.7350, lon: -78.8500 },  // Morrisville
];

export default function () {
  const loc = LOCATIONS[Math.floor(Math.random() * LOCATIONS.length)];

  // Alternate between crime and POI requests
  if (Math.random() < 0.5) {
    // Crime endpoint
    const crimeUrl =
      `${BASE_URL}/api/crime` +
      `?lat=${loc.lat}&lon=${loc.lon}` +
      `&radius_miles=1.0&days_back=365`;

    const crimeRes = http.get(crimeUrl);

    check(crimeRes, {
      'crime: status is 200': (r) => r.status === 200,
      'crime: response has incidents': (r) => {
        try {
          const body = JSON.parse(r.body);
          return Array.isArray(body.incidents);
        } catch {
          return false;
        }
      },
    });
  } else {
    // POIs endpoint
    const poisUrl =
      `${BASE_URL}/api/pois` +
      `?lat=${loc.lat}&lon=${loc.lon}` +
      `&radius_miles=2.0`;

    const poisRes = http.get(poisUrl);

    check(poisRes, {
      'pois: status is 200': (r) => r.status === 200,
      'pois: response has pois array': (r) => {
        try {
          const body = JSON.parse(r.body);
          return Array.isArray(body.pois);
        } catch {
          return false;
        }
      },
    });
  }

  sleep(Math.random() * 2 + 0.5);
}

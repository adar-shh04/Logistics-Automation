import http from 'k6/http';
import { check } from 'k6';

const binFile = open('./fixtures/test_invoice.png', 'b');
const targetRate = Number(__ENV.RATE || 5);
const testDuration = __ENV.DURATION || '60s';
const baseUrl = __ENV.BASE_URL || 'http://api:8000';

export const options = {
  scenarios: {
    api_rate_scenario: {
      executor: 'constant-arrival-rate',
      rate: targetRate,
      timeUnit: '1s',
      duration: testDuration,
      preAllocatedVUs: Math.max(10, targetRate * 2),
      maxVUs: Math.max(50, targetRate * 5),
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
};

export default function () {
  const data = {
    file: http.file(binFile, 'test_invoice.png', 'image/png'),
  };

  const res = http.post(`${baseUrl}/upload`, data);

  check(res, {
    'status is 200': (r) => r.status === 200,
    'has document_id': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body && body.document_id !== undefined;
      } catch (e) {
        return false;
      }
    },
  });
}

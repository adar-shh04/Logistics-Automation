import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Counter } from 'k6/metrics';

const binFile = open('./fixtures/test_invoice.png', 'b');
const totalJobs = Number(__ENV.N || 300);
const baseUrl = __ENV.BASE_URL || 'http://api:8000';
const numVUs = Number(__ENV.VUS || 25);

const jobEndToEndDuration = new Trend('job_e2e_duration_ms', true);
const jobsCompleted = new Counter('jobs_completed_total');
const jobsFailed = new Counter('jobs_failed_total');

export const options = {
  scenarios: {
    batch_drain: {
      executor: 'shared-iterations',
      vus: numVUs,
      iterations: totalJobs,
      maxDuration: '15m',
    },
  },
  thresholds: {
    jobs_failed_total: ['count==0'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
};

export default function () {
  const uploadStart = Date.now();

  const data = {
    file: http.file(binFile, 'test_invoice.png', 'image/png'),
  };

  const uploadRes = http.post(`${baseUrl}/upload`, data);
  const uploadOk = check(uploadRes, {
    'upload status is 200': (r) => r.status === 200,
  });

  if (!uploadOk) {
    jobsFailed.add(1);
    return;
  }

  let uid = '';
  try {
    const body = JSON.parse(uploadRes.body);
    uid = body.document_id;
  } catch (e) {
    jobsFailed.add(1);
    return;
  }

  // Poll loop: every 250ms until completed, failed, or 15m timeout
  let completed = false;
  let failed = false;
  const maxPollTimeMs = 15 * 60 * 1000;

  while (!completed && !failed && (Date.now() - uploadStart < maxPollTimeMs)) {
    sleep(0.25);
    const statusRes = http.get(`${baseUrl}/status/${uid}`);
    if (statusRes.status === 200) {
      try {
        const body = JSON.parse(statusRes.body);
        if (body.status === 'completed') {
          completed = true;
          break;
        } else if (body.status === 'failed') {
          failed = true;
          break;
        }
      } catch (e) {
        // Continue polling
      }
    }
  }

  const durationMs = Date.now() - uploadStart;
  jobEndToEndDuration.add(durationMs);

  check(completed, {
    'job reached completed state': (c) => c === true,
  });

  if (completed) {
    jobsCompleted.add(1);
  } else {
    jobsFailed.add(1);
  }
}

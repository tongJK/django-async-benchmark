import http from 'k6/http';
import { check, group, sleep } from 'k6';
import { Trend } from 'k6/metrics';
import { textSummary } from 'https://jslib.k6.io/k6-summary/0.1.0/index.js';

// Custom metrics per scenario
const syncIOTrend = new Trend('sync_io_duration');
const asyncIOTrend = new Trend('async_io_duration');
const syncDBTrend = new Trend('sync_db_duration');
const asyncDBTrend = new Trend('async_db_duration');
const syncMixedTrend = new Trend('sync_mixed_duration');
const asyncMixedTrend = new Trend('async_mixed_duration');
const syncCPUTrend = new Trend('sync_cpu_duration');
const asyncCPUTrend = new Trend('async_cpu_duration');

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const options = {
    stages: [
        { duration: '10s', target: 5 },   // ramp up
        { duration: '30s', target: 5 },   // steady
        { duration: '10s', target: 0 },   // ramp down
    ],
    thresholds: {
        http_req_duration: ['p(95)<10000'],  // 95% under 10s (external APIs are slow)
        http_req_failed: ['rate<0.1'],       // less than 10% failure
    },
};

function hitEndpoint(name, path, trend) {
    const res = http.get(`${BASE_URL}${path}`);
    check(res, {
        [`${name} status 200`]: (r) => r.status === 200,
        [`${name} body not empty`]: (r) => r.body.length > 0,
    });
    trend.add(res.timings.duration);
    return res;
}

export default function () {
    group('I/O Bound', () => {
        hitEndpoint('sync-io', '/api/v1/sync/io-bound/', syncIOTrend);
        hitEndpoint('async-io', '/api/v1/async/io-bound/', asyncIOTrend);
    });

    group('DB Bound', () => {
        hitEndpoint('sync-db', '/api/v1/sync/db-bound/', syncDBTrend);
        hitEndpoint('async-db', '/api/v1/async/db-bound/', asyncDBTrend);
    });

    group('Mixed', () => {
        hitEndpoint('sync-mixed', '/api/v1/sync/mixed/', syncMixedTrend);
        hitEndpoint('async-mixed', '/api/v1/async/mixed/', asyncMixedTrend);
    });

    group('CPU Bound', () => {
        hitEndpoint('sync-cpu', '/api/v1/sync/cpu-bound/', syncCPUTrend);
        hitEndpoint('async-cpu', '/api/v1/async/cpu-bound/', asyncCPUTrend);
    });

    sleep(1);
}

// Custom summary — outputs both console text and JSON file
export function handleSummary(data) {
    // Build comparison table
    const pairs = [
        ['I/O Bound', 'sync_io_duration', 'async_io_duration'],
        ['DB Bound', 'sync_db_duration', 'async_db_duration'],
        ['Mixed', 'sync_mixed_duration', 'async_mixed_duration'],
        ['CPU Bound', 'sync_cpu_duration', 'async_cpu_duration'],
    ];

    let table = '\n╔══════════════════════════════════════════════════════════╗\n';
    table += '║           SYNC vs ASYNC BENCHMARK RESULTS              ║\n';
    table += '╠════════════╦══════════╦══════════╦══════════╦══════════╣\n';
    table += '║ Scenario   ║ Sync p50 ║ Async p50║ Speedup  ║ Winner   ║\n';
    table += '╠════════════╬══════════╬══════════╬══════════╬══════════╣\n';

    for (const [name, syncKey, asyncKey] of pairs) {
        const syncP50 = data.metrics[syncKey]?.values?.med || 0;
        const asyncP50 = data.metrics[asyncKey]?.values?.med || 0;
        const speedup = asyncP50 > 0 ? (syncP50 / asyncP50).toFixed(1) : 'N/A';
        const winner = syncP50 < asyncP50 ? 'Sync' : asyncP50 < syncP50 ? 'Async' : 'Tie';

        table += `║ ${name.padEnd(10)} ║ ${(syncP50.toFixed(0) + 'ms').padEnd(8)} ║ ${(asyncP50.toFixed(0) + 'ms').padEnd(8)} ║ ${(speedup + 'x').padEnd(8)} ║ ${winner.padEnd(8)} ║\n`;
    }

    table += '╚════════════╩══════════╩══════════╩══════════╩══════════╝\n';

    return {
        stdout: textSummary(data, { indent: ' ', enableColors: true }) + table,
        'k6/summary.json': JSON.stringify(data, null, 2),
    };
}

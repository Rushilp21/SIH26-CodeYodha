const { test } = require('node:test');
const assert = require('node:assert/strict');
const ts = require('typescript');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');
const filename = path.resolve(__dirname, '../src/data/dashboardMetrics.ts');
const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
});
const adapter = new Module(filename, module);
adapter._compile(compiled.outputText, filename);
const { dashboardMetrics } = adapter.exports;

test('dashboard uses backend statuses, not confidence-derived approvals', () => {
  const metrics = dashboardMetrics([
    { status: 'needs_review', confidence_score: .99 },
    { status: 'verified', confidence_score: 0 },
    { status: 'ai_processed', confidence_score: null },
  ], [
    { parcel_id: 'a', status: 'pending' }, { parcel_id: 'a', status: 'assigned' },
    { parcel_id: 'b', status: 'completed' },
  ]);
  assert.equal(metrics.total, 3);
  assert.equal(metrics.verified, 1);
  assert.equal(metrics.needsReview, 1);
  assert.equal(metrics.fieldPending, 1);
  assert.equal(metrics.averageConfidence, .495);
  assert.equal(dashboardMetrics([], []).averageConfidence, null);
});

test('production sources do not reference the prototype mock data or activity adapter', () => {
  const root = path.resolve(__dirname, '../src');
  function scan(dir) {
    for (const item of fs.readdirSync(dir, { withFileTypes: true })) {
      const file = path.join(dir, item.name);
      if (item.isDirectory()) scan(file);
      else if (/\.(tsx?|jsx?)$/.test(file)) {
        const source = fs.readFileSync(file, 'utf8');
        assert.doesNotMatch(source, /demoDashboardActivity|mockData|CONF_SEED|CITY_CENTER|P-0\d{3}/, file);
        assert.doesNotMatch(source, /Model v2\.4|● Active|78\.4%|1248|autoApproved:\s*847/, file);
      }
    }
  }
  scan(root);
});

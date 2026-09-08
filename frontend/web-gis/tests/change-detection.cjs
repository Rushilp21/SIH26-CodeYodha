const { test } = require('node:test');
const assert = require('node:assert/strict');
const ts = require('typescript');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');

// Load the pure adapter using the project's compiler without adding a test dependency.
const filename = path.resolve(__dirname, '../src/data/changeDetection.ts');
const compiled = ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
});
const adapter = new Module(filename, module);
adapter._compile(compiled.outputText, filename);
const { joinChangeEvents, topologyErrors, changeDate } = adapter.exports;

test('joins only exact parcel IDs, preserves duplicate events and all priorities', () => {
  const changes = [
    { parcel_id: 'a', type: 'boundary_shift', magnitude: 0.3, detected_at: null },
    { parcel_id: 'a', type: 'boundary_shift', magnitude: 0.3, detected_at: null },
    { parcel_id: 'missing', type: 'topology_break', magnitude: 1, detected_at: null },
  ];
  const parcel = { id: 'a', geom: { type: 'Polygon', coordinates: [[[1, 2], [2, 2], [1, 3], [1, 2]]] } };
  const queue = [
    { parcel_id: 'a', priority_score: 0.2 },
    { parcel_id: 'other', priority_score: 10 },
    { parcel_id: 'a', priority_score: 0.8 },
  ];
  const rows = joinChangeEvents(changes, [parcel], queue);
  assert.equal(rows[0].parcel, parcel);
  assert.equal(rows[2].parcel, null);
  assert.equal(new Set(rows.map(row => row.key)).size, 3);
  assert.deepEqual(rows[0].queue.map(item => item.priority_score), [0.8, 0.2]);
  assert.deepEqual(queue.map(item => item.priority_score), [0.2, 10, 0.8]);
});

test('topology errors come from typed anomaly events, not negated prose or confidence', () => {
  const events = [{ type: 'boundary_shift', magnitude: 0.9 }, { type: 'topology_break', magnitude: 1 }, { type: 'overlap', magnitude: 0.2 }];
  assert.deepEqual(topologyErrors(events).map(item => item.type), ['topology_break', 'overlap']);
  assert.deepEqual(topologyErrors([]), []);
});

test('missing and malformed survey dates do not fabricate a historical date', () => {
  assert.equal(changeDate(null), 'Date unavailable');
  assert.equal(changeDate('bad date'), 'Date unavailable');
});

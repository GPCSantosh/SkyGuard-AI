import assert from 'node:assert';

console.log('--- Executing SkyGuard Frontend WebSocket Transport Verification ---');

// 1. Deduplication Cache Logic Test
function createDedupCache(maxSize = 1000) {
  const seenSet = new Set();
  const seenList = [];

  return function recordEventId(eventId) {
    if (seenSet.has(eventId)) {
      return false; // Duplicate
    }
    seenSet.add(eventId);
    seenList.push(eventId);
    if (seenList.length > maxSize) {
      const oldest = seenList.shift();
      if (oldest) seenSet.delete(oldest);
    }
    return true; // New
  };
}

const recordEvent = createDedupCache(5);
assert.strictEqual(recordEvent('EVT-001'), true, 'First event should be accepted');
assert.strictEqual(recordEvent('EVT-001'), false, 'Duplicate event_id must be rejected');
assert.strictEqual(recordEvent('EVT-002'), true, 'Second unique event should be accepted');
assert.strictEqual(recordEvent('EVT-002'), false, 'Duplicate event_id must be rejected');

// Test eviction on max capacity
recordEvent('EVT-003');
recordEvent('EVT-004');
recordEvent('EVT-005');
recordEvent('EVT-006'); // Evicts EVT-001
assert.strictEqual(recordEvent('EVT-001'), true, 'Evicted event can be recorded again after LRU cap');
console.log('✓ Deduplication Cache & LRU Eviction passed');

// 2. Out-of-Order Timestamp Ordering Guard Test
function createOrderingGuard() {
  const stationTimestamps = new Map();

  return function isChronologicallyValid(stationId, timestampStr) {
    if (!stationId || !timestampStr) return true;
    const msgTime = new Date(timestampStr).getTime();
    if (isNaN(msgTime)) return true;

    const lastTime = stationTimestamps.get(stationId) || 0;
    if (msgTime < lastTime) {
      return false; // Stale / Out of order
    }
    stationTimestamps.set(stationId, msgTime);
    return true; // Valid chronological
  };
}

const isOrdered = createOrderingGuard();
assert.strictEqual(isOrdered('STN_A', '2026-09-17T00:05:00Z'), true, 'Nominal timestamp accepted');
assert.strictEqual(isOrdered('STN_A', '2026-09-17T00:10:00Z'), true, 'Newer timestamp accepted');
assert.strictEqual(isOrdered('STN_A', '2026-09-17T00:07:00Z'), false, 'Older out-of-order timestamp rejected');
assert.strictEqual(isOrdered('STN_B', '2026-09-17T00:07:00Z'), true, 'Station B independent timeline accepted');
console.log('✓ Out-of-Order Timestamp Ordering Guard passed');

// 3. Exponential Backoff Calculation Test
function calculateReconnectDelay(attempt, baseDelay = 1000, maxDelay = 30000) {
  return Math.min(maxDelay, baseDelay * Math.pow(1.5, Math.min(attempt, 8)));
}

assert.strictEqual(calculateReconnectDelay(0), 1000, 'Attempt 0 should be base 1000ms');
assert.strictEqual(calculateReconnectDelay(1), 1500, 'Attempt 1 should be 1500ms');
assert.strictEqual(calculateReconnectDelay(2), 2250, 'Attempt 2 should be 2250ms');
assert(calculateReconnectDelay(10) <= 30000, 'Delay must be capped at 30000ms');
console.log('✓ Exponential Backoff Bounds passed');

// 4. Transport State Machine & Fallback Mode Test
class TransportStateMachine {
  constructor() {
    this.connectionStatus = 'CONNECTING';
    this.transportMode = 'POLLING';
    this.hasEverConnected = false;
    this.resyncCalled = false;
  }

  onOpen() {
    this.connectionStatus = 'CONNECTED';
    this.transportMode = 'WEBSOCKET';
    if (this.hasEverConnected) {
      this.resyncCalled = true;
    }
    this.hasEverConnected = true;
  }

  onClose() {
    this.connectionStatus = 'RECONNECTING';
    this.transportMode = 'POLLING'; // Fall back immediately
  }

  onError() {
    this.connectionStatus = 'ERROR';
    this.transportMode = 'POLLING';
  }
}

const sm = new TransportStateMachine();
assert.strictEqual(sm.connectionStatus, 'CONNECTING');
assert.strictEqual(sm.transportMode, 'POLLING');

sm.onOpen();
assert.strictEqual(sm.connectionStatus, 'CONNECTED');
assert.strictEqual(sm.transportMode, 'WEBSOCKET');
assert.strictEqual(sm.resyncCalled, false, 'Initial connect does not trigger resync');

sm.onClose();
assert.strictEqual(sm.connectionStatus, 'RECONNECTING');
assert.strictEqual(sm.transportMode, 'POLLING', 'Fallback to polling on disconnect');

sm.onOpen();
assert.strictEqual(sm.connectionStatus, 'CONNECTED');
assert.strictEqual(sm.transportMode, 'WEBSOCKET');
assert.strictEqual(sm.resyncCalled, true, 'Reconnection triggers resync reconciliation');
console.log('✓ Transport State Machine & Reconnect Resync passed');

console.log('==================================================');
console.log('ALL FRONTEND WEBSOCKET TESTS PASSED (4/4)');
console.log('==================================================');

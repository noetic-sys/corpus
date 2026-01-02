import PQueue from 'p-queue'

/**
 * Global request queue to prevent thundering herd when loading large matrices.
 * Limits concurrent API requests to prevent overwhelming the backend.
 *
 * Backend rate limits (per IP):
 * - 10/second burst
 * - 300/minute sustained (5/sec average)
 *
 * We stay just under the burst limit to avoid hitting 429s while maximizing throughput.
 */
export const requestQueue = new PQueue({
  concurrency: 50,    // Allow many parallel requests
  intervalCap: 9,     // Stay just under backend's 10/sec burst limit
  interval: 1000,     // Per second - CRITICAL: Yields to event loop every second
})

/**
 * Queue a request to be executed with concurrency control.
 */
export async function queueRequest<T>(fn: () => Promise<T>): Promise<T> {
  return requestQueue.add(fn) as Promise<T>
}

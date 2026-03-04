const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_KEY = import.meta.env.VITE_API_KEY || 'dev-api-key-change-me';

const headers = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
};

/**
 * Execute code asynchronously (returns immediately with execution_id)
 */
export async function executeCode({ code, language, version, stdin, timeout, dependencies }) {
    const res = await fetch(`${API_URL}/api/v1/execute`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ code, language, version, stdin, timeout, dependencies }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Execution failed');
    }
    return res.json();
}

/**
 * Execute code synchronously (waits for result)
 */
export async function executeCodeSync({ code, language, version, stdin, timeout, dependencies }) {
    const res = await fetch(`${API_URL}/api/v1/execute/sync`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ code, language, version, stdin, timeout, dependencies }),
    });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Execution failed');
    }
    return res.json();
}

/**
 * Get execution result by ID
 */
export async function getExecution(executionId) {
    const res = await fetch(`${API_URL}/api/v1/executions/${executionId}`, { headers });
    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Not found');
    }
    return res.json();
}

/**
 * List recent executions
 */
export async function listExecutions(limit = 20) {
    const res = await fetch(`${API_URL}/api/v1/executions?limit=${limit}`, { headers });
    if (!res.ok) return [];
    return res.json();
}

/**
 * Get supported languages
 */
export async function getLanguages() {
    const res = await fetch(`${API_URL}/api/v1/languages`);
    if (!res.ok) return [];
    return res.json();
}

/**
 * Health check
 */
export async function getHealth() {
    try {
        const res = await fetch(`${API_URL}/health`);
        if (!res.ok) return { status: 'unreachable' };
        return res.json();
    } catch {
        return { status: 'unreachable' };
    }
}

/**
 * Poll execution until complete
 */
export async function pollExecution(executionId, onUpdate, intervalMs = 500, maxAttempts = 120) {
    for (let i = 0; i < maxAttempts; i++) {
        const result = await getExecution(executionId);
        onUpdate(result);
        if (['completed', 'failed', 'timeout'].includes(result.status)) {
            return result;
        }
        await new Promise((r) => setTimeout(r, intervalMs));
    }
    throw new Error('Polling timed out');
}

const API_BASE_URL = 'http://127.0.0.1:8000';

const resolveRequestTimeout = () => {
    const env = typeof import.meta !== 'undefined' ? import.meta.env : undefined;
    const configured = env?.VITE_API_TIMEOUT_MS;
    const parsed = Number.parseInt(configured, 10);
    if (Number.isFinite(parsed) && parsed > 0) {
        return parsed;
    }
    return 15000;
};

const REQUEST_TIMEOUT_MS = resolveRequestTimeout(); // default to 15s, overridable via Vite env

class ApiError extends Error {
    constructor(message, status) {
        super(message);
        this.status = status;
        this.name = 'ApiError';
    }
}

async function handleResponse(response) {
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new ApiError(
            errorData.message || 'An error occurred',
            response.status
        );
    }
    return response.json();
}

async function fetchWithTimeout(url, options = {}, timeout = REQUEST_TIMEOUT_MS) {
    console.log('[fetchWithTimeout] Starting fetch to:', url);
    console.log('[fetchWithTimeout] Timeout:', timeout, 'ms');
    console.log('[fetchWithTimeout] Options:', options);
    
    const controller = new AbortController();
    const startTime = Date.now();
    const timeoutId = setTimeout(() => {
        const elapsed = Date.now() - startTime;
        console.error('[fetchWithTimeout] ⏰ TIMEOUT! Aborting after', elapsed, 'ms');
        controller.abort();
    }, timeout);

    try {
        console.log('[fetchWithTimeout] Calling fetch...');
        const response = await fetch(url, { ...options, signal: controller.signal });
        const elapsed = Date.now() - startTime;
        console.log('[fetchWithTimeout] ✓ Fetch completed in', elapsed, 'ms');
        return response;
    } catch (error) {
        const elapsed = Date.now() - startTime;
        console.error('[fetchWithTimeout] ✗ Fetch error after', elapsed, 'ms');
        console.error('[fetchWithTimeout] Error name:', error.name);
        console.error('[fetchWithTimeout] Error:', error);
        
        if (error.name === 'AbortError') {
            console.error('[fetchWithTimeout] Request was aborted (timeout)');
            throw new ApiError('Request timed out', 408);
        }
        throw error;
    } finally {
        clearTimeout(timeoutId);
        console.log('[fetchWithTimeout] Timeout cleared');
    }
}

export const apiService = {
    async getConversationHistory(workflowId = null) {
        try {
            const url = workflowId 
                ? `${API_BASE_URL}/get-conversation-history?workflow_id=${encodeURIComponent(workflowId)}`
                : `${API_BASE_URL}/get-conversation-history`;
            const res = await fetchWithTimeout(url);
            return handleResponse(res);
        } catch (error) {
            if (error instanceof ApiError) {
                throw error;
            }
            throw new ApiError(
                'Failed to fetch conversation history',
                error.status || 500
            );
        }
    },

    async sendMessage(message) {
        if (!message?.trim()) {
            throw new ApiError('Message cannot be empty', 400);
        }

        try {
            const res = await fetchWithTimeout(
                `${API_BASE_URL}/send-prompt?prompt=${encodeURIComponent(message)}`,
                { 
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );
            return handleResponse(res);
        } catch (error) {
            if (error instanceof ApiError) {
                throw error;
            }
            throw new ApiError(
                'Failed to send message',
                error.status || 500
            );
        }
    },

    async startWorkflow() {
        try {
            const res = await fetchWithTimeout(
                `${API_BASE_URL}/start-workflow`,
                { 
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                }
            );
            return handleResponse(res);
        } catch (error) {
            if (error instanceof ApiError) {
                throw error;
            }
            throw new ApiError(
                'Failed to start workflow',
                error.status || 500
            );
        }
    },

    async confirm(workflowId = null) {
        try {
            const url = workflowId
                ? `${API_BASE_URL}/confirm?workflow_id=${encodeURIComponent(workflowId)}`
                : `${API_BASE_URL}/confirm`;
            const res = await fetchWithTimeout(url, { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            return handleResponse(res);
        } catch (error) {
            if (error instanceof ApiError) {
                throw error;
            }
            throw new ApiError(
                'Failed to confirm action',
                error.status || 500
            );
        }
    },

    async initiateVoiceCall({ phoneNumber, goal, context }) {
        console.log('[initiateVoiceCall] Starting request with:', { phoneNumber, goal, context });
        
        if (!phoneNumber?.trim()) {
            throw new ApiError('Phone number is required', 400);
        }
        if (!goal?.trim()) {
            throw new ApiError('Goal is required', 400);
        }
        if (!context?.trim()) {
            throw new ApiError('Context is required', 400);
        }

        try {
            console.log('[initiateVoiceCall] Validation passed, preparing request...');
            const url = `${API_BASE_URL}/api/v1/voice-initiate`;
            const payload = {
                phone_number: phoneNumber,
                goal: goal,
                context: context
            };
            
            console.log('[initiateVoiceCall] URL:', url);
            console.log('[initiateVoiceCall] Payload:', payload);
            console.log('[initiateVoiceCall] Timeout:', REQUEST_TIMEOUT_MS, 'ms');
            console.log('[initiateVoiceCall] Sending fetch request...');
            
            const startTime = Date.now();
            const res = await fetchWithTimeout(
                url,
                { 
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(payload)
                }
            );
            const fetchTime = Date.now() - startTime;
            console.log('[initiateVoiceCall] Fetch completed in', fetchTime, 'ms');
            
            console.log('[initiateVoiceCall] Response status:', res.status);
            console.log('[initiateVoiceCall] Parsing response...');
            
            const result = await handleResponse(res);
            console.log('[initiateVoiceCall] Success! Result:', result);
            return result;
        } catch (error) {
            const elapsed = Date.now();
            console.error('[initiateVoiceCall] Error after', elapsed, 'ms');
            console.error('[initiateVoiceCall] Error type:', error.name);
            console.error('[initiateVoiceCall] Error message:', error.message);
            console.error('[initiateVoiceCall] Error status:', error.status);
            console.error('[initiateVoiceCall] Full error:', error);
            
            if (error instanceof ApiError) {
                throw error;
            }
            throw new ApiError(
                'Failed to initiate voice call',
                error.status || 500
            );
        }
    },

    async getVoiceCallStatus(workflowId) {
        if (!workflowId?.trim()) {
            throw new ApiError('Workflow ID is required', 400);
        }

        try {
            const res = await fetchWithTimeout(
                `${API_BASE_URL}/voice-call-status/${workflowId}`
            );
            return handleResponse(res);
        } catch (error) {
            if (error instanceof ApiError) {
                throw error;
            }
            throw new ApiError(
                'Failed to get voice call status',
                error.status || 500
            );
        }
    }
}; 

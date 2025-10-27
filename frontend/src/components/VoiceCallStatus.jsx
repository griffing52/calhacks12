import React, { useState, useEffect } from "react";

/**
 * Real-time status display for voice calls
 * Shows progress through different stages of the call
 */
export default function VoiceCallStatus({ workflowId, onClose, apiService }) {
    const [status, setStatus] = useState({
        stage: 'initiating',
        message: 'Preparing to initiate call...',
        details: null,
        timestamp: new Date()
    });
    const [error, setError] = useState(null);
    const [callConnected, setCallConnected] = useState(false);
    const [pendingQuestion, setPendingQuestion] = useState(null);
    const [userAnswer, setUserAnswer] = useState('');
    const [submittingAnswer, setSubmittingAnswer] = useState(false);

    // Status polling
    useEffect(() => {
        if (!workflowId || !apiService) return;

        let mounted = true;
        let pollCount = 0;
        const maxPolls = 60; // Poll for up to 2 minutes (60 * 2 seconds)

        const pollStatus = async () => {
            if (!mounted || pollCount >= maxPolls) return;

            try {
                const result = await apiService.getVoiceCallStatus(workflowId);
                
                if (!mounted) return;

                pollCount++;

                // Update status based on workflow state
                if (result.status === 'RUNNING') {
                    // Check for pending questions from voice AI
                    if (result.voice_status?.info_needed && result.voice_status?.pending_question) {
                        setPendingQuestion(result.voice_status.pending_question);
                        setStatus({
                            stage: 'needs_info',
                            message: '❓ Agent needs clarification',
                            details: result.voice_status.pending_question,
                            timestamp: new Date()
                        });
                    } else {
                        // No pending question, clear it if it was set
                        if (pendingQuestion) {
                            setPendingQuestion(null);
                            setUserAnswer('');
                        }
                        
                        // Parse conversation history to determine current stage
                        const history = result.conversation_history || [];
                        const latestMessage = history[history.length - 1];
                        
                        if (latestMessage) {
                            const response = latestMessage.response?.response || '';
                            
                            // Detect stages from message content
                            if (response.includes('initiated successfully') || response.includes('Calling')) {
                                setStatus({
                                    stage: 'calling',
                                    message: '📞 Calling your phone...',
                                    details: 'Please answer your phone to connect with the AI assistant.',
                                    timestamp: new Date()
                                });
                            } else if (response.includes('connected') || response.includes('speaking') || response.includes('in progress')) {
                                setStatus({
                                    stage: 'connected',
                                    message: '✅ Call connected!',
                                    details: 'You are now speaking with the AI assistant.',
                                    timestamp: new Date()
                                });
                                setCallConnected(true);
                            } else if (latestMessage.response?.next === 'approval') {
                                setStatus({
                                    stage: 'approval',
                                    message: '⏳ Waiting for your approval...',
                                    details: response,
                                    timestamp: new Date()
                                });
                            }
                        }
                    }
                } else if (result.status === 'COMPLETED') {
                    setStatus({
                        stage: 'completed',
                        message: '✅ Call completed successfully',
                        details: 'The voice call has finished.',
                        timestamp: new Date()
                    });
                    setCallConnected(true);
                    mounted = false; // Stop polling
                } else if (result.status === 'FAILED') {
                    setStatus({
                        stage: 'failed',
                        message: '❌ Call failed',
                        details: 'There was an error with the call.',
                        timestamp: new Date()
                    });
                    setError('Call failed');
                    mounted = false; // Stop polling
                }

                // Continue polling if still running
                if (mounted && result.status === 'RUNNING') {
                    setTimeout(pollStatus, 2000); // Poll every 2 seconds
                }

            } catch (err) {
                console.error('[VoiceCallStatus] Error polling status:', err);
                if (mounted) {
                    setError(err.message || 'Failed to get call status');
                }
            }
        };

        // Start with initial status
        setStatus({
            stage: 'initiating',
            message: '🚀 Initiating voice call...',
            details: 'Setting up the call workflow...',
            timestamp: new Date()
        });

        // Start polling after a short delay
        setTimeout(pollStatus, 1000);

        return () => {
            mounted = false;
        };
    }, [workflowId, apiService]);

    const getStageIcon = (stage) => {
        switch (stage) {
            case 'initiating':
                return '🚀';
            case 'calling':
                return '📞';
            case 'connected':
                return '✅';
            case 'approval':
                return '⏳';
            case 'completed':
                return '✅';
            case 'failed':
                return '❌';
            default:
                return '📡';
        }
    };

    const getStageProgress = (stage) => {
        switch (stage) {
            case 'initiating':
                return 25;
            case 'calling':
                return 50;
            case 'connected':
                return 75;
            case 'needs_info':
                return 65; // Between calling and connected
            case 'approval':
                return 85;
            case 'completed':
                return 100;
            case 'failed':
                return 0;
            default:
                return 10;
        }
    };

    const formatTimestamp = (date) => {
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    };

    const handleSubmitAnswer = async (e) => {
        e.preventDefault();
        
        if (!userAnswer.trim() || submittingAnswer) return;
        
        try {
            setSubmittingAnswer(true);
            setError(null);
            
            // Send answer to backend
            const formData = new FormData();
            formData.append('answer', userAnswer.trim());
            
            const response = await fetch(
                `http://localhost:8000/voice-provide-answer/${workflowId}`,
                {
                    method: 'POST',
                    body: formData
                }
            );
            
            if (!response.ok) {
                throw new Error('Failed to send answer');
            }
            
            // Clear the form and pending question
            setUserAnswer('');
            setPendingQuestion(null);
            
            // Update status
            setStatus({
                stage: 'connected',
                message: '✅ Answer sent to agent',
                details: 'The voice assistant received your response and will continue the call.',
                timestamp: new Date()
            });
            
        } catch (err) {
            console.error('[VoiceCallStatus] Error submitting answer:', err);
            setError(err.message || 'Failed to send answer');
        } finally {
            setSubmittingAnswer(false);
        }
    };

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6">
            {/* Header */}
            <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100">
                    {getStageIcon(status.stage)} Voice Call Status
                </h2>
                {(status.stage === 'completed' || status.stage === 'failed') && onClose && (
                    <button
                        onClick={onClose}
                        className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 
                            dark:hover:text-gray-200 transition-colors"
                    >
                        Close
                    </button>
                )}
            </div>

            {/* Progress Bar */}
            <div className="mb-6">
                <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
                    <div
                        className={`h-full transition-all duration-500 ease-out rounded-full
                            ${status.stage === 'failed' 
                                ? 'bg-red-500' 
                                : status.stage === 'completed' 
                                    ? 'bg-green-500' 
                                    : 'bg-blue-500 animate-pulse'}`}
                        style={{ width: `${getStageProgress(status.stage)}%` }}
                    />
                </div>
                <div className="flex justify-between mt-2 text-xs text-gray-500 dark:text-gray-400">
                    <span>Initiating</span>
                    <span>Calling</span>
                    <span>Connected</span>
                    <span>Complete</span>
                </div>
            </div>

            {/* Status Message */}
            <div className="space-y-4">
                <div className={`p-4 rounded-lg ${
                    status.stage === 'failed' 
                        ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800' 
                        : status.stage === 'completed'
                            ? 'bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800'
                            : 'bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800'
                }`}>
                    <div className="flex items-start gap-3">
                        {status.stage !== 'completed' && status.stage !== 'failed' && (
                            <svg className="animate-spin h-5 w-5 text-blue-600 dark:text-blue-400 mt-0.5" 
                                xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle className="opacity-25" cx="12" cy="12" r="10" 
                                    stroke="currentColor" strokeWidth="4"></circle>
                                <path className="opacity-75" fill="currentColor" 
                                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
                                </path>
                            </svg>
                        )}
                        <div className="flex-1">
                            <h3 className={`font-semibold ${
                                status.stage === 'failed' 
                                    ? 'text-red-800 dark:text-red-200' 
                                    : status.stage === 'completed'
                                        ? 'text-green-800 dark:text-green-200'
                                        : 'text-blue-800 dark:text-blue-200'
                            }`}>
                                {status.message}
                            </h3>
                            {status.details && (
                                <p className={`text-sm mt-1 ${
                                    status.stage === 'failed' 
                                        ? 'text-red-700 dark:text-red-300' 
                                        : status.stage === 'completed'
                                            ? 'text-green-700 dark:text-green-300'
                                            : 'text-blue-700 dark:text-blue-300'
                                }`}>
                                    {status.details}
                                </p>
                            )}
                            <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
                                {formatTimestamp(status.timestamp)}
                            </p>
                        </div>
                    </div>
                </div>

                {/* Workflow ID */}
                <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-md">
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                        <strong>Workflow ID:</strong>
                    </p>
                    <p className="text-xs text-gray-800 dark:text-gray-200 font-mono mt-1 break-all">
                        {workflowId}
                    </p>
                </div>

                {/* Call Instructions */}
                {status.stage === 'calling' && !callConnected && (
                    <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
                        <p className="text-sm text-yellow-800 dark:text-yellow-200 font-semibold mb-2">
                            📱 Important: Answer Your Phone
                        </p>
                        <ul className="text-xs text-yellow-700 dark:text-yellow-300 space-y-1 list-disc list-inside">
                            <li>Check for incoming call from Twilio number</li>
                            <li>Answer to connect with AI assistant</li>
                            <li>Speak naturally - the AI can hear you</li>
                        </ul>
                    </div>
                )}

                {/* Question from Agent - Needs Clarification */}
                {pendingQuestion && (
                    <div className="p-4 bg-purple-50 dark:bg-purple-900/20 border-2 border-purple-300 dark:border-purple-700 rounded-lg">
                        <div className="flex items-start gap-3 mb-3">
                            <span className="text-2xl">❓</span>
                            <div className="flex-1">
                                <p className="text-sm text-purple-800 dark:text-purple-200 font-semibold mb-1">
                                    Agent Needs Information
                                </p>
                                <p className="text-sm text-purple-700 dark:text-purple-300">
                                    {pendingQuestion}
                                </p>
                            </div>
                        </div>
                        
                        <form onSubmit={handleSubmitAnswer} className="mt-3">
                            <div className="flex gap-2">
                                <input
                                    type="text"
                                    value={userAnswer}
                                    onChange={(e) => setUserAnswer(e.target.value)}
                                    placeholder="Type your answer here..."
                                    disabled={submittingAnswer}
                                    className="flex-1 px-3 py-2 border border-purple-300 dark:border-purple-600 rounded-md
                                        focus:outline-none focus:ring-2 focus:ring-purple-500
                                        dark:bg-gray-700 dark:text-gray-100
                                        disabled:opacity-50 disabled:cursor-not-allowed"
                                    autoFocus
                                />
                                <button
                                    type="submit"
                                    disabled={!userAnswer.trim() || submittingAnswer}
                                    className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-md
                                        font-medium transition-colors
                                        disabled:opacity-50 disabled:cursor-not-allowed
                                        focus:outline-none focus:ring-2 focus:ring-purple-500"
                                >
                                    {submittingAnswer ? (
                                        <svg className="animate-spin h-5 w-5 text-white" 
                                            xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                            <circle className="opacity-25" cx="12" cy="12" r="10" 
                                                stroke="currentColor" strokeWidth="4"></circle>
                                            <path className="opacity-75" fill="currentColor" 
                                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
                                            </path>
                                        </svg>
                                    ) : (
                                        'Send'
                                    )}
                                </button>
                            </div>
                            <p className="text-xs text-purple-600 dark:text-purple-400 mt-2">
                                💡 The agent will relay this information during the call
                            </p>
                        </form>
                    </div>
                )}

                {/* Error Display */}
                {error && (
                    <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
                        <p className="text-sm text-red-800 dark:text-red-200">
                            <strong>Error:</strong> {error}
                        </p>
                    </div>
                )}
            </div>
        </div>
    );
}

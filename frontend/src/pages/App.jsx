import React, { useEffect, useState, useRef, useCallback } from "react";
import NavBar from "../components/NavBar";
import ChatWindow from "../components/ChatWindow";
import VoiceCallForm from "../components/VoiceCallForm";
import { apiService } from "../services/api";

const POLL_INTERVAL = 600; // 0.6 seconds
const INITIAL_ERROR_STATE = { visible: false, message: '' };
const DEBOUNCE_DELAY = 300; // 300ms debounce for user input
const CONVERSATION_FETCH_ERROR_DELAY_MS = 10000; // wait 10s before showing fetch errors
const CONVERSATION_FETCH_ERROR_THRESHOLD = Math.ceil(
    CONVERSATION_FETCH_ERROR_DELAY_MS / POLL_INTERVAL
);

function useDebounce(value, delay) {
    const [debouncedValue, setDebouncedValue] = useState(value);

    useEffect(() => {
        const handler = setTimeout(() => {
            setDebouncedValue(value);
        }, delay);

        return () => {
            clearTimeout(handler);
        };
    }, [value, delay]);

    return debouncedValue;
}

export default function App() {
    const containerRef = useRef(null);
    const inputRef = useRef(null);
    const pollingRef = useRef(null);
    const scrollTimeoutRef = useRef(null);
    
    const [conversation, setConversation] = useState([]);
    const [lastMessage, setLastMessage] = useState(null);
    const [userInput, setUserInput] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(INITIAL_ERROR_STATE);
    const [done, setDone] = useState(true);
    
    // Voice call mode state - START IN VOICE MODE BY DEFAULT
    const [voiceMode, setVoiceMode] = useState(true);
    const [voiceWorkflowId, setVoiceWorkflowId] = useState(null);
    const [voiceCallStatus, setVoiceCallStatus] = useState(null);

    const debouncedUserInput = useDebounce(userInput, DEBOUNCE_DELAY);

    const errorTimerRef = useRef(null);
    const conversationFetchErrorCountRef = useRef(0);

    const handleError = useCallback((error, context) => {
        console.error(`${context}:`, error);

        const isConversationFetchError =
            context === "fetching conversation" && (error.status === 404 || error.status === 408);

        if (isConversationFetchError) {
            if (error.status === 404) {
                conversationFetchErrorCountRef.current += 1;

                const hasExceededThreshold =
                    conversationFetchErrorCountRef.current >= CONVERSATION_FETCH_ERROR_THRESHOLD;

                if (!hasExceededThreshold) {
                    return;
                }
            } else {
                // For timeouts or other connectivity errors surface immediately
                conversationFetchErrorCountRef.current = CONVERSATION_FETCH_ERROR_THRESHOLD;
            }
        } else {
            conversationFetchErrorCountRef.current = 0;
        }

        const errorMessage = isConversationFetchError
            ? "Error fetching conversation. Retrying..."
            : `Error ${context.toLowerCase()}. Please try again.`;

        setError(prevError => {
            // If the same 404 error is already being displayed, don't reset state (prevents flickering)
            if (prevError.visible && prevError.message === errorMessage) {
                return prevError;
            }
            return { visible: true, message: errorMessage };
        });

        // Clear any existing timeout
        if (errorTimerRef.current) {
            clearTimeout(errorTimerRef.current);
        }

        // Only auto-dismiss non-404 errors after 3 seconds
        if (!isConversationFetchError) {
            errorTimerRef.current = setTimeout(() => setError(INITIAL_ERROR_STATE), 3000);
        }
    }, []);
    
    
    const clearErrorOnSuccess = useCallback(() => {
        if (errorTimerRef.current) {
            clearTimeout(errorTimerRef.current);
        }
        conversationFetchErrorCountRef.current = 0;
        setError(INITIAL_ERROR_STATE);
    }, []);
    
    const fetchConversationHistory = useCallback(async () => {
        try {
            const data = await apiService.getConversationHistory(voiceWorkflowId);
            const newConversation = data.messages || [];
            
            setConversation(prevConversation => 
                JSON.stringify(prevConversation) !== JSON.stringify(newConversation) ? newConversation : prevConversation
            );
    
            if (newConversation.length > 0) {
                const lastMsg = newConversation[newConversation.length - 1];
                const isAgentMessage = lastMsg.actor === "agent";
                
                setLoading(!isAgentMessage);
                setDone(lastMsg.response.next === "done");
    
                setLastMessage(prevLastMessage =>
                    !prevLastMessage || lastMsg.response.response !== prevLastMessage.response.response
                        ? lastMsg
                        : prevLastMessage
                );
            } else {
                setLoading(false);
                setDone(true);
                setLastMessage(null);
            }
    
            // Successfully fetched data, clear any persistent errors
            clearErrorOnSuccess();
        } catch (err) {
            handleError(err, "fetching conversation");
        }
    }, [voiceWorkflowId, handleError, clearErrorOnSuccess]);
    
    // Setup polling with cleanup - Only poll when we have an active voice workflow
    useEffect(() => {
        // Only poll if we have a voice workflow and are not in voice mode
        if (voiceWorkflowId && !voiceMode) {
            pollingRef.current = setInterval(fetchConversationHistory, POLL_INTERVAL);
        }
        
        return () => {
            if (pollingRef.current) {
                clearInterval(pollingRef.current);
            }
        };
    }, [fetchConversationHistory, voiceWorkflowId, voiceMode]);
    

    const scrollToBottom = useCallback(() => {
        if (containerRef.current) {
            if (scrollTimeoutRef.current) {
                clearTimeout(scrollTimeoutRef.current);
            }
            
            scrollTimeoutRef.current = setTimeout(() => {
                const element = containerRef.current;
                element.scrollTop = element.scrollHeight;
                scrollTimeoutRef.current = null;
            }, 100);
        }
    }, []);

    const handleContentChange = useCallback(() => {
        scrollToBottom();
    }, [scrollToBottom]);

    useEffect(() => {
        if (lastMessage) {
            scrollToBottom();
        }
    }, [lastMessage, scrollToBottom]);

    useEffect(() => {
        if (inputRef.current && !loading && !done) {
            inputRef.current.focus();
        }
        
        return () => {
            if (scrollTimeoutRef.current) {
                clearTimeout(scrollTimeoutRef.current);
            }
        };
    }, [loading, done]);

    const handleSendMessage = async () => {
        const trimmedInput = userInput.trim();
        if (!trimmedInput) return;
        
        try {
            setLoading(true);
            setError(INITIAL_ERROR_STATE);
            await apiService.sendMessage(trimmedInput);
            setUserInput("");
        } catch (err) {
            handleError(err, "sending message");
            setLoading(false);
        }
    };

    const handleConfirm = async () => {
        try {
            setLoading(true);
            setError(INITIAL_ERROR_STATE);
            await apiService.confirm(voiceWorkflowId);
        } catch (err) {
            handleError(err, "confirming action");
            setLoading(false);
        }
    };

    const handleStartNewChat = async () => {
        try {
            setError(INITIAL_ERROR_STATE);
            setLoading(true);
            await apiService.startWorkflow();
            setConversation([]);
            setLastMessage(null);
            setVoiceMode(false);
            setVoiceWorkflowId(null);
            setVoiceCallStatus(null);
        } catch (err) {
            handleError(err, "starting new chat");
        } finally {
            setLoading(false);
        }
    };

    const handleToggleVoiceMode = () => {
        setVoiceMode(!voiceMode);
        setError(INITIAL_ERROR_STATE);
    };

    const handleVoiceCallSubmit = async ({ phoneNumber, goal, context }) => {
        try {
            setLoading(true);
            setError(INITIAL_ERROR_STATE);
            
            const result = await apiService.initiateVoiceCall({
                phoneNumber,
                goal,
                context
            });

            // Store workflow ID for status tracking
            setVoiceWorkflowId(result.workflow_id);
            
            // Show success message in conversation
            const successMessage = {
                actor: "system",
                response: {
                    response: `✅ Voice call initiated successfully!\n\n` +
                        `📱 Calling: ${result.phone_number}\n` +
                        `🎯 Goal: ${result.goal}\n` +
                        `📝 Context: ${result.context}\n\n` +
                        `Workflow ID: ${result.workflow_id}\n\n` +
                        `The voice assistant will call you shortly to help with your request.`,
                    next: "question"
                }
            };
            
            setConversation([successMessage]);
            setLastMessage(successMessage);
            
            // Log workflow ID to console for debugging
            console.log('Voice call workflow initiated:', result.workflow_id);
            
            // Switch back to chat view to show status
            setVoiceMode(false);
            setDone(false);
            
        } catch (err) {
            handleError(err, "initiating voice call");
        } finally {
            setLoading(false);
        }
    };

    const handleCancelVoiceMode = () => {
        setVoiceMode(false);
        setError(INITIAL_ERROR_STATE);
    };

    return (
        <div className="flex flex-col h-screen bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
            <NavBar title="🎙️ AI Voice Assistant - Powered by Twilio & LiveKit" />

            {error.visible && (
                <div className="fixed top-16 left-1/2 transform -translate-x-1/2 
                    bg-red-500 text-white px-6 py-3 rounded-lg shadow-xl z-50 
                    transition-all duration-300 animate-slide-down">
                    <div className="flex items-center gap-2">
                        <span className="text-xl">⚠️</span>
                        <span>{error.message}</span>
                    </div>
                </div>
            )}

            <div className="flex-grow flex justify-center px-4 py-6 overflow-hidden">
                <div className="w-full max-w-2xl bg-white dark:bg-gray-900 p-8 rounded-xl shadow-2xl 
                    flex flex-col overflow-hidden border border-gray-200 dark:border-gray-700">
                    
                    {/* Main Header */}
                    <div className="text-center mb-6">
                        <h1 className="text-3xl font-bold text-gray-800 dark:text-white mb-2">
                            {voiceMode ? '📞 Make a Voice Call' : '💬 Call Status'}
                        </h1>
                        <p className="text-gray-600 dark:text-gray-400">
                            {voiceMode 
                                ? 'Our AI assistant will call on your behalf to complete your goal' 
                                : 'Track your voice call in real-time'}
                        </p>
                    </div>

                    {/* Voice Mode Toggle - More Prominent */}
                    {!voiceWorkflowId && (
                        <div className="mb-6">
                            <button
                                onClick={handleToggleVoiceMode}
                                className={`w-full px-6 py-4 rounded-lg font-semibold text-lg
                                    transition-all duration-300 transform hover:scale-105
                                    shadow-md hover:shadow-lg
                                    ${voiceMode 
                                        ? 'bg-gradient-to-r from-gray-600 to-gray-700 text-white hover:from-gray-700 hover:to-gray-800' 
                                        : 'bg-gradient-to-r from-green-500 to-green-600 text-white hover:from-green-600 hover:to-green-700'
                                    }`}
                            >
                                {voiceMode ? '� View Call History' : '🎙️ Make New Voice Call'}
                            </button>
                        </div>
                    )}

                    {/* Conditional rendering: Voice Form or Call Status */}
                    {voiceMode ? (
                        <div className="flex-grow flex items-center justify-center">
                            <VoiceCallForm 
                                onSubmit={handleVoiceCallSubmit}
                                loading={loading}
                                onCancel={handleCancelVoiceMode}
                            />
                        </div>
                    ) : (
                        <>
                            <div ref={containerRef} 
                                className="flex-grow overflow-y-auto pb-4 scroll-smooth
                                    border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-gray-50 dark:bg-gray-800">
                                
                                {/* Show call status or history */}
                                {conversation.length === 0 ? (
                                    <div className="text-center py-12">
                                        <div className="text-6xl mb-4">📞</div>
                                        <h3 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-2">
                                            No Active Calls
                                        </h3>
                                        <p className="text-gray-500 dark:text-gray-400">
                                            Click "Make New Voice Call" above to get started
                                        </p>
                                    </div>
                                ) : (
                                    <>
                                        <ChatWindow
                                            conversation={conversation}
                                            loading={loading}
                                            onConfirm={handleConfirm}
                                            onContentChange={handleContentChange}
                                        />
                                        {done && (
                                            <div className="text-center text-sm text-gray-500 dark:text-gray-400 mt-4 
                                                p-3 bg-gray-100 dark:bg-gray-700 rounded-md">
                                                ✅ Call Completed
                                            </div>
                                        )}
                                    </>
                                )}
                                
                                {/* Show workflow ID if voice call was initiated */}
                                {voiceWorkflowId && (
                                    <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg border-2 border-blue-200 dark:border-blue-700">
                                        <div className="flex items-start gap-3">
                                            <span className="text-2xl">🔄</span>
                                            <div className="flex-1">
                                                <p className="text-sm font-semibold text-blue-800 dark:text-blue-200 mb-2">
                                                    Active Workflow
                                                </p>
                                                <p className="text-xs text-blue-700 dark:text-blue-300 font-mono break-all bg-white dark:bg-gray-800 p-2 rounded">
                                                    {voiceWorkflowId}
                                                </p>
                                                <p className="text-xs text-blue-600 dark:text-blue-400 mt-2">
                                                    💡 Track this call in the <a href="http://localhost:8081" target="_blank" rel="noopener noreferrer" className="underline hover:text-blue-800">Temporal UI</a>
                                                </p>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </div>
                            
                            {/* Action buttons for call status view */}
                            <div className="mt-4 text-center">
                                <button
                                    onClick={handleStartNewChat}
                                    className="bg-gradient-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 
                                        text-white px-6 py-3 rounded-lg font-semibold
                                        transition-all duration-300 transform hover:scale-105 shadow-md hover:shadow-lg"
                                    disabled={!done}
                                >
                                    🎙️ Make Another Call
                                </button>
                            </div>
                        </>
                    )}
                </div>
            </div>

            {/* Remove the chat input area entirely - Voice-only interface */}
        </div>
    );
}

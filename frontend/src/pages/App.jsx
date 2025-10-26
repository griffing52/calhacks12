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
    
    // Voice call mode state
    const [voiceMode, setVoiceMode] = useState(false);
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
            const data = await apiService.getConversationHistory();
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
    }, [handleError, clearErrorOnSuccess]);
    
    // Setup polling with cleanup
    useEffect(() => {
        pollingRef.current = setInterval(fetchConversationHistory, POLL_INTERVAL);
        
        return () => clearInterval(pollingRef.current);
    }, [fetchConversationHistory]);
    

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
            await apiService.confirm();
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
        <div className="flex flex-col h-screen">
            <NavBar title="Temporal AI Agent 🤖" />

            {error.visible && (
                <div className="fixed top-16 left-1/2 transform -translate-x-1/2 
                    bg-red-500 text-white px-4 py-2 rounded shadow-lg z-50 
                    transition-opacity duration-300">
                    {error.message}
                </div>
            )}

            <div className="flex-grow flex justify-center px-4 py-2 overflow-hidden">
                <div className="w-full max-w-lg bg-white dark:bg-gray-900 p-8 px-3 rounded shadow-md 
                    flex flex-col overflow-hidden">
                    
                    {/* Voice Mode Toggle Button */}
                    {done && !voiceWorkflowId && (
                        <div className="mb-4 text-center">
                            <button
                                onClick={handleToggleVoiceMode}
                                className={`px-4 py-2 rounded-md font-medium transition-all duration-200
                                    ${voiceMode 
                                        ? 'bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-300 dark:hover:bg-gray-600' 
                                        : 'bg-green-600 text-white hover:bg-green-700'
                                    }`}
                            >
                                {voiceMode ? '💬 Switch to Chat' : '📞 Start Voice Call'}
                            </button>
                        </div>
                    )}

                    {/* Conditional rendering: Voice Form or Chat Window */}
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
                                className="flex-grow overflow-y-auto pb-20 pt-10 scroll-smooth">
                                <ChatWindow
                                    conversation={conversation}
                                    loading={loading}
                                    onConfirm={handleConfirm}
                                    onContentChange={handleContentChange}
                                />
                                {done && (
                                    <div className="text-center text-sm text-gray-500 dark:text-gray-400 mt-4 
                                        animate-fade-in">
                                        Chat ended
                                    </div>
                                )}
                                
                                {/* Show workflow ID if voice call was initiated */}
                                {voiceWorkflowId && (
                                    <div className="mt-4 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-md">
                                        <p className="text-sm text-blue-800 dark:text-blue-200 font-mono break-all">
                                            <strong>Workflow ID:</strong> {voiceWorkflowId}
                                        </p>
                                        <p className="text-xs text-blue-600 dark:text-blue-300 mt-2">
                                            You can use this ID to track the call status in the Temporal UI.
                                        </p>
                                    </div>
                                )}
                            </div>
                        </>
                    )}
                </div>
            </div>

            {/* Input area - only show in chat mode */}
            {!voiceMode && (
                <div className="fixed bottom-0 left-1/2 transform -translate-x-1/2 
                    w-full max-w-lg bg-white dark:bg-gray-900 p-4
                    border-t border-gray-300 dark:border-gray-700 shadow-lg
                    transition-all duration-200"
                    style={{ zIndex: 10 }}>
                    <form onSubmit={(e) => {
                        e.preventDefault();
                        handleSendMessage();
                    }} className="flex items-center">
                        <input
                            ref={inputRef}
                            type="text"
                            className={`flex-grow rounded-l px-3 py-2 border border-gray-300
                                dark:bg-gray-700 dark:border-gray-600 focus:outline-none
                                transition-opacity duration-200
                                ${loading || done ? "opacity-50 cursor-not-allowed" : ""}`}
                            placeholder="Type your message..."
                            value={userInput}
                            onChange={(e) => setUserInput(e.target.value)}
                            disabled={loading || done}
                            aria-label="Type your message"
                        />
                        <button
                            type="submit"
                            className={`bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-r 
                                transition-all duration-200
                                ${loading || done ? "opacity-50 cursor-not-allowed" : ""}`}
                            disabled={loading || done}
                            aria-label="Send message"
                        >
                            Send
                        </button>
                    </form>
                    
                    <div className="text-right mt-3">
                        <button
                            onClick={handleStartNewChat}
                            className={`text-sm underline text-gray-600 dark:text-gray-400 
                                hover:text-gray-800 dark:hover:text-gray-200 
                                transition-all duration-200
                                ${!done ? "opacity-0 cursor-not-allowed" : ""}`}
                            disabled={!done}
                            aria-label="Start new chat"
                        >
                            Start New Chat
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}

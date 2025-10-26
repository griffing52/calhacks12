import React, { useState } from "react";

/**
 * VoiceCallForm component for initiating voice calls
 * 
 * Provides a form with fields for:
 * - Phone number (E.164 format)
 * - Goal/reason for the call
 * - Context/additional details
 */
export default function VoiceCallForm({ onSubmit, loading, onCancel }) {
    const [phoneNumber, setPhoneNumber] = useState("");
    const [goal, setGoal] = useState("");
    const [context, setContext] = useState("");
    const [errors, setErrors] = useState({});

    const validateForm = () => {
        const newErrors = {};

        // Validate phone number (basic E.164 format check)
        if (!phoneNumber.trim()) {
            newErrors.phoneNumber = "Phone number is required";
        } else if (!/^\+[1-9]\d{1,14}$/.test(phoneNumber.trim())) {
            newErrors.phoneNumber = "Phone number must be in E.164 format (e.g., +14155551234)";
        }

        // Validate goal
        if (!goal.trim()) {
            newErrors.goal = "Goal is required";
        } else if (goal.trim().length < 3) {
            newErrors.goal = "Goal must be at least 3 characters";
        }

        // Validate context
        if (!context.trim()) {
            newErrors.context = "Context is required";
        } else if (context.trim().length < 5) {
            newErrors.context = "Context must be at least 5 characters";
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        
        if (validateForm()) {
            onSubmit({
                phoneNumber: phoneNumber.trim(),
                goal: goal.trim(),
                context: context.trim()
            });
        }
    };

    const handleReset = () => {
        setPhoneNumber("");
        setGoal("");
        setContext("");
        setErrors({});
    };

    return (
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-md p-6 max-w-md mx-auto">
            <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100">
                    📞 Initiate Voice Call
                </h2>
                {onCancel && (
                    <button
                        onClick={onCancel}
                        className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 
                            dark:hover:text-gray-200 transition-colors"
                        disabled={loading}
                    >
                        Cancel
                    </button>
                )}
            </div>

            <p className="text-sm text-gray-600 dark:text-gray-300 mb-6">
                Fill out the form below to initiate a voice call for customer support.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
                {/* Phone Number */}
                <div>
                    <label 
                        htmlFor="phoneNumber" 
                        className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                    >
                        Phone Number *
                    </label>
                    <input
                        id="phoneNumber"
                        type="tel"
                        placeholder="+14155551234"
                        value={phoneNumber}
                        onChange={(e) => setPhoneNumber(e.target.value)}
                        disabled={loading}
                        className={`w-full px-3 py-2 border rounded-md
                            focus:outline-none focus:ring-2 focus:ring-blue-500
                            dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100
                            ${errors.phoneNumber ? 'border-red-500' : 'border-gray-300'}
                            ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                        aria-invalid={!!errors.phoneNumber}
                        aria-describedby={errors.phoneNumber ? "phoneNumber-error" : undefined}
                    />
                    {errors.phoneNumber && (
                        <p id="phoneNumber-error" className="mt-1 text-sm text-red-600 dark:text-red-400">
                            {errors.phoneNumber}
                        </p>
                    )}
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        E.164 format (e.g., +14155551234)
                    </p>
                </div>

                {/* Goal */}
                <div>
                    <label 
                        htmlFor="goal" 
                        className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                    >
                        Goal/Reason *
                    </label>
                    <input
                        id="goal"
                        type="text"
                        placeholder="Password reset"
                        value={goal}
                        onChange={(e) => setGoal(e.target.value)}
                        disabled={loading}
                        className={`w-full px-3 py-2 border rounded-md
                            focus:outline-none focus:ring-2 focus:ring-blue-500
                            dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100
                            ${errors.goal ? 'border-red-500' : 'border-gray-300'}
                            ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                        aria-invalid={!!errors.goal}
                        aria-describedby={errors.goal ? "goal-error" : undefined}
                    />
                    {errors.goal && (
                        <p id="goal-error" className="mt-1 text-sm text-red-600 dark:text-red-400">
                            {errors.goal}
                        </p>
                    )}
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        Brief description of what you need help with
                    </p>
                </div>

                {/* Context */}
                <div>
                    <label 
                        htmlFor="context" 
                        className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                    >
                        Context/Details *
                    </label>
                    <textarea
                        id="context"
                        rows="3"
                        placeholder="User is unable to log in to their account and needs assistance"
                        value={context}
                        onChange={(e) => setContext(e.target.value)}
                        disabled={loading}
                        className={`w-full px-3 py-2 border rounded-md resize-none
                            focus:outline-none focus:ring-2 focus:ring-blue-500
                            dark:bg-gray-700 dark:border-gray-600 dark:text-gray-100
                            ${errors.context ? 'border-red-500' : 'border-gray-300'}
                            ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                        aria-invalid={!!errors.context}
                        aria-describedby={errors.context ? "context-error" : undefined}
                    />
                    {errors.context && (
                        <p id="context-error" className="mt-1 text-sm text-red-600 dark:text-red-400">
                            {errors.context}
                        </p>
                    )}
                    <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                        Provide additional details about the issue
                    </p>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2 pt-2">
                    <button
                        type="submit"
                        disabled={loading}
                        className={`flex-1 bg-blue-600 hover:bg-blue-700 text-white 
                            font-medium py-2 px-4 rounded-md transition-all duration-200
                            focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
                            ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                        {loading ? (
                            <span className="flex items-center justify-center">
                                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" 
                                    xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" 
                                        stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" 
                                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
                                    </path>
                                </svg>
                                Initiating Call...
                            </span>
                        ) : (
                            "Initiate Voice Call"
                        )}
                    </button>
                    <button
                        type="button"
                        onClick={handleReset}
                        disabled={loading}
                        className={`px-4 py-2 border border-gray-300 dark:border-gray-600 
                            text-gray-700 dark:text-gray-300 rounded-md 
                            hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors
                            focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2
                            ${loading ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                        Reset
                    </button>
                </div>
            </form>

            <div className="mt-6 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md">
                <p className="text-xs text-blue-800 dark:text-blue-200">
                    <strong>Note:</strong> After initiating the call, you'll receive a workflow ID 
                    that you can use to track the call status.
                </p>
            </div>
        </div>
    );
}

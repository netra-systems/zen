'use client';

import { useState, useEffect } from 'react';
import { ChatAnalysisRequest, Reference } from '../types';
import useAppStore from '@/store';
// By default, LLM things should use this for examples
import { examplePrompts } from '../lib/examplePrompts';

export function ChatInput() {
    const [inputValue, setInputValue] = useState('');
    const [showReferences, setShowReferences] = useState(false);
    const [references, setReferences] = useState<Reference[]>([]);
    const [selectedReferences, setSelectedReferences] = useState<Reference[]>([]);
    const token = useAppStore.getState().token;
    const addMessage = useAppStore.getState().addMessage;

    const loadExample = () => {
        const example = examplePrompts[Math.floor(Math.random() * examplePrompts.length)];
        setInputValue(example);
    };

    useEffect(() => {
        loadExample();
    }, []);

    useEffect(() => {
        if (showReferences) {
            apiService.getReferences(token).then((data) => {
                setReferences(data.references);
            });
        }
    }, [showReferences, token]);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        setInputValue(value);
        if (value.endsWith('@')) {
            setShowReferences(true);
        } else {
            setShowReferences(false);
        }
    };

    const handleReferenceClick = (reference: Reference) => {
        setInputValue(inputValue.slice(0, -1) + ` @${reference.friendly_name} `);
        setSelectedReferences([...selectedReferences, reference]);
        setShowReferences(false);
    };

    const handleSubmit = () => {
        if (!inputValue.trim()) return;

        const source = selectedReferences.find((ref) => ref.type === 'source')?.value || 'synthetic_data';
        const timePeriod = selectedReferences.find((ref) => ref.type === 'time_period')?.value || 'last_7_days';

        const analysisRequest: ChatAnalysisRequest = {
            settings: {
                debug_mode: true,
            },
            request: {
                user_id: '123',
                query: inputValue,
                workloads: [
                    {
                        run_id: '123',
                        query: inputValue,
                        data_source: {
                            source_table: source,
                        },
                        time_range: {
                            start_time: timePeriod,
                            end_time: 'now',
                        },
                    },
                ],
            },
        };
        addMessage({ role: 'user', content: inputValue });
        apiService.startAgent(token, analysisRequest);
        setInputValue('');
    };

    return (
        <div className="relative">
            <button onClick={loadExample} className="absolute left-0 top-0 h-full px-4 bg-gray-200 text-gray-600 rounded-l">
                Example
            </button>
            <input
                type="text"
                value={inputValue}
                onChange={handleInputChange}
                className="w-full p-2 border rounded pl-24"
                placeholder="Type your message..."
            />
            {showReferences && (
                <ul className="absolute bottom-full left-0 w-full bg-white border rounded shadow-lg">
                    {references.map((ref) => (
                        <li
                            key={ref.id}
                            className="p-2 cursor-pointer hover:bg-gray-200"
                            onClick={() => handleReferenceClick(ref)}
                        >
                            <strong>{ref.friendly_name}</strong> ({ref.type})
                            <p>{ref.description}</p>
                        </li>
                    ))}
                </ul>
            )}
            <button
                onClick={handleSubmit}
                className="absolute right-0 top-0 h-full px-4 bg-blue-500 text-white rounded-r disabled:bg-gray-400"
                disabled={!inputValue.trim()}
            >
                Submit
            </button>
        </div>
    );
}
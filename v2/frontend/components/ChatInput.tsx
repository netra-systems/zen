'use client';

import { useState, useEffect } from 'react';
import { AnalysisRequest, ReferenceItem } from '@/types';
import { useWebSocket } from '@/hooks/useWebSocket';
import { examplePrompts } from '../lib/examplePrompts';

export function ChatInput() {
    const [inputValue, setInputValue] = useState('');
    const [showReferences, setShowReferences] = useState(false);
    const [references, setReferences] = useState<ReferenceItem[]>([]);
    const [selectedReferences, setSelectedReferences] = useState<ReferenceItem[]>([]);
    const { sendMessage } = useWebSocket();

    const loadExample = () => {
        const example = examplePrompts[Math.floor(Math.random() * examplePrompts.length)];
        setInputValue(example);
    };

    useEffect(() => {
        loadExample();
    }, []);

    const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        setInputValue(value);
        if (value.endsWith('@')) {
            setShowReferences(true);
        } else {
            setShowReferences(false);
        }
    };

    const handleReferenceClick = (reference: ReferenceItem) => {
        setInputValue(inputValue.slice(0, -1) + ` @${reference.friendly_name} `);
        setSelectedReferences([...selectedReferences, reference]);
        setShowReferences(false);
    };

    const handleSubmit = () => {
        if (!inputValue.trim()) return;

        const source = selectedReferences.find((ref) => ref.type === 'source')?.value || 'synthetic_data';
        const timePeriod = selectedReferences.find((ref) => ref.type === 'time_period')?.value || 'last_7_days';

        const analysisRequest: AnalysisRequest = {
            request_model: {
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
        sendMessage({ type: 'analysis_request', payload: analysisRequest });
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
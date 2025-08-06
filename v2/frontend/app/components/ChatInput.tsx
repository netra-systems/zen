
'use client';

import { useState, useEffect } from 'react';
import { apiService } from '../api';
import useAppStore from '../store';

export function ChatInput() {
    const [inputValue, setInputValue] = useState('');
    const [showReferences, setShowReferences] = useState(false);
    const [references, setReferences] = useState<any[]>([]);
    const [selectedReferences, setSelectedReferences] = useState<any[]>([]);
    const token = useAppStore((state) => state.token);

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

    const handleReferenceClick = (reference: any) => {
        setInputValue(inputValue.slice(0, -1) + ` @${reference.name} `);
        setSelectedReferences([...selectedReferences, reference]);
        setShowReferences(false);
    };

    const handleSubmit = () => {
        const source = selectedReferences.find((ref) => ref.type === 'source')?.value || 'synthetic_data';
        const timePeriod = selectedReferences.find((ref) => ref.type === 'time_period')?.value || 'last_7_days';

        const analysisRequest = {
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

        apiService.startAgent(token, analysisRequest);
    };

    return (
        <div className="relative">
            <input
                type="text"
                value={inputValue}
                onChange={handleInputChange}
                className="w-full p-2 border rounded"
                placeholder="Type your message..."
            />
            {showReferences && (
                <ul className="absolute bottom-full left-0 w-full bg-white border rounded shadow-lg">
                    {references.map((ref) => (
                        <li
                            key={ref.name}
                            className="p-2 cursor-pointer hover:bg-gray-200"
                            onClick={() => handleReferenceClick(ref)}
                        >
                            {ref.name}
                        </li>
                    ))}
                </ul>
            )}
            <button onClick={handleSubmit} className="absolute right-0 top-0 h-full px-4 bg-blue-500 text-white rounded-r">
                Submit
            </button>
        </div>
    );
}

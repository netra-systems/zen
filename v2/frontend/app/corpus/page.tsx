'use client';

import React, { useState, useEffect } from 'react';
import { Corpus } from '../../types';
import { useWebSocket } from '@/app/hooks/useWebSocket';

export default function CorpusAdminPage() {
    const [corpora, setCorpora] = useState<Corpus[]>([]);
    const [newCorpusName, setNewCorpusName] = useState('');
    const [newCorpusDescription, setNewCorpusDescription] = useState('');
    const { lastMessage } = useWebSocket();

    useEffect(() => {
        fetch('/api/v3/corpus')
            .then(res => res.json())
            .then(data => setCorpora(data));
    }, []);

    useEffect(() => {
        if (lastMessage) {
            const message = lastMessage.data;
            const match = message.match(/Corpus (.*) progress: (.*)/);
            if (match) {
                const corpusId = match[1];
                const progress = match[2];
                setCorpora(prevCorpora =>
                    prevCorpora.map(c =>
                        c.id === corpusId ? { ...c, status: `running: ${progress}` } : c
                    )
                );
            }
            const completedMatch = message.match(/Corpus (.*) completed/);
            if (completedMatch) {
                const corpusId = completedMatch[1];
                setCorpora(prevCorpora =>
                    prevCorpora.map(c =>
                        c.id === corpusId ? { ...c, status: 'completed' } : c
                    )
                );
            }
        }
    }, [lastMessage]);

    const handleCreateCorpus = () => {
        fetch('/api/v3/corpus', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name: newCorpusName, description: newCorpusDescription }),
        })
            .then(res => res.json())
            .then(newCorpus => {
                setCorpora([...corpora, newCorpus]);
                setNewCorpusName('');
                setNewCorpusDescription('');
            });
    };

    return (
        <div className="container mx-auto p-4">
            <h1 className="text-2xl font-bold mb-4">Corpus Administration</h1>

            <div className="mb-8">
                <h2 className="text-xl font-semibold mb-2">Create New Corpus</h2>
                <div className="flex flex-col space-y-2">
                    <input
                        type="text"
                        placeholder="Corpus Name"
                        value={newCorpusName}
                        onChange={e => setNewCorpusName(e.target.value)}
                        className="p-2 border rounded"
                    />
                    <textarea
                        placeholder="Corpus Description"
                        value={newCorpusDescription}
                        onChange={e => setNewCorpusDescription(e.target.value)}
                        className="p-2 border rounded"
                    />
                    <button onClick={handleCreateCorpus} className="bg-blue-500 text-white p-2 rounded">
                        Create Corpus
                    </button>
                </div>
            </div>

            <div>
                <h2 className="text-xl font-semibold mb-2">Existing Corpora</h2>
                <ul className="space-y-2">
                    {corpora.map(corpus => (
                        <li key={corpus.id} className="p-4 border rounded shadow-sm">
                            <h3 className="text-lg font-bold">{corpus.name}</h3>
                            <p>{corpus.description}</p>
                            <p className="text-sm text-gray-500">Status: {corpus.status}</p>
                            <p className="text-sm text-gray-500">Created: {new Date(corpus.created_at).toLocaleString()}</p>
                        </li>
                    ))}
                </ul>
            </div>
        </div>
    );
}
import React, { useState, FormEvent, useEffect, useRef } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Send } from 'lucide-react';
import { MessageOrchestrator } from './MessageOrchestrator';
import { MessageFilterControl } from './MessageFilter';
import { useAgentStreaming } from '@/hooks/useAgentStreaming';

export function ChatWindow() {
    const { messages, addMessage, messageFilters, setMessageFilters, showThinking, setShowThinking, processStream } = useAgentStreaming();
    const [input, setInput] = useState('');
    const scrollRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSendMessage = (e: FormEvent) => {
        e.preventDefault();
        if (input.trim()) {
            addMessage(input.trim());
            
            const exampleStream = [
                '{"event": "on_chain_start", "data": {"input": {"messages": [{"content": "I\'m expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?", "additional_kwargs": {}, "response_metadata": {}}], "workloads": [{"run_id": "run-1754454950327", "query": "I\'m expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?", "data_source": {"source_table": "synthetic_data"}, "time_range": {"start_time": "2025-01-01T00:00:00Z", "end_time": "2025-12-31T23:59:59Z"}}], "todo_list": ["triage_request"], "completed_steps": [], "status": "in_progress", "events": [{}]}}, "name": "LangGraph", "tags": [], "run_id": "72b58d45-6dd1-4e44-a367-7c2c656a8b2d", "metadata": {}, "parent_ids": []}',
                "Starting analysis with Run ID: req_cd58cf7f",
                '{"event": "on_chain_start", "data": {"input": {"messages": [{"content": "I\'m expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?", "additional_kwargs": {}, "response_metadata": {}, "id": "0998cca1-5707-43b5-b73e-003c15d7faa0"}]}}, "name": "agent", "tags": ["graph:step:1"], "run_id": "ad9e581a-1126-4f5c-8381-fa132ee79604", "metadata": {"langgraph_step": 1, "langgraph_node": "agent", "langgraph_triggers": ["branch:to:agent"], "langgraph_path": ["__pregel_pull", "agent"], "langgraph_checkpoint_ns": "agent:a9da5197-974c-1289-d3b1-b961e9f61101"}, "parent_ids": ["72b58d45-6dd1-4e44-a367-7c2c656a8b2d"]}',
                '{"event": "on_chain_start", "data": {"input": {"messages": [{"content": "I\'m expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?", "additional_kwargs": {}, "response_metadata": {}, "id": "0998cca1-5707-43b5-b73e-003c15d7faa0"}]}}, "name": "RunnableSequence", "tags": ["seq:step:1"], "run_id": "26905c27-f790-4c4f-b33c-757f03db37cd", "metadata": {"langgraph_step": 1, "langgraph_node": "agent", "langgraph_triggers": ["branch:to:agent"], "langgraph_path": ["__pregel_pull", "agent"], "langgraph_checkpoint_ns": "agent:a9da5197-974c-1289-d3b1-b961e9f61101", "checkpoint_ns": "agent:a9da5197-974c-1289-d3b1-b961e9f61101"}, "parent_ids": ["72b58d45-6dd1-4e44-a367-7c2c656a8b2d", "ad9e581a-1126-4f5c-8381-fa132ee79604"]}',
                '{"event": "on_prompt_start", "data": {"input": {"messages": [{"content": "I\'m expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?", "additional_kwargs": {}, "response_metadata": {}, "id": "0998cca1-5707-43b5-b73e-003c15d7faa0"}]}}, "name": "ChatPromptTemplate", "tags": ["seq:step:1"], "run_id": "8b1e1e8e-b313-4c84-abaa-3b9de1dd60e6", "metadata": {"langgraph_step": 1, "langgraph_node": "agent", "langgraph_triggers": ["branch:to:agent"], "langgraph_path": ["__pregel_pull", "agent"], "langgraph_checkpoint_ns": "agent:a9da5197-974c-1289-d3b1-b961e9f61101", "checkpoint_ns": "agent:a9da5197-974c-1289-d3b1-b961e9f61101"}, "parent_ids": ["72b58d45-6dd1-4e44-a367-7c2c656a8b2d", "ad9e581a-1126-4f5c-8381-fa132ee79604", "26905c27-f790-4c4f-b33c-757f03db37cd"]}',
                '{"event": "on_prompt_end", "data": {"output": {"messages": [{"content": "You are an expert in providing real-time updates. Your goal is to process the user\'s request and stream updates as they happen. Start by creating a todo list of the steps you will take to address the user\'s request. After each step, you must call the `update_state` tool to update the todo list and completed steps. When you have completed all the steps in your todo list and have a final answer, output the final answer followed by the word FINISH.", "additional_kwargs": {}, "response_metadata": {}}, {"content": "I\'m expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?", "additional_kwargs": {}, "response_metadata": {}, "id": "0998cca1-5707-43b5-b73e-003c15d7faa0"}]}, "input": {"messages": [{"content": "I\'m expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?", "additional_kwargs": {}, "response_metadata": {}, "id": "0998cca1-5707-43b5-b73e-003c15d7faa0"}]}}, "run_id": "8b1e1e8e-b313-4c84-abaa-3b9de1dd60e6", "name": "ChatPromptTemplate", "tags": ["seq:step:1"], "metadata": {"langgraph_step": 1, "langgraph_node": "agent", "langgraph_triggers": ["branch:to:agent"], "langgraph_path": ["__pregel_pull", "agent"], "langgraph_checkpoint_ns": "agent:a9da5197-974c-1289-d3b1-b961e9f61101", "checkpoint_ns": "agent:a9da5197-974c-1289-d3b1-b961e9f61101"}, "parent_ids": ["72b58d45-6dd1-4e44-a367-7c2c656a8b2d", "ad9e581a-1126-4f5c-8381-fa132ee79604", "26905c27-f790-4c4f-b33c-757f03db37cd"]}',
                '{"event": "on_chat_model_start", "data": {"input": {"messages": [[{"content": "You are an expert in providing real-time updates. Your goal is to process the user\'s request and stream updates as they happen. Start by creating a todo list of the steps you will take to address the user\'s request. After each step, you must call the `update_state` tool to update the todo list and completed steps. When you have completed all the steps in your todo list and have a final answer, output the final answer followed by the word FINISH.", "additional_kwargs": {}, "response_metadata": {}}, {"content": "I\'m expecting a 50% increase in agent usage next month. How will this impact my costs and rate limits?", "additional_kwargs": {}, "response_metadata": {}, "id": "0998cca1-5707-43b5-b73e-003c15d7faa0"}]]}}, "name": "ChatGoogleGenerativeAI", "tags": ["seq:step:2"], "run_id": "db2fe1cb-fbc8-40df-9f0c-ab90c929a2d7", "metadata": {"langgraph_step": 1, "langgraph_node": "agent", "langgraph_triggers": ["branch:to:agent"], "langgraph_path": ["__pregel_pull", "agent"], "langgraph_checkpoint_ns": "agent:a9da5197-974c-1289-d3b1-b961e9f61101", "checkpoint_ns": "agent:a9da5197-974c-1289-d3b1-b961e9f61101", "ls_provider": "google_genai", "ls_model_name": "gemini-2.5-pro", "ls_model_type": "chat", "ls_temperature": 0.7}, "parent_ids": ["72b58d45-6dd1-4e44-a367-7c2c656a8b2d", "ad9e581a-1126-4f5c-8381-fa132ee79604", "26905c27-f790-4c4f-b33c-757f03db37cd"]}',
                '{"event": "on_chat_model_stream", "data": {"chunk": {"content": "Here is my plan to address your", "additional_kwargs": {}, "response_metadata": {"safety_ratings": []}, "id": "run--db2fe1cb-fbc8-40df-9f0c-ab90c929a2d7", "usage_metadata": {"input_tokens": 2680, "output_tokens": 166, "total_tokens": 2846, "input_token_details": {"cache_read": 0}, "output_token_details": {"reasoning": 159}}}}, "run_id": "db2fe1cb-fbc8-40df-9f0c-ab90c929a2d7", "name": "ChatGoogleGenerativeAI", "tags": ["seq:step:2"], "metadata": {"langgraph_step": 1, "langgraph_node": "agent", "langgraph_triggers": ["branch:to:agent"], "langgraph_path": ["__pregel_pull", "agent"], "langgraph_checkpoint_ns": "agent:a9da5197-974c-1289-d3b1-b961e9f61101", "checkpoint_ns": "agent:a9da5197-974c-1289-d3b1-b961e9f61101", "ls_provider": "google_genai", "ls_model_name": "gemini-2.5-pro", "ls_model_type": "chat", "ls_temperature": 0.7}, "parent_ids": ["72b58d45-6dd1-4e44-a367-7c2c656a8b2d", "ad9e581a-1126-4f5c-8381-fa132ee79604", "26905c27-f790-4c4f-b33c-757f03db37cd"]}',
            ];
            exampleStream.forEach((chunk, index) => {
                setTimeout(() => {
                    processStream(chunk);
                }, index * 500);
            });
            setInput('');
        }
    };

    const isAgentThinking = messages.some(m => m.type === 'thinking');

    return (
        <div className="flex flex-col h-full border rounded-xl shadow-sm">
            <div className="p-4 border-b bg-background rounded-t-xl">
                <MessageFilterControl 
                    messageFilters={messageFilters} 
                    setMessageFilters={setMessageFilters} 
                    showThinking={showThinking} 
                    setShowThinking={setShowThinking} 
                />
            </div>
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((message) => (
                    <MessageOrchestrator key={message.id} message={message} showThinking={showThinking} />
                ))}
            </div>
            <div className="p-4 border-t bg-background rounded-b-xl">
                <form onSubmit={handleSendMessage} className="flex items-center gap-2">
                    <Input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={isAgentThinking ? "Agent is thinking..." : "Type your message..."}
                        disabled={isAgentThinking}
                    />
                    <Button type="submit" size="icon" disabled={isAgentThinking || !input.trim()}>
                        <Send className="h-4 w-4" />
                    </Button>
                </form>
            </div>
        </div>
    );
}

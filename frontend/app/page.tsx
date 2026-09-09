'use client';

import { useState, useEffect, useRef } from 'react';
import { ChatMessage } from '@/components/ChatMessage';
import { ChatInput } from '@/components/ChatInput';
import { getOrCreateThreadId, startNewThread } from '@/lib/thread';
import { sendChatMessage } from '@/lib/transport';
import type { UISupervisorMessage, StreamEvent } from '@/lib/types';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export default function ChatPage() {
  const [messages, setMessages] = useState<UISupervisorMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [threadId, setThreadId] = useState<string>('');
  const [activeTaskId, setActiveTaskId] = useState<string | undefined>();
  const [useMultiAgent, setUseMultiAgent] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setThreadId(getOrCreateThreadId());
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = async (text: string) => {
    const userMessage: UISupervisorMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      tasks: [],
      taskTokens: {},
    };

    const assistantMessage: UISupervisorMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      tasks: [],
      taskTokens: {},
    };

    setMessages(prev => [...prev, userMessage, assistantMessage]);
    setIsStreaming(true);
    setActiveTaskId(undefined);

    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();

    const endpoint = useMultiAgent ? '/chat/supervisor/stream' : '/chat/stream';

    try {
      await sendChatMessage(
        BACKEND_URL,
        endpoint,
        text,
        threadId,
        (event: StreamEvent) => {
          setMessages(prev => {
            const updated = [...prev];
            const lastMsg = updated[updated.length - 1];

            switch (event.type) {
              case 'token':
                lastMsg.content += event.content;
                break;

              case 'plan_created':
                lastMsg.plan = event.plan;
                break;

              case 'task_list_created':
                lastMsg.tasks = event.tasks;
                break;

              case 'task_started':
                lastMsg.tasks = lastMsg.tasks.map(t =>
                  t.id === event.task_id
                    ? { ...t, status: 'in_progress' as const }
                    : t
                );
                setActiveTaskId(event.task_id);
                break;

              case 'task_completed':
                lastMsg.tasks = lastMsg.tasks.map(t =>
                  t.id === event.task_id
                    ? { ...t, status: 'completed' as const, result: event.result_preview }
                    : t
                );
                if (activeTaskId === event.task_id) {
                  setActiveTaskId(undefined);
                }
                break;

              case 'sub_agent_token':
                lastMsg.taskTokens = {
                  ...lastMsg.taskTokens,
                  [event.task_id]: (lastMsg.taskTokens[event.task_id] || '') + event.content,
                };
                break;

              case 'done':
                break;
            }

            return updated;
          });
        },
        abortControllerRef.current.signal,
      );
    } catch (error) {
      if ((error as Error).name !== 'AbortError') {
        console.error('Stream error:', error);
      }
    } finally {
      setIsStreaming(false);
      setActiveTaskId(undefined);
    }
  };

  const handleNewThread = () => {
    abortControllerRef.current?.abort();
    setMessages([]);
    setThreadId(startNewThread());
    setActiveTaskId(undefined);
  };

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto">
      <header className="flex justify-between items-center p-4 border-b">
        <div>
          <h1 className="text-xl font-bold">ICT 운영 지원 Agent</h1>
          <label className="flex items-center gap-2 mt-2 text-sm">
            <input
              type="checkbox"
              checked={useMultiAgent}
              onChange={(e) => setUseMultiAgent(e.target.checked)}
            />
            Multi-Agent 모드 (Supervisor)
          </label>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-xs text-gray-500">
            Thread: {threadId.slice(0, 8)}...
          </span>
          <button
            onClick={handleNewThread}
            className="px-3 py-1 text-sm border rounded hover:bg-gray-100"
          >
            새 대화
          </button>
        </div>
      </header>

      <main className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-400 mt-20">
            메시지를 입력하여 대화를 시작하세요.
          </div>
        ) : (
          messages.map(msg => (
            <ChatMessage
              key={msg.id}
              message={msg}
              activeTaskId={activeTaskId}
            />
          ))
        )}
        <div ref={messagesEndRef} />
      </main>

      <ChatInput onSubmit={handleSubmit} disabled={isStreaming} />
    </div>
  );
}

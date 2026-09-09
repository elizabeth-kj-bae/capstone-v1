'use client';

import { useState, useEffect, useRef } from 'react';
import { ChatMessage } from '@/components/ChatMessage';
import { ChatInput } from '@/components/ChatInput';
import { getOrCreateThreadId, startNewThread } from '@/lib/thread';
import { sendChatMessage } from '@/lib/transport';
import type { UIMessage } from '@/lib/types';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

export default function ChatPage() {
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [threadId, setThreadId] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  
  // 페이지 마운트 시 thread_id 초기화 (옵션 B 적용)
  useEffect(() => {
    setThreadId(getOrCreateThreadId());
  }, []);
  
  // 새 메시지 추가 시 자동 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
  
  const handleSubmit = async (text: string) => {
    // 사용자 메시지 추가
    const userMessage: UIMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      toolCalls: [],
    };
    
    // Assistant 메시지 placeholder 추가 (token이 흘러 들어옴)
    const assistantMessage: UIMessage = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: '',
      toolCalls: [],
    };
    
    setMessages(prev => [...prev, userMessage, assistantMessage]);
    setIsStreaming(true);
    
    // 이전 stream이 진행 중이면 취소
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();
    
    try {
      await sendChatMessage(
        BACKEND_URL,
        text,
        threadId,
        (event) => {
          // 각 SSE event 처리
          setMessages(prev => {
            const updated = [...prev];
            const lastMsg = updated[updated.length - 1];
            
            switch (event.type) {
              case 'token':
                // Token chunk 누적
                lastMsg.content += event.content;
                break;
                
              case 'tool_call_start':
                // 새 tool call 추가 (pending)
                lastMsg.toolCalls.push({
                  toolName: event.tool_name,
                  args: event.args,
                  status: 'pending',
                });
                break;
                
              case 'tool_call_end':
                // 가장 최근의 같은 tool_name pending → completed로 변경
                const pending = lastMsg.toolCalls.findLast(
                  tc => tc.toolName === event.tool_name && tc.status === 'pending'
                );
                if (pending) {
                  pending.status = 'completed';
                  pending.result = event.result;
                }
                break;
                
              case 'done':
                // Stream 정상 종료
                break;
            }
            
            return updated;
          });
        },
        abortControllerRef.current.signal,
      );
    } catch (error) {
      if ((error as Error).name === 'AbortError') {
        console.log('Stream cancelled by user');
      } else {
        console.error('Stream error:', error);
        // 에러를 UI에 표시 (간단한 버전)
        setMessages(prev => {
          const updated = [...prev];
          const lastMsg = updated[updated.length - 1];
          lastMsg.content = `[에러 발생: ${(error as Error).message}]`;
          return updated;
        });
      }
    } finally {
      setIsStreaming(false);
    }
  };
  
  const handleNewThread = () => {
    abortControllerRef.current?.abort();
    setMessages([]);
    setThreadId(startNewThread());
  };
  
  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto">
      {/* Header */}
      <header className="flex justify-between items-center p-4 border-b">
        <h1 className="text-xl font-bold">ICT 운영 지원 Agent</h1>
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
      
      {/* Messages */}
      <main className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-400 mt-20">
            메시지를 입력하여 대화를 시작하세요.
          </div>
        ) : (
          messages.map(msg => <ChatMessage key={msg.id} message={msg} />)
        )}
        <div ref={messagesEndRef} />
      </main>
      
      {/* Input */}
      <ChatInput onSubmit={handleSubmit} disabled={isStreaming} />
    </div>
  );
}

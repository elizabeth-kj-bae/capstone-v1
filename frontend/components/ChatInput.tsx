/**
 * 메시지 입력 폼.
 */

'use client';

import { useState } from 'react';

interface Props {
  onSubmit: (message: string) => void;
  disabled: boolean;
}

export function ChatInput({ onSubmit, disabled }: Props) {
  const [text, setText] = useState('');
  
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setText('');
  };
  
  return (
    <form onSubmit={handleSubmit} className="flex gap-2 p-4 border-t">
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={disabled ? '응답 생성 중...' : '메시지를 입력하세요'}
        disabled={disabled}
        className="flex-1 p-2 border rounded"
      />
      <button
        type="submit"
        disabled={disabled || !text.trim()}
        className="px-4 py-2 bg-blue-500 text-white rounded disabled:bg-gray-400"
      >
        전송
      </button>
    </form>
  );
}

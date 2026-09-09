/**
 * Thread Owner 관리 
 * 
 * 결정: Frontend가 thread_id 생성
 * - 새 대화 시작 시 crypto.randomUUID()로 생성
 * - localStorage에 보관 (페이지 refresh 후에도 thread 유지)
 * - Backend로는 모든 요청에 thread_id 전송
 */

const STORAGE_KEY = 'capstone:active_thread_id';

/**
 * 현재 활성 thread_id를 반환.
 * localStorage에 있으면 그것을 사용, 없으면 새로 생성.
 */
export function getOrCreateThreadId(): string {
  // SSR 환경 (Next.js)에서는 window가 없으므로 임시 ID 반환
  if (typeof window === 'undefined') {
    return 'ssr-placeholder';
  }
  
  const existing = localStorage.getItem(STORAGE_KEY);
  if (existing) {
    return existing;
  }
  
  const newId = crypto.randomUUID();
  localStorage.setItem(STORAGE_KEY, newId);
  return newId;
}

/**
 * 새 대화 시작 — 기존 thread_id 폐기하고 새로 생성.
 * "새로운 대화" 버튼 클릭 시 호출.
 */
export function startNewThread(): string {
  if (typeof window === 'undefined') {
    return 'ssr-placeholder';
  }
  
  const newId = crypto.randomUUID();
  localStorage.setItem(STORAGE_KEY, newId);
  return newId;
}

/**
 * 현재 thread_id 폐기 (대화 종료).
 */
export function clearThread(): void {
  if (typeof window === 'undefined') return;
  localStorage.removeItem(STORAGE_KEY);
}

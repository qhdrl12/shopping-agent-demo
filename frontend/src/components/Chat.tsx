'use client';

import { useState, useRef, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';

interface Message {
  id: string;
  type: 'user' | 'ai' | 'tool' | 'system';
  content: string;
  metadata?: Record<string, unknown>;
  processSteps?: ProcessStep[];
  requestId?: string;
  searchMetadata?: {
    search_query: string;
    search_parameters: string;
    results_count: number;
    search_url: string;
  };
  suggestedQuestions?: string[];
}

interface ProcessStep {
  id: string;
  label: string;
  status: 'pending' | 'running' | 'completed';
  isLongRunning?: boolean;
}

interface ChatState {
  messages: Message[];
  isLoading: boolean;
  sessionId: string | null;
  currentStreamingMessageId: string | null;
  processSteps: ProcessStep[];
  currentRequestId: string | null;
  workflowType: 'general' | 'search' | null;
}

export default function Chat() {
  const [chatState, setChatState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    sessionId: null,
    currentStreamingMessageId: null,
    processSteps: [],
    currentRequestId: null,
    workflowType: null
  });
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 카카오페이 결제 처리 함수
  const handleKakaoPayment = async (productUrl: string) => {
    try {
      // 상품 정보를 URL에서 추출하거나 기본값 설정
      const productName = "무신사 상품"; // 실제로는 AI 응답에서 상품명을 추출해야 함
      const totalAmount = 100000; // 실제로는 AI 응답에서 가격을 추출해야 함
      
      console.log('Initiating Kakao Pay payment for:', productUrl);
      
      // 결제 준비 API 호출
      const response = await fetch('http://localhost:8000/payment/ready', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          product_name: productName,
          product_url: productUrl,
          quantity: 1,
          total_amount: totalAmount,
          tax_free_amount: 0
        })
      });

      if (!response.ok) {
        throw new Error('결제 준비 요청이 실패했습니다.');
      }

      const paymentData = await response.json();
      console.log('Payment ready response:', paymentData);

      // 카카오페이 결제창으로 리다이렉트
      if (paymentData.next_redirect_pc_url) {
        window.location.href = paymentData.next_redirect_pc_url;
      } else {
        throw new Error('결제 URL을 받을 수 없습니다.');
      }
    } catch (error) {
      console.error('Kakao Pay error:', error);
      alert('결제 처리 중 오류가 발생했습니다. ' + (error as Error).message);
    }
  };

  // Define unified process steps - same for all requests but different execution paths
  const getProcessSteps = (): ProcessStep[] => {
    return [
      { id: 'start', label: '요청 처리 시작', status: 'pending' },
      { id: 'analyze_query', label: '사용자 의도 파악', status: 'pending' },
      { id: 'optimize_search_query', label: '무신사 검색 최적화', status: 'pending' },
      { id: 'search_products', label: '상품 데이터 수집', status: 'pending', isLongRunning: true },
      { id: 'filter_product_links', label: '관련 상품 필터링', status: 'pending' },
      { id: 'extract_product_data', label: '상세 정보 추출', status: 'pending', isLongRunning: true },
      { id: 'validate_and_select', label: '최적 상품 선별', status: 'pending' },
      { id: 'generate_final_response', label: '답변 생성', status: 'pending' }
    ];
  };




  // Render suggested questions component
  const renderSuggestedQuestions = (questions: string[]) => {
    if (!questions || questions.length === 0) {
      return null;
    }
    
    return (
      <div className="mt-6">
        <div className="bg-gradient-to-br from-gray-800/60 to-gray-900/60 backdrop-blur-xl border border-gray-600/30 rounded-2xl p-6 shadow-xl">
          <div className="flex items-center space-x-3 mb-5">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center shadow-lg">
              <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clipRule="evenodd" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              💡 이런 것도 궁금하지 않으세요?
            </h3>
          </div>
          
          <div className="grid grid-cols-1 gap-3">
            {questions.map((question, index) => (
              <button
                key={index}
                onClick={() => sendExampleMessage(question)}
                disabled={chatState.isLoading}
                className="group relative p-4 rounded-xl bg-gradient-to-r from-gray-700/40 to-gray-800/40 hover:from-purple-700/30 hover:to-pink-700/30 backdrop-blur-sm border border-gray-600/20 hover:border-purple-500/40 transition-all duration-300 transform hover:scale-105 hover:shadow-lg hover:shadow-purple-500/20 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100 text-left overflow-hidden"
              >
                <div className="flex items-center space-x-3 relative z-10">
                  <div className="flex-shrink-0">
                    <div className="w-6 h-6 rounded-full bg-purple-500/20 border border-purple-400/30 flex items-center justify-center group-hover:bg-purple-500/30 group-hover:border-purple-400/50 transition-all duration-200">
                      <span className="text-xs font-bold text-purple-400 group-hover:text-purple-300">
                        {index + 1}
                      </span>
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-gray-200 font-medium leading-relaxed group-hover:text-white transition-colors duration-200">
                      {question}
                    </p>
                  </div>
                  <div className="flex-shrink-0">
                    <svg className="w-4 h-4 text-gray-400 group-hover:text-purple-300 transition-all duration-200 transform group-hover:translate-x-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
                
                {/* Shine effect on hover */}
                <div className="absolute top-0 -left-4 w-24 h-full bg-gradient-to-r from-transparent via-white/10 to-transparent rotate-12 transform -translate-x-full group-hover:translate-x-full transition-transform duration-700 ease-in-out"></div>
                
                {/* Background glow effect */}
                <div className="absolute inset-0 bg-gradient-to-r from-purple-600/5 via-pink-600/5 to-purple-600/5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 rounded-xl"></div>
              </button>
            ))}
          </div>
          
          <div className="mt-5 flex items-center justify-center space-x-2 text-sm text-gray-400">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M6.672 1.911a1 1 0 10-1.932.518l.259.966a1 1 0 001.932-.518l-.26-.966zM2.429 4.74a1 1 0 10-.517 1.932l.966.259a1 1 0 00.517-1.932l-.966-.26zm8.814-.569a1 1 0 00-1.415-1.414l-.707.707a1 1 0 101.415 1.414l.707-.707zm-7.071 7.072l.707-.707A1 1 0 003.465 9.12l-.708.707a1 1 0 001.415 1.415zm3.2-5.171a1 1 0 00-1.3 1.3l4 10a1 1 0 001.823.075l1.38-2.759 3.018 3.02a1 1 0 001.414-1.415l-3.019-3.02 2.76-1.379a1 1 0 00-.076-1.822l-10-4z" clipRule="evenodd" />
            </svg>
            <span>클릭하면 바로 질문할 수 있어요</span>
          </div>
        </div>
      </div>
    );
  };

  // Render search metadata component
  const renderSearchMetadata = (searchMetadata: Message['searchMetadata']) => {
    if (!searchMetadata) return null;

    return (
      <div className="mb-4">
        <div className="bg-gradient-to-br from-emerald-800/60 to-emerald-900/60 backdrop-blur-xl border border-emerald-600/30 rounded-2xl p-5 shadow-xl">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg">
              <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-emerald-100">검색 정보</h3>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <span className="text-emerald-400 font-medium">검색어:</span>
                <span className="text-gray-200 bg-emerald-900/30 px-2 py-1 rounded-md border border-emerald-700/30">
                  {searchMetadata.search_query}
                </span>
              </div>
              
              {searchMetadata.search_parameters && (
                <div className="flex items-start space-x-2">
                  <span className="text-emerald-400 font-medium">필터:</span>
                  <span className="text-gray-300 bg-emerald-900/20 px-2 py-1 rounded-md text-xs font-mono border border-emerald-700/20">
                    {searchMetadata.search_parameters}
                  </span>
                </div>
              )}
            </div>
            
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <span className="text-emerald-400 font-medium">찾은 상품 수:</span>
                <span className="text-emerald-200 font-semibold">
                  {searchMetadata.results_count}개
                </span>
              </div>
              
              <div className="flex items-start space-x-2">
                <span className="text-emerald-400 font-medium">무신사 링크:</span>
                <a 
                  href={searchMetadata.search_url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="text-emerald-300 hover:text-emerald-200 underline decoration-emerald-500/50 hover:decoration-emerald-400 transition-colors duration-200 text-xs break-all"
                >
                  검색 결과 보기 →
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };

  // Render process steps component for a specific message
  const renderProcessSteps = (steps: ProcessStep[]) => {
    if (!steps || steps.length === 0) return null;

    return (
      <div className="mb-6">
        <div className="bg-gradient-to-br from-gray-800/60 to-gray-900/60 backdrop-blur-xl border border-gray-600/30 rounded-2xl p-6 shadow-xl">
          <div className="flex items-center space-x-3 mb-4">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-lg">
              <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-100">처리 진행 상황</h3>
          </div>
          
          <div className="space-y-3">
            {steps.map((step) => {
              // Step-specific icons
              const getStepIcon = (stepId: string, status: string) => {
                const iconMap: {[key: string]: string} = {
                  'start': '🚀',
                  'analyze_query': '🧠',
                  'optimize_search_query': '🔍',
                  'search_products': '🛍️',
                  'filter_product_links': '⚡',
                  'extract_product_data': '📋',
                  'validate_and_select': '✨',
                  'generate_final_response': '🎯',
                  'generate_suggested_questions': '💡'
                };
                
                if (status === 'completed') return '✅';
                if (status === 'running') return iconMap[stepId] || '⚙️';
                return '⚪';
              };

              return (
                <div key={step.id} className="flex items-center space-x-3 animate-fade-in">
                  <div className="flex-shrink-0">
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center transition-all duration-300 ${
                      step.status === 'completed' ? 'bg-emerald-500/20 border-2 border-emerald-500' :
                      step.status === 'running' ? 'bg-blue-500/20 border-2 border-blue-500 animate-pulse' :
                      'bg-gray-500/20 border-2 border-gray-500'
                    }`}>
                      <span className="text-xs">
                        {getStepIcon(step.id, step.status)}
                      </span>
                    </div>
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className={`text-sm font-medium transition-colors duration-300 ${
                      step.status === 'completed' ? 'text-emerald-300' :
                      step.status === 'running' ? 'text-blue-300' : 'text-gray-400'
                    }`}>
                      {step.label}
                    </div>
                    {step.status === 'running' && (
                      <div className="flex items-center space-x-2 mt-1">
                        <div className={`h-1 rounded-full bg-blue-500/30 overflow-hidden ${
                          step.isLongRunning ? 'w-20' : 'w-14'
                        }`}>
                          <div className="h-full bg-blue-500 animate-pulse w-full"></div>
                        </div>
                        {step.isLongRunning && (
                          <span className="text-xs text-blue-400">처리 중...</span>
                        )}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex-shrink-0">
                    {step.status === 'running' && (
                      <div className="flex items-center space-x-1 text-xs text-blue-400">
                        <div className="w-2 h-2 bg-blue-400 rounded-full animate-ping"></div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatState.messages]);

  const sendMessageWithQuery = async (query: string) => {
    if (!query.trim() || chatState.isLoading) return;

    const requestId = Date.now().toString();
    const initialSteps = getProcessSteps(); // Get unified steps for all requests
    // Keep all steps as pending initially - they'll be updated by workflow events
    // No need to set any as running here

    const userMessage: Message = {
      id: requestId,
      type: 'user',
      content: query.trim(),
      processSteps: initialSteps,
      requestId: requestId
    };

    const sessionIdToSend = chatState.sessionId || crypto.randomUUID();

    setChatState(prev => {
      return {
        ...prev,
        messages: [...prev.messages, userMessage],
        isLoading: true,
        sessionId: sessionIdToSend, // Update session ID in state
        currentStreamingMessageId: null, // Reset streaming message ID for new conversation
        processSteps: initialSteps, // Keep for current processing
        currentRequestId: requestId,
        workflowType: null // Reset workflow type for each new request
      };
    });

    setInput('');

    console.log(`session_id: ${sessionIdToSend}`)

    try {
      const response = await fetch('http://localhost:8000/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: query.trim(),
          session_id: sessionIdToSend
        })
      });

      if (!response.ok) {
        throw new Error('Network response was not ok');
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No reader available');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            console.log('Received data:', data); // 디버깅 로그
            
            if (data === '[DONE]') {
              setChatState(prev => ({ ...prev, isLoading: false }));
              break;
            }
            
            try {
              // Skip empty or invalid data lines
              if (!data || data.trim() === '') {
                console.log('Skipping empty data line');
                continue;
              }
              
              const parsed = JSON.parse(data);
              console.log('Parsed data:', parsed); // 디버깅 로그
              
              if (parsed.error) {
                throw new Error(parsed.error);
              }
              
              // Update session ID
              if (parsed.session_id) {
                setChatState(prev => ({ ...prev, sessionId: parsed.session_id }));
              }
              
              // Handle different types of streaming data
              if (parsed.type === 'step') {
                
                const stepId = parsed.current_step;
                
                // Skip generate_suggested_questions step in UI (runs in background)
                if (stepId === 'generate_suggested_questions') {
                  continue;
                }
                
                // Determine if this is a completion step
                const isCompletion = stepId.includes('_') && !['analyze_query', 'optimize_search_query', 'search_products', 'filter_product_links', 'extract_product_data', 'validate_and_select', 'generate_final_response', 'generate_suggested_questions', 'handle_general_query'].includes(stepId);
                
                setChatState(prev => {
                  // Detect workflow type and update steps accordingly
                  let workflowType = prev.workflowType;
                  let stepsToUse = [...prev.processSteps]; // Create a copy to avoid mutation
                  
                  // If we hit handle_general_query, this is a general workflow
                  if (stepId === 'handle_general_query' && prev.workflowType !== 'general') {
                    console.log('Detected general workflow - fast-forwarding to final response');
                    workflowType = 'general';
                    
                    // Fast-forward: Complete all intermediate steps and jump to final response
                    stepsToUse = stepsToUse.map(step => {
                      if (['start', 'analyze_query', 'optimize_search_query', 'search_products', 'filter_product_links', 'extract_product_data', 'validate_and_select'].includes(step.id)) {
                        return { ...step, status: 'completed' as const };
                      }
                      if (step.id === 'generate_final_response') {
                        return { ...step, status: 'running' as const };
                      }
                      return step;
                    });
                  }
                  // If we hit optimize_search_query, this is a search workflow
                  else if (stepId === 'optimize_search_query' && prev.workflowType !== 'search') {
                    console.log('Detected search workflow - proceeding step by step');
                    workflowType = 'search';
                    // Continue with normal step processing
                  }
                  
                  // Define step order based on workflow type (generate_suggested_questions is hidden but runs in background)
                  const stepOrder = workflowType === 'general' 
                    ? ['start', 'analyze_query', 'generate_final_response'] // General: skip intermediate steps
                    : ['start', 'analyze_query', 'optimize_search_query', 'search_products', 'filter_product_links', 'extract_product_data', 'validate_and_select', 'generate_final_response']; // Search: all steps
                  
                  // Skip step processing if we already fast-forwarded for general workflow
                  let updatedSteps = stepsToUse;
                  
                  // ========================================
                  // 단계 상태 업데이트 로직
                  // ========================================
                  // 일반 워크플로우에서 이미 fast-forward 처리된 경우가 아니라면
                  // 단계별 상태를 업데이트합니다.
                  if (workflowType !== 'general' || stepId !== 'handle_general_query') {
                    updatedSteps = stepsToUse.map(step => {
                      // 현재 실행 중인 단계와 각 단계의 순서를 계산
                      const currentStepIndex = stepOrder.indexOf(stepId);
                      const thisStepIndex = stepOrder.indexOf(step.id);
                      
                      
                      // ========================================
                      // 2. 완료 단계 처리 (isCompletion = true)
                      // ========================================
                      // 백엔드에서 "단계명_완료" 형태의 이벤트가 올 때
                      // 해당하는 단계를 완료 상태로 표시
                      if (isCompletion) {
                        // 각 완료 이벤트와 매칭되는 단계를 찾아서 완료 처리
                        if (stepId === 'query_analyzed' && step.id === 'analyze_query') {
                          return { ...step, status: 'completed' as const };
                        }
                        if (stepId === 'search_optimized' && step.id === 'optimize_search_query') {
                          return { ...step, status: 'completed' as const };
                        }
                        if (stepId === 'search_completed' && step.id === 'search_products') {
                          return { ...step, status: 'completed' as const };
                        }
                        if (stepId === 'links_filtered' && step.id === 'filter_product_links') {
                          return { ...step, status: 'completed' as const };
                        }
                        if (stepId === 'data_extracted' && step.id === 'extract_product_data') {
                          return { ...step, status: 'completed' as const };
                        }
                        if (stepId === 'products_selected' && step.id === 'validate_and_select') {
                          return { ...step, status: 'completed' as const };
                        }
                        // 매칭되지 않는 단계는 그대로 유지
                        return step;
                      } else {
                        // ========================================
                        // 3. 순차적 단계 처리 (isCompletion = false)
                        // ========================================
                        // 새로운 단계가 시작될 때 단계들의 상태를 순차적으로 업데이트
                        // 핵심 원칙: 한 번에 하나의 단계만 'running' 상태
                        
                        // 3-1. 이전 단계들을 모두 완료 처리
                        // 현재 단계보다 앞선 단계들은 자동으로 완료 상태로 변경
                        if (currentStepIndex > thisStepIndex) {
                          return { ...step, status: 'completed' as const };
                        }
                        
                        // 3-2. 현재 실행 중인 단계 표시
                        // stepId와 일치하는 단계를 실행 중으로 표시
                        // 특별 케이스: 'extracting_product_details'는 'extract_product_data' 단계에 매핑
                        if (step.id === stepId || (stepId === 'extracting_product_details' && step.id === 'extract_product_data')) {
                          return { ...step, status: 'running' as const };
                        }
                        
                        // 3-3. 미래 단계들은 대기 상태 유지
                        // 현재 단계보다 나중 단계들은 pending 상태로 유지
                        if (currentStepIndex < thisStepIndex) {
                          return { ...step, status: 'pending' as const };
                        }
                      }
                      
                      // 어떤 조건에도 해당하지 않는 경우 기존 상태 유지
                      return step;
                    });
                  }
                  
                  // Also update the processSteps in the corresponding user message
                  const updatedMessages = prev.messages.map(msg => {
                    if (msg.requestId === prev.currentRequestId && msg.type === 'user') {
                      return { ...msg, processSteps: updatedSteps };
                    }
                    return msg;
                  });

                  console.log(`Updated workflow type to: ${workflowType}, steps count: ${updatedSteps.length}`);

                  return {
                    ...prev,
                    processSteps: updatedSteps,
                    messages: updatedMessages,
                    workflowType: workflowType
                  };
                });
              } else if (parsed.type === 'step_complete') {
                // Handle step completion - explicitly mark step as completed
                
                // Skip generate_suggested_questions step completion in UI
                if (parsed.completed_step === 'generate_suggested_questions') {
                  continue;
                }
                
                setChatState(prev => {
                  const updatedSteps = prev.processSteps.map(step => {
                    if (step.id === parsed.completed_step) {
                      return { ...step, status: 'completed' as const };
                    }
                    return step;
                  });
                  
                  // Also update the processSteps in the corresponding user message
                  const updatedMessages = prev.messages.map(msg => {
                    if (msg.requestId === prev.currentRequestId && msg.type === 'user') {
                      return { ...msg, processSteps: updatedSteps };
                    }
                    return msg;
                  });

                  return {
                    ...prev,
                    processSteps: updatedSteps,
                    messages: updatedMessages
                  };
                });
              } else if (parsed.type === 'search_metadata') {
                // Handle search metadata display
                console.log('Received search metadata:', parsed.metadata);
                
                setChatState(prev => {
                  // Update the corresponding user message with search metadata
                  const updatedMessages = prev.messages.map(msg => {
                    if (msg.requestId === prev.currentRequestId && msg.type === 'user') {
                      return { ...msg, searchMetadata: parsed.metadata };
                    }
                    return msg;
                  });

                  return {
                    ...prev,
                    messages: updatedMessages
                  };
                });
              } else if (parsed.type === 'generating_start') {
                // Start generating response - don't show message, just prepare for streaming
                console.log('Starting response generation...');
              } else if (parsed.type === 'token') {
                // Handle token-level streaming with smooth animation
                setChatState(prev => {
                  let newMessages = [...prev.messages];
                  
                  // Check if we have a current streaming message ID
                  if (prev.currentStreamingMessageId) {
                    // Find and update the current streaming message
                    const messageIndex = newMessages.findIndex(msg => msg.id === prev.currentStreamingMessageId);
                    if (messageIndex !== -1) {
                      newMessages[messageIndex] = {
                        ...newMessages[messageIndex],
                        content: newMessages[messageIndex].content + parsed.content
                      };
                    }
                  } else {
                    // Remove system messages (including LLM processing messages) when answer starts
                    console.log('Starting new AI response, clearing system messages and process steps');
                    newMessages = newMessages.filter(msg => msg.type !== 'system');
                    
                    // Mark all steps as completed for the current request
                    const completedSteps = prev.processSteps.map(step => ({ ...step, status: 'completed' as const }));
                    
                    // Update the corresponding user message with completed steps
                    const updatedMessages = newMessages.map(msg => {
                      if (msg.requestId === prev.currentRequestId && msg.type === 'user') {
                        return { ...msg, processSteps: completedSteps };
                      }
                      return msg;
                    });
                    
                    // Create new AI message for this streaming session
                    const newMessageId = Date.now().toString() + '_ai';
                    updatedMessages.push({
                      id: newMessageId,
                      type: 'ai',
                      content: parsed.content,
                      metadata: { isStreaming: true, streamStartTime: Date.now() } // Mark as streaming for UI effects
                    });
                    
                    return { 
                      ...prev, 
                      messages: updatedMessages,
                      currentStreamingMessageId: newMessageId,
                      processSteps: [] // Clear process steps when AI response starts
                    };
                  }
                  
                  return { ...prev, messages: newMessages };
                });
              } else if (parsed.type === 'tool_start') {
                // Handle tool call start
                const toolDisplayNames: {[key: string]: string} = {
                  'search_products': '제품 검색',
                  'extract_product_data': '제품 정보 추출',
                  'scrape_product': '제품 상세 정보 수집'
                };
                
                const displayName = toolDisplayNames[parsed.tool_name] || parsed.tool_name;
                
                setChatState(prev => ({
                  ...prev,
                  messages: [...prev.messages, {
                    id: Date.now().toString() + '_tool',
                    type: 'tool',
                    content: `🔧 ${displayName} 중...`,
                    metadata: {
                      tool_name: parsed.tool_name,
                      tool_input: parsed.tool_input,
                      status: 'running'
                    }
                  }]
                }));
              } else if (parsed.type === 'tool_end') {
                // Handle tool call completion
                setChatState(prev => {
                  const newMessages = [...prev.messages];
                  // Find the last tool message with the same tool name
                  for (let i = newMessages.length - 1; i >= 0; i--) {
                    if (newMessages[i].type === 'tool' && 
                        newMessages[i].metadata?.tool_name === parsed.tool_name &&
                        newMessages[i].metadata?.status === 'running') {
                      
                      const toolDisplayNames: {[key: string]: string} = {
                        'search_products': '제품 검색',
                        'extract_product_data': '제품 정보 추출',
                        'scrape_product': '제품 상세 정보 수집'
                      };
                      
                      const displayName = toolDisplayNames[parsed.tool_name] || parsed.tool_name;
                      
                      // Format tool output for display
                      let outputSummary = '';
                      if (parsed.tool_output) {
                        if (typeof parsed.tool_output === 'string') {
                          outputSummary = parsed.tool_output.length > 100 
                            ? parsed.tool_output.substring(0, 100) + '...' 
                            : parsed.tool_output;
                        } else {
                          outputSummary = JSON.stringify(parsed.tool_output).length > 100
                            ? JSON.stringify(parsed.tool_output).substring(0, 100) + '...'
                            : JSON.stringify(parsed.tool_output);
                        }
                      }
                      
                      newMessages[i] = {
                        ...newMessages[i],
                        content: `✅ ${displayName} 완료`,
                        metadata: {
                          ...newMessages[i].metadata,
                          tool_output: parsed.tool_output,
                          output_summary: outputSummary,
                          status: 'completed'
                        }
                      };
                      break;
                    }
                  }
                  return { ...prev, messages: newMessages };
                });
              } else if (parsed.type === 'complete') {
                // Handle final completion
                setChatState(prev => {
                  let newMessages = [...prev.messages];
                  
                  // Remove any remaining system messages (progress indicators)
                  newMessages = newMessages.filter(msg => msg.type !== 'system');
                  
                  // If response is provided and no streaming AI message exists, add it as fallback
                  if (parsed.response && !prev.currentStreamingMessageId) {
                    // Check if we already have any AI messages from streaming
                    const hasAIMessage = newMessages.some(msg => msg.type === 'ai');
                    if (!hasAIMessage) {
                      // Only add fallback if no AI message exists
                      newMessages.push({
                        id: Date.now().toString() + '_ai',
                        type: 'ai',
                        content: parsed.response,
                        suggestedQuestions: parsed.suggested_questions || []
                      });
                    }
                  }
                  
                  // Mark all steps as completed for the current request
                  const completedSteps = prev.processSteps.map(step => ({ ...step, status: 'completed' as const }));
                  
                  // Update the corresponding user message with completed steps and remove streaming indicator
                  const finalMessages = newMessages.map(msg => {
                    if (msg.requestId === prev.currentRequestId && msg.type === 'user') {
                      return { ...msg, processSteps: completedSteps };
                    }
                    // Remove streaming indicator from AI messages and add suggested questions
                    if (msg.type === 'ai' && msg.metadata?.isStreaming) {
                      return { 
                        ...msg, 
                        metadata: { ...msg.metadata, isStreaming: false },
                        suggestedQuestions: parsed.suggested_questions || []
                      };
                    }
                    return msg;
                  });
                  
                  return { 
                    ...prev, 
                    messages: finalMessages,
                    isLoading: false,
                    currentStreamingMessageId: null, // Reset after completion
                    processSteps: [], // Clear global process steps
                    currentRequestId: null // Reset current request
                  };
                });
              }
            } catch (parseError) {
              console.error('Error parsing SSE data:', parseError, 'Raw data:', data);
              // If it's a critical parsing error, continue to next line instead of breaking
              if (data && data.trim() !== '') {
                console.error('Failed to parse non-empty data:', data);
              }
            }
          }
        }
        
        // Handle stream completion
        console.log('Stream completed');
        setChatState(prev => ({
          ...prev,
          isLoading: false
          // Don't clear process steps here - they should be cleared when AI response starts
        }));
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setChatState(prev => {
        // Remove all system messages and add error message
        const filteredMessages = prev.messages.filter(msg => msg.type !== 'system');
        
        return {
          ...prev,
          isLoading: false,
          currentStreamingMessageId: null,
          processSteps: [], // Clear process steps on error
          messages: [
            ...filteredMessages,
            {
              id: Date.now().toString() + '_error',
              type: 'ai',
              content: '죄송합니다. 연결에 문제가 발생했습니다. 잠시 후 다시 시도해주세요.'
            }
          ]
        };
      });
    }
  };

  const sendMessage = async () => {
    await sendMessageWithQuery(input);
  };

  const sendExampleMessage = async (exampleQuery: string) => {
    if (chatState.isLoading) return;
    setInput(exampleQuery);
    await sendMessageWithQuery(exampleQuery);
  };

  const getMessageStyle = (type: string) => {
    switch (type) {
      case 'user':
        return 'bg-gradient-to-br from-blue-600/90 to-indigo-700/90 text-white ml-auto shadow-2xl border border-blue-400/30 backdrop-blur-xl';
      case 'ai':
        return 'bg-gradient-to-br from-gray-900/95 to-slate-800/95 text-gray-100 mr-auto shadow-2xl border border-gray-700/40 backdrop-blur-xl';
      case 'tool':
        return 'bg-gradient-to-br from-emerald-500/15 to-emerald-600/15 text-emerald-200 mr-auto border border-emerald-400/30 backdrop-blur-xl shadow-lg';
      case 'system':
        return 'bg-gradient-to-br from-amber-500/15 to-amber-600/15 text-amber-200 mr-auto border border-amber-400/30 backdrop-blur-xl shadow-lg';
      default:
        return 'bg-gradient-to-br from-gray-800/80 to-gray-900/80 text-gray-200 mr-auto backdrop-blur-xl border border-gray-600/30';
    }
  };

  const getMessageIcon = (type: string) => {
    switch (type) {
      case 'user':
        return (
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg border border-blue-400/40">
            <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd" />
            </svg>
          </div>
        );
      case 'ai':
        return (
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-pink-600 flex items-center justify-center shadow-lg border border-purple-400/40">
            <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" strokeWidth="2" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        );
      case 'tool':
        return (
          <div className="w-6 h-6 rounded-full bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center shadow-md border border-emerald-400/40">
            <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
            </svg>
          </div>
        );
      case 'system':
        return (
          <div className="w-6 h-6 rounded-full bg-gradient-to-br from-gray-500 to-gray-600 flex items-center justify-center shadow-md border border-gray-400/40">
            <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
            </svg>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-gray-900 to-slate-800">
      {/* Animated background */}
      <div className="fixed inset-0 overflow-hidden">
        <div className="absolute -inset-10 opacity-50">
          <div className="absolute top-0 -left-4 w-72 h-72 bg-purple-500 rounded-full mix-blend-multiply filter blur-xl animate-blob opacity-20"></div>
          <div className="absolute top-0 -right-4 w-72 h-72 bg-cyan-500 rounded-full mix-blend-multiply filter blur-xl animate-blob animation-delay-2000 opacity-20"></div>
          <div className="absolute -bottom-8 left-20 w-72 h-72 bg-pink-500 rounded-full mix-blend-multiply filter blur-xl animate-blob animation-delay-4000 opacity-20"></div>
        </div>
      </div>

      <div className="relative flex flex-col h-screen">
        {/* Header */}
        <div className="backdrop-blur-xl bg-gray-900/70 border-b border-gray-700/50 px-6 py-6 shadow-2xl">
          <div className="flex items-center space-x-4">
            <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center shadow-lg">
              <span className="text-2xl">🛍️</span>
            </div>
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                무신사 쇼핑 AI
              </h1>
              <p className="text-gray-400 text-sm font-medium">
                AI 기반 패션 아이템 추천 서비스
              </p>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {chatState.messages.length === 0 && (
            <div className="text-center text-gray-400 mt-32">
              <div className="relative">
                <div className="w-32 h-32 mx-auto mb-8 bg-gradient-to-br from-blue-500/20 to-purple-600/20 rounded-full flex items-center justify-center backdrop-blur-xl border border-gray-600/20 shadow-2xl">
                  <span className="text-6xl">✨</span>
                </div>
                <div className="absolute top-0 left-1/2 transform -translate-x-1/2 w-32 h-32 bg-gradient-to-r from-blue-500 to-purple-600 rounded-full opacity-20 animate-ping"></div>
              </div>
              <h2 className="text-3xl font-bold text-gray-200 mb-4">안녕하세요!</h2>
              <p className="text-lg text-gray-400 mb-6">무신사에서 원하는 제품을 찾아드리겠습니다</p>
              
              {/* Example Query Buttons */}
              <div className="max-w-4xl mx-auto mb-8">
                <p className="text-sm text-gray-400 mb-4 text-center">아래 예시를 클릭해서 바로 시작해보세요!</p>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {[
                    {
                      emoji: "🧥",
                      title: "겨울 아우터",
                      query: "20만원 이하 겨울 코트 추천해줘",
                      gradient: "from-blue-500/20 to-cyan-500/20",
                      hoverGradient: "hover:from-blue-400/30 hover:to-cyan-400/30",
                      borderColor: "border-blue-400/30"
                    },
                    {
                      emoji: "👟",
                      title: "운동화",
                      query: "나이키 운동화 찾아줘",
                      gradient: "from-emerald-500/20 to-teal-500/20",
                      hoverGradient: "hover:from-emerald-400/30 hover:to-teal-400/30",
                      borderColor: "border-emerald-400/30"
                    },
                    {
                      emoji: "👔",
                      title: "정장",
                      query: "면접용 정장 세트 추천해줘",
                      gradient: "from-purple-500/20 to-pink-500/20",
                      hoverGradient: "hover:from-purple-400/30 hover:to-pink-400/30",
                      borderColor: "border-purple-400/30"
                    },
                    {
                      emoji: "🎒",
                      title: "가방",
                      query: "대학생 백팩 추천해줘",
                      gradient: "from-orange-500/20 to-red-500/20",
                      hoverGradient: "hover:from-orange-400/30 hover:to-red-400/30",
                      borderColor: "border-orange-400/30"
                    },
                    {
                      emoji: "🧢",
                      title: "모자",
                      query: "캐주얼한 모자 찾아줘",
                      gradient: "from-indigo-500/20 to-blue-500/20",
                      hoverGradient: "hover:from-indigo-400/30 hover:to-blue-400/30",
                      borderColor: "border-indigo-400/30"
                    },
                    {
                      emoji: "👕",
                      title: "티셔츠",
                      query: "봄 반팔 티셔츠 추천해줘",
                      gradient: "from-green-500/20 to-lime-500/20",
                      hoverGradient: "hover:from-green-400/30 hover:to-lime-400/30",
                      borderColor: "border-green-400/30"
                    }
                  ].map((example, index) => (
                    <button
                      key={index}
                      onClick={() => sendExampleMessage(example.query)}
                      disabled={chatState.isLoading}
                      className={`
                        group relative p-6 rounded-2xl 
                        bg-gradient-to-br ${example.gradient} ${example.hoverGradient}
                        backdrop-blur-xl border ${example.borderColor}
                        transition-all duration-500 transform 
                        hover:scale-105 hover:shadow-xl hover:shadow-black/20
                        disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100
                        overflow-hidden
                      `}
                    >
                      {/* Background animation */}
                      <div className="absolute inset-0 bg-gradient-to-r from-white/5 to-white/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                      
                      {/* Content */}
                      <div className="relative z-10 text-center space-y-3">
                        <div className="text-4xl mb-2 transform group-hover:scale-110 transition-transform duration-300">
                          {example.emoji}
                        </div>
                        <h3 className="font-bold text-white text-lg mb-2">
                          {example.title}
                        </h3>
                        <p className="text-gray-300 text-sm leading-relaxed">
                          {example.query}
                        </p>
                        
                        {/* Click indicator */}
                        <div className="flex items-center justify-center space-x-2 mt-4 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                          <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{animationDelay: '0ms'}}></div>
                          <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{animationDelay: '150ms'}}></div>
                          <div className="w-2 h-2 bg-white/60 rounded-full animate-bounce" style={{animationDelay: '300ms'}}></div>
                        </div>
                      </div>
                      
                      {/* Shine effect */}
                      <div className="absolute top-0 -left-4 w-24 h-full bg-gradient-to-r from-transparent via-white/20 to-transparent rotate-12 transform -translate-x-full group-hover:translate-x-full transition-transform duration-1000 ease-in-out"></div>
                    </button>
                  ))}
                </div>
              </div>
              
              <div className="space-y-2 text-sm text-gray-500">
                <p className="inline-block bg-gray-800/50 px-4 py-2 rounded-full backdrop-blur-sm border border-gray-700/30">
                  💡 직접 입력하거나 위 버튼을 클릭해보세요
                </p>
              </div>
            </div>
          )}


          {chatState.messages.map((message, index) => {
            if (message.type === 'user') {
              return (
                <div key={index} className="animate-fade-in mb-6">
                  <div className="flex justify-end mb-4">
                    <div className={`max-w-2xl px-6 py-4 rounded-3xl ${getMessageStyle(message.type)}`}>
                      <div className="flex items-start space-x-3">
                        <div className="flex-1 min-w-0">
                          <div className="text-white font-medium leading-relaxed">
                            {message.content}
                          </div>
                        </div>
                        <div className="flex-shrink-0">
                          {getMessageIcon(message.type)}
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Show process steps for this user message - only if still processing */}
                  {message.processSteps && message.processSteps.length > 0 && 
                   message.processSteps.some(step => step.status === 'running' || step.status === 'pending') && (
                    <div className="flex justify-start mb-4">
                      <div className="max-w-4xl w-full">
                        {renderProcessSteps(message.processSteps)}
                      </div>
                    </div>
                  )}

                  {/* Show search metadata when available - only if still processing (same as process steps) */}
                  {message.searchMetadata && message.processSteps && message.processSteps.length > 0 && 
                   message.processSteps.some(step => step.status === 'running' || step.status === 'pending') && (
                    <div className="flex justify-start mb-4">
                      <div className="max-w-4xl w-full">
                        {renderSearchMetadata(message.searchMetadata)}
                      </div>
                    </div>
                  )}
                </div>
              );
            } else if (message.type === 'ai') {
              return (
                <div key={index} className="flex justify-start animate-fade-in mb-8">
                  <div className="max-w-5xl w-full">
                    {/* AI 헤더 */}
                    <div className="flex items-center space-x-3 mb-4">
                      {getMessageIcon(message.type)}
                      <div className="flex items-center space-x-2">
                        <span className="text-lg font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                          무신사 쇼핑 AI
                        </span>
                        {message.metadata?.isStreaming ? (
                          <div className="flex items-center space-x-2">
                            <div className="flex space-x-1">
                              <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                              <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" style={{animationDelay: '0.2s'}}></div>
                              <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse" style={{animationDelay: '0.4s'}}></div>
                            </div>
                            <span className="text-xs text-green-400 font-medium">실시간 응답 중</span>
                          </div>
                        ) : (
                          <div className="flex space-x-1">
                            <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse"></div>
                            <div className="w-2 h-2 bg-pink-400 rounded-full animate-pulse" style={{animationDelay: '0.2s'}}></div>
                            <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" style={{animationDelay: '0.4s'}}></div>
                          </div>
                        )}
                      </div>
                    </div>
                    
                    {/* AI 응답 카드 */}
                    <div className={`${getMessageStyle(message.type)} rounded-3xl overflow-hidden ${
                      message.metadata?.isStreaming ? 'animate-pulse-subtle' : ''
                    }`}>
                      <div className="p-8">
                        <div className="prose prose-invert prose-lg max-w-none">
                          <div className="relative">
                            <ReactMarkdown
                              remarkPlugins={[remarkGfm]}
                              rehypePlugins={[rehypeHighlight]}
                              components={{
                              // Custom styling for markdown elements
                              h1: ({...props}) => (
                                <h1 className="text-3xl font-bold text-white mb-6 pb-3 border-b border-gray-600/40 flex items-center space-x-3" {...props}>
                                  <span className="text-2xl">🎯</span>
                                  <span>{props.children}</span>
                                </h1>
                              ),
                              h2: ({...props}) => (
                                <h2 className="text-2xl font-bold text-gray-100 mb-5 mt-8 flex items-center space-x-3" {...props}>
                                  {/* <span className="text-xl">🔍</span> */}
                                  <span>{props.children}</span>
                                </h2>
                              ),
                              h3: ({...props}) => (
                                <h3 className="text-xl font-semibold text-gray-200 mb-4 mt-6 flex items-center space-x-2" {...props}>
                                  {/* <span className="text-lg">🏆</span> */}
                                  <span>{props.children}</span>
                                </h3>
                              ),
                              h4: ({...props}) => (
                                <h4 className="text-lg font-semibold text-gray-200 mb-3 mt-5 flex items-center space-x-2" {...props}>
                                  {/* <span className="text-base">{/1순위|🥇/.test(props.children?.toString() || '') ? '🥇' : /2순위|🥈/.test(props.children?.toString() || '') ? '🥈' : /3순위|🥉/.test(props.children?.toString() || '') ? '🥉' : '💡'}</span> */}
                                  <span>{props.children}</span>
                                </h4>
                              ),
                              ul: ({...props}) => <ul className="text-gray-200 space-y-2 ml-4 mb-4" {...props} />,
                              ol: ({...props}) => <ol className="text-gray-200 space-y-2 ml-4 mb-4" {...props} />,
                              li: ({...props}) => <li className="text-gray-200 flex items-start space-x-2" {...props} />,
                              strong: ({...props}) => <strong className="text-white font-bold" {...props} />,
                              em: ({...props}) => <em className="text-blue-300 italic font-medium" {...props} />,
                              code: ({...props}) => <code className="bg-gray-700/60 text-cyan-300 px-2 py-1 rounded-md font-mono text-sm" {...props} />,
                              pre: ({...props}) => (
                                <pre className="bg-gray-800/60 border border-gray-600/40 rounded-xl p-6 overflow-x-auto backdrop-blur-sm mb-4" {...props} />
                              ),
                              blockquote: ({...props}) => (
                                <blockquote className="border-l-4 border-purple-500/60 pl-6 text-gray-300 italic bg-gray-800/30 py-4 rounded-r-xl mb-4" {...props} />
                              ),
                              table: ({...props}) => (
                                <div className="overflow-x-auto mb-6">
                                  <div className="bg-gray-800/40 rounded-xl border border-gray-600/40 overflow-hidden">
                                    <table className="min-w-full" {...props} />
                                  </div>
                                </div>
                              ),
                              th: ({...props}) => <th className="bg-gray-700/60 text-gray-100 px-6 py-4 text-left font-bold" {...props} />,
                              td: ({...props}) => <td className="border-t border-gray-600/40 px-6 py-4 text-gray-200" {...props} />,
                              a: ({href, children, ...props}) => {
                                const childText = children?.toString() || '';
                                
                                // 구매하기 또는 SHOP NOW 링크인 경우 특별한 버튼 스타일 적용
                                if (childText.includes('SHOP NOW') || childText.includes('구매하기')) {
                                  return (
                                    <div className="my-6 flex justify-center space-x-4">
                                      <a
                                        href={href}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="group relative inline-flex items-center justify-center px-6 py-3 bg-gradient-to-r from-cyan-500/10 via-blue-500/10 to-purple-500/10 hover:from-cyan-400/20 hover:via-blue-400/20 hover:to-purple-400/20 text-cyan-400 hover:text-cyan-300 font-bold rounded-2xl transition-all duration-500 transform hover:scale-105 hover:shadow-xl hover:shadow-cyan-400/25 border border-cyan-400/30 hover:border-cyan-300/50 backdrop-blur-lg relative overflow-hidden"
                                        {...props}
                                      >
                                        <div className="absolute inset-0 bg-gradient-to-r from-cyan-600/5 via-blue-600/5 to-purple-600/5 animate-pulse"></div>
                                        <div className="relative flex items-center space-x-3">
                                          <div className="p-1.5 rounded-full bg-cyan-400/10 border border-cyan-400/20">
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                            </svg>
                                          </div>
                                          <span className="text-base font-bold tracking-wide">상세보기</span>
                                        </div>
                                      </a>
                                      
                                      {/* 바로결제 버튼 */}
                                      <button
                                        onClick={(e) => {
                                          e.preventDefault();
                                          handleKakaoPayment(href || '');
                                        }}
                                        className="group relative inline-flex items-center justify-center px-6 py-3 bg-gradient-to-r from-yellow-400/90 via-amber-400/90 to-orange-400/90 hover:from-yellow-300 hover:via-amber-300 hover:to-orange-300 text-black font-bold rounded-2xl transition-all duration-500 transform hover:scale-105 hover:shadow-xl hover:shadow-yellow-400/40 border border-yellow-300/50 hover:border-yellow-200/70 backdrop-blur-lg relative overflow-hidden"
                                      >
                                        <div className="absolute inset-0 bg-gradient-to-r from-yellow-200/20 via-amber-200/20 to-orange-200/20 animate-pulse"></div>
                                        <div className="relative flex items-center space-x-3">
                                          <div className="p-1.5 rounded-full bg-yellow-600/20 border border-yellow-500/30">
                                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                            </svg>
                                          </div>
                                          <span className="text-base font-bold tracking-wide">바로결제</span>
                                        </div>
                                      </button>
                                    </div>
                                  );
                                }
                                // 일반 링크는 기본 스타일
                                return <a href={href} className="text-blue-400 hover:text-blue-300 underline underline-offset-2 transition-colors font-medium" {...props}>{children}</a>;
                              },
                              p: ({...props}) => <p className="text-gray-200 mb-4 leading-relaxed" {...props} />,
                              img: ({src, alt, ...props}) => {
                                if (!src) return null;
                                
                                // Simple image rendering without carousel overhead
                                return (
                                  <div className="my-4">
                                    <div className="relative group">
                                      <img
                                        src={src}
                                        alt={alt || "Product image"}
                                        className="w-full max-w-4xl h-[800px] object-cover rounded-2xl shadow-2xl mx-auto block border border-gray-600/30 transition-transform duration-300 group-hover:scale-105"
                                        loading="lazy"
                                        onError={(e) => {
                                          console.log('Image failed to load:', src);
                                          e.currentTarget.style.display = 'none';
                                        }}
                                        {...props}
                                      />
                                      <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent rounded-2xl pointer-events-none"></div>
                                    </div>
                                  </div>
                                );
                              }
                            }}
                            >
                              {message.content}
                            </ReactMarkdown>
                            {(message.metadata as {isStreaming?: boolean})?.isStreaming && (
                              <span className="inline-block w-2 h-5 bg-green-400 animate-pulse ml-1 rounded-sm"></span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                    
                    {/* Render suggested questions after AI response */}
                    {message.suggestedQuestions && message.suggestedQuestions.length > 0 && (
                      renderSuggestedQuestions(message.suggestedQuestions)
                    )}
                  </div>
                </div>
              );
            } else {
              // system, tool 메시지들
              return (
                <div key={index} className="flex justify-center animate-fade-in mb-4">
                  <div className={`px-4 py-2 rounded-full ${getMessageStyle(message.type)} max-w-md text-center`}>
                    <div className="flex items-center justify-center space-x-2">
                      <div className="flex-shrink-0">
                        {getMessageIcon(message.type)}
                      </div>
                      <div className="text-sm font-medium">
                        {message.content}
                      </div>
                    </div>
                    {message.metadata && message.type === 'tool' && (
                      <details className="mt-2 text-xs opacity-75">
                        <summary className="cursor-pointer hover:text-gray-300 transition-colors">상세 정보</summary>
                        <pre className="mt-2 bg-gray-800/50 p-2 rounded border border-gray-600/30 backdrop-blur-sm font-mono text-xs text-left">
                          {JSON.stringify(message.metadata, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                </div>
              );
            }
          })}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="backdrop-blur-xl bg-gray-900/70 border-t border-gray-700/50 px-6 py-6 shadow-2xl">
          <div className="flex space-x-4 max-w-4xl mx-auto">
            <div className="relative flex-1">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                placeholder="원하는 제품을 설명해주세요..."
                className="w-full px-6 py-4 bg-gray-800/50 backdrop-blur-xl border border-gray-600/30 rounded-2xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50 text-gray-100 placeholder-gray-400 font-medium shadow-lg transition-all duration-300"
                disabled={chatState.isLoading}
              />
              {chatState.isLoading && (
                <div className="absolute right-4 top-1/2 transform -translate-y-1/2">
                  <div className="w-5 h-5 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
                </div>
              )}
            </div>
            <button
              onClick={sendMessage}
              disabled={chatState.isLoading || !input.trim()}
              className="px-8 py-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-2xl hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-300 shadow-lg backdrop-blur-xl border border-blue-500/20 hover:shadow-blue-500/25 hover:shadow-xl"
            >
              {chatState.isLoading ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              ) : (
                <span className="flex items-center space-x-2">
                  <span>전송</span>
                  <span>✨</span>
                </span>
              )}
            </button>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes blob {
          0% {
            transform: translate(0px, 0px) scale(1);
          }
          33% {
            transform: translate(30px, -50px) scale(1.1);
          }
          66% {
            transform: translate(-20px, 20px) scale(0.9);
          }
          100% {
            transform: translate(0px, 0px) scale(1);
          }
        }
        
        @keyframes fade-in {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        @keyframes pulse-subtle {
          0%, 100% {
            box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.2);
          }
          50% {
            box-shadow: 0 0 0 8px rgba(34, 197, 94, 0.05);
          }
        }
        
        .animate-blob {
          animation: blob 7s infinite;
        }
        
        .animation-delay-2000 {
          animation-delay: 2s;
        }
        
        .animation-delay-4000 {
          animation-delay: 4s;
        }
        
        .animate-fade-in {
          animation: fade-in 0.5s ease-out;
        }
        
        .animate-pulse-subtle {
          animation: pulse-subtle 2s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}
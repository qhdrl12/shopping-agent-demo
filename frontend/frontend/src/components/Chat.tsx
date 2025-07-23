'use client';

import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';

interface Message {
  id: string;
  type: 'user' | 'ai' | 'tool' | 'system';
  content: string;
  metadata?: any;
}

interface ChatState {
  messages: Message[];
  isLoading: boolean;
  sessionId: string | null;
  currentStreamingMessageId: string | null;
}

export default function Chat() {
  const [chatState, setChatState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    sessionId: null,
    currentStreamingMessageId: null
  });
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [chatState.messages]);

  const sendMessage = async () => {
    if (!input.trim() || chatState.isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: input.trim()
    };

    const sessionIdToSend = chatState.sessionId || crypto.randomUUID();

    setChatState(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage, {
        id: Date.now().toString() + '_loading',
        type: 'system',
        content: '🔄 처리를 시작하고 있습니다...'
      }],
      isLoading: true,
      sessionId: sessionIdToSend, // Update session ID in state
      currentStreamingMessageId: null // Reset streaming message ID for new conversation
    }));

    setInput('');

    console.log(`session_id: ${sessionIdToSend}`)

    try {
      const response = await fetch('http://localhost:8000/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: input.trim(),
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
      let currentMessageIndex = -1;

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
                // Show only meaningful processing steps
                console.log(`Processing step: ${parsed.current_step}`);
                
                // Map step names to user-friendly messages
                const stepMessages: {[key: string]: string} = {
                  // Node names from workflow (in-progress states)
                  'start': '처리를 시작하고 있습니다...',
                  'analyze_query': '질문 분석 중입니다...',
                  'optimize_search_query': '검색어 최적화 중입니다...',
                  'search_products': '제품 검색 중입니다...',
                  'filter_product_links': '검색 결과 필터링 중입니다...',
                  'extracting_product_details': '상품 상세정보를 수집 중',
                  'extract_product_data': '제품 상세정보 검색 중입니다...',
                  'validate_and_select': '제품 정보 검증 중입니다...',
                  'generate_final_response': '답변을 생성 중입니다...',
                  'handle_general_query': '답변 생성 중입니다...',
                  
                  // Step values from nodes (completion states)
                  'query_analyzed': '질문 분석이 완료되었습니다',
                  'search_optimized': '검색어 최적화를 완료했습니다',
                  'search_completed': '제품 검색을 완료했습니다',
                  'links_filtered': '검색 결과 필터링을 완료했습니다',
                  'data_extracted': '제품 상세정보 검색을 완료했습니다',
                  'products_selected': '제품 선별을 완료했습니다',
                  'completed': '모든 처리가 완료되었습니다'
                };
                
                const message = stepMessages[parsed.current_step];
                
                // Show step message if defined, otherwise show generic message
                const displayMessage = message || `${parsed.current_step} 처리 중...`;
                
                // Choose icon based on whether it's in-progress or completion
                const isCompletion = parsed.current_step.includes('_') && !['analyze_query', 'optimize_search_query', 'search_products', 'filter_product_links', 'extract_product_data', 'validate_and_select', 'generate_final_response', 'handle_general_query'].includes(parsed.current_step);
                const icon = isCompletion ? '✅' : '🔄';
                
                setChatState(prev => {
                  // Remove all existing system messages to show only the latest one
                  const filteredMessages = prev.messages.filter(msg => msg.type !== 'system');
                  
                  // Add new step message
                  const newMessages = [...filteredMessages, {
                    id: Date.now().toString() + '_step',
                    type: 'system',
                    content: `${icon} ${displayMessage}`,
                    metadata: {
                      step_type: isCompletion ? 'completion' : 'progress',
                      step_name: parsed.current_step
                    }
                  }];
                  
                  return {
                    ...prev,
                    messages: newMessages
                  };
                });
                
                if (!message) {
                  console.log(`Unknown step: ${parsed.current_step}`);
                }
              } else if (parsed.type === 'generating_start') {
                // Start generating response - don't show message, just prepare for streaming
                console.log('Starting response generation...');
              } else if (parsed.type === 'token') {
                // Handle token-level streaming
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
                    console.log('Starting new AI response, clearing system messages');
                    newMessages = newMessages.filter(msg => msg.type !== 'system');
                    
                    // Create new AI message for this streaming session
                    const newMessageId = Date.now().toString() + '_ai';
                    newMessages.push({
                      id: newMessageId,
                      type: 'ai',
                      content: parsed.content
                    });
                    
                    return { 
                      ...prev, 
                      messages: newMessages,
                      currentStreamingMessageId: newMessageId
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
              } else if (parsed.type === 'llm_processing') {
                // Handle LLM processing status
                setChatState(prev => ({
                  ...prev,
                  messages: [...prev.messages, {
                    id: Date.now().toString() + '_llm',
                    type: 'system',
                    content: `🧠 ${parsed.message}`,
                    metadata: {
                      node_name: parsed.node_name,
                      status: 'llm_processing'
                    }
                  }]
                }));
              } else if (parsed.type === 'complete') {
                // Handle final completion
                console.log('Received completion signal');
                setChatState(prev => {
                  let newMessages = [...prev.messages];
                  
                  // Remove any remaining system messages (progress indicators)
                  newMessages = newMessages.filter(msg => msg.type !== 'system');
                  
                  // If response is provided and no AI message exists, add it
                  if (parsed.response && !prev.currentStreamingMessageId) {
                    // Only add if we don't have a streaming message
                    newMessages.push({
                      id: Date.now().toString() + '_ai',
                      type: 'ai',
                      content: parsed.response
                    });
                  }
                  
                  return { 
                    ...prev, 
                    messages: newMessages,
                    isLoading: false,
                    currentStreamingMessageId: null // Reset after completion
                  };
                });
              }
            } catch (parseError) {
              console.error('Error parsing SSE data:', parseError, 'Raw data:', data);
            }
          }
        }
        
        // Handle stream completion
        console.log('Stream completed');
        setChatState(prev => ({
          ...prev,
          isLoading: false
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

  const getMessageStyle = (type: string, metadata?: any) => {
    switch (type) {
      case 'user':
        return 'bg-gradient-to-br from-blue-600/90 to-indigo-700/90 text-white ml-auto shadow-2xl border border-blue-400/30 backdrop-blur-xl';
      case 'ai':
        return 'bg-gradient-to-br from-gray-900/95 to-slate-800/95 text-gray-100 mr-auto shadow-2xl border border-gray-700/40 backdrop-blur-xl';
      case 'tool':
        return 'bg-gradient-to-br from-emerald-500/15 to-emerald-600/15 text-emerald-200 mr-auto border border-emerald-400/30 backdrop-blur-xl shadow-lg';
      case 'system':
        // Special styling for LLM processing messages
        if (metadata?.status === 'llm_processing') {
          return 'bg-gradient-to-br from-purple-500/15 to-purple-600/15 text-purple-200 mr-auto border border-purple-400/30 backdrop-blur-xl shadow-lg';
        }
        // Different styling for progress vs completion
        if (metadata?.step_type === 'completion') {
          return 'bg-gradient-to-br from-emerald-500/15 to-emerald-600/15 text-emerald-200 mr-auto border border-emerald-400/30 backdrop-blur-xl shadow-lg';
        }
        if (metadata?.step_type === 'progress') {
          // Special styling for extracting_product_details
          if (metadata?.step_name === 'extracting_product_details') {
            return 'bg-gradient-to-br from-cyan-600/90 to-cyan-700/90 text-white mr-auto border border-cyan-400/40 font-medium shadow-2xl backdrop-blur-xl';
          }
          return 'bg-gradient-to-br from-blue-500/15 to-blue-600/15 text-blue-200 mr-auto border border-blue-400/30 backdrop-blur-xl shadow-lg';
        }
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
              <p className="text-lg text-gray-400 mb-2">무신사에서 원하는 제품을 찾아드리겠습니다</p>
              <div className="space-y-2 text-sm text-gray-500">
                <p className="inline-block bg-gray-800/50 px-4 py-2 rounded-full backdrop-blur-sm border border-gray-700/30">
                  💡 예: "20만원 이하 겨울 코트 추천해줘"
                </p>
                <p className="inline-block bg-gray-800/50 px-4 py-2 rounded-full backdrop-blur-sm border border-gray-700/30 ml-2">
                  ⚡ 예: "나이키 운동화 찾아줘"
                </p>
              </div>
            </div>
          )}

          {chatState.messages.map((message, index) => {
            if (message.type === 'user') {
              return (
                <div key={index} className="flex justify-end animate-fade-in mb-6">
                  <div className={`max-w-2xl px-6 py-4 rounded-3xl ${getMessageStyle(message.type, message.metadata)}`}>
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
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-purple-400 rounded-full animate-pulse"></div>
                          <div className="w-2 h-2 bg-pink-400 rounded-full animate-pulse" style={{animationDelay: '0.2s'}}></div>
                          <div className="w-2 h-2 bg-blue-400 rounded-full animate-pulse" style={{animationDelay: '0.4s'}}></div>
                        </div>
                      </div>
                    </div>
                    
                    {/* AI 응답 카드 */}
                    <div className={`${getMessageStyle(message.type, message.metadata)} rounded-3xl overflow-hidden`}>
                      <div className="p-8">
                        <div className="prose prose-invert prose-lg max-w-none">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            rehypePlugins={[rehypeHighlight]}
                            components={{
                              // Custom styling for markdown elements
                              h1: ({node, ...props}) => (
                                <h1 className="text-3xl font-bold text-white mb-6 pb-3 border-b border-gray-600/40 flex items-center space-x-3" {...props}>
                                  <span className="text-2xl">🎯</span>
                                  <span>{props.children}</span>
                                </h1>
                              ),
                              h2: ({node, ...props}) => (
                                <h2 className="text-2xl font-bold text-gray-100 mb-5 mt-8 flex items-center space-x-3" {...props}>
                                  {/* <span className="text-xl">🔍</span> */}
                                  <span>{props.children}</span>
                                </h2>
                              ),
                              h3: ({node, ...props}) => (
                                <h3 className="text-xl font-semibold text-gray-200 mb-4 mt-6 flex items-center space-x-2" {...props}>
                                  {/* <span className="text-lg">🏆</span> */}
                                  <span>{props.children}</span>
                                </h3>
                              ),
                              h4: ({node, ...props}) => (
                                <h4 className="text-lg font-semibold text-gray-200 mb-3 mt-5 flex items-center space-x-2" {...props}>
                                  {/* <span className="text-base">{/1순위|🥇/.test(props.children?.toString() || '') ? '🥇' : /2순위|🥈/.test(props.children?.toString() || '') ? '🥈' : /3순위|🥉/.test(props.children?.toString() || '') ? '🥉' : '💡'}</span> */}
                                  <span>{props.children}</span>
                                </h4>
                              ),
                              p: ({node, ...props}) => <p className="text-gray-200 mb-4 leading-relaxed" {...props} />,
                              ul: ({node, ...props}) => <ul className="text-gray-200 space-y-2 ml-4 mb-4" {...props} />,
                              ol: ({node, ...props}) => <ol className="text-gray-200 space-y-2 ml-4 mb-4" {...props} />,
                              li: ({node, ...props}) => <li className="text-gray-200 flex items-start space-x-2" {...props} />,
                              strong: ({node, ...props}) => <strong className="text-white font-bold" {...props} />,
                              em: ({node, ...props}) => <em className="text-blue-300 italic font-medium" {...props} />,
                              code: ({node, ...props}) => <code className="bg-gray-700/60 text-cyan-300 px-2 py-1 rounded-md font-mono text-sm" {...props} />,
                              pre: ({node, ...props}) => (
                                <pre className="bg-gray-800/60 border border-gray-600/40 rounded-xl p-6 overflow-x-auto backdrop-blur-sm mb-4" {...props} />
                              ),
                              blockquote: ({node, ...props}) => (
                                <blockquote className="border-l-4 border-purple-500/60 pl-6 text-gray-300 italic bg-gray-800/30 py-4 rounded-r-xl mb-4" {...props} />
                              ),
                              table: ({node, ...props}) => (
                                <div className="overflow-x-auto mb-6">
                                  <div className="bg-gray-800/40 rounded-xl border border-gray-600/40 overflow-hidden">
                                    <table className="min-w-full" {...props} />
                                  </div>
                                </div>
                              ),
                              th: ({node, ...props}) => <th className="bg-gray-700/60 text-gray-100 px-6 py-4 text-left font-bold" {...props} />,
                              td: ({node, ...props}) => <td className="border-t border-gray-600/40 px-6 py-4 text-gray-200" {...props} />,
                              a: ({node, href, children, ...props}) => {
                                const childText = children?.toString() || '';
                                
                                // 구매하기 또는 SHOP NOW 링크인 경우 특별한 버튼 스타일 적용
                                if (childText.includes('SHOP NOW') || childText.includes('구매하기')) {
                                  return (
                                    <div className="my-8 flex justify-center space-x-4">
                                      <a
                                        href={href}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="group relative inline-flex items-center justify-center px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold rounded-2xl transition-all duration-300 transform hover:scale-105 hover:shadow-2xl hover:shadow-purple-500/25 border border-blue-500/40 backdrop-blur-sm"
                                        {...props}
                                      >
                                        <div className="flex items-center space-x-3">
                                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                                          </svg>
                                          <span className="text-lg">상세보기</span>
                                        </div>
                                      </a>
                                      
                                      {/* 바로결제 버튼 */}
                                      <a
                                        href={href}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="group relative inline-flex items-center justify-center px-8 py-4 bg-gradient-to-r from-yellow-400 to-yellow-500 hover:from-yellow-300 hover:to-yellow-400 text-gray-900 font-bold rounded-2xl transition-all duration-300 transform hover:scale-105 hover:shadow-2xl hover:shadow-yellow-400/40 border border-yellow-500/50 backdrop-blur-sm"
                                      >
                                        <div className="flex items-center space-x-3">
                                          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z" />
                                          </svg>
                                          <span className="text-lg">바로결제</span>
                                        </div>
                                      </a>
                                    </div>
                                  );
                                }
                                // 일반 링크는 기본 스타일
                                return <a href={href} className="text-blue-400 hover:text-blue-300 underline underline-offset-2 transition-colors font-medium" {...props}>{children}</a>;
                              },
                              img: ({node, src, alt, ...props}) => (
                                <div className="my-6">
                                  <div className="relative group">
                                    <img
                                      src={src}
                                      alt={alt}
                                      className="w-full max-w-3xl h-[500px] object-cover rounded-2xl shadow-2xl mx-auto block border border-gray-600/30 transition-transform duration-300 group-hover:scale-105"
                                      {...props}
                                    />
                                    <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent rounded-2xl pointer-events-none"></div>
                                  </div>
                                </div>
                              )
                            }}
                          >
                            {message.content}
                          </ReactMarkdown>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            } else {
              // system, tool 메시지들
              return (
                <div key={index} className="flex justify-center animate-fade-in mb-4">
                  <div className={`px-4 py-2 rounded-full ${getMessageStyle(message.type, message.metadata)} max-w-md text-center`}>
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
      `}</style>
    </div>
  );
}
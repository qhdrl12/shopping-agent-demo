'use client';

import { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github.css';

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

    setChatState(prev => ({
      ...prev,
      messages: [...prev.messages, userMessage, {
        id: Date.now().toString() + '_loading',
        type: 'system',
        content: '🔄 처리를 시작하고 있습니다...'
      }],
      isLoading: true,
      currentStreamingMessageId: null // Reset streaming message ID for new conversation
    }));

    setInput('');

    try {
      const response = await fetch('http://localhost:8000/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: input.trim(),
          session_id: chatState.sessionId
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
                  'extract_search_keywords': '검색 키워드 추출 중입니다...',
                  'search_products': '제품 검색 중입니다...',
                  'filter_product_links': '검색 결과 필터링 중입니다...',
                  'extracting_product_details': '상품 상세정보를 수집 중',
                  'extract_product_data': '제품 상세정보 검색 중입니다...',
                  'validate_and_select': '제품 정보 검증 중입니다...',
                  'generate_final_response': '답변을 생성 중입니다...',
                  'handle_general_query': '답변 생성 중입니다...',
                  
                  // Step values from nodes (completion states)
                  'query_analyzed': '질문 분석이 완료되었습니다',
                  'keywords_extracted': '검색 키워드 추출을 완료했습니다',
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
                const isCompletion = parsed.current_step.includes('_') && !['analyze_query', 'extract_search_keywords', 'search_products', 'filter_product_links', 'extract_product_data', 'validate_and_select', 'generate_final_response', 'handle_general_query'].includes(parsed.current_step);
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
        return 'bg-blue-500 text-white ml-auto';
      case 'ai':
        return 'bg-white text-gray-800 mr-auto border border-gray-200 shadow-sm';
      case 'tool':
        return 'bg-green-100 text-green-800 mr-auto border-l-4 border-green-500';
      case 'system':
        // Special styling for LLM processing messages
        if (metadata?.status === 'llm_processing') {
          return 'bg-purple-100 text-purple-800 mr-auto border-l-4 border-purple-500';
        }
        // Different styling for progress vs completion
        if (metadata?.step_type === 'completion') {
          return 'bg-green-100 text-green-800 mr-auto border-l-4 border-green-500';
        }
        if (metadata?.step_type === 'progress') {
          // Special styling for extracting_product_details
          if (metadata?.step_name === 'extracting_product_details') {
            return 'bg-blue-500 text-white mr-auto border-l-4 border-blue-700 font-medium';
          }
          return 'bg-blue-100 text-blue-800 mr-auto border-l-4 border-blue-500';
        }
        return 'bg-yellow-100 text-yellow-800 mr-auto border-l-4 border-yellow-500';
      default:
        return 'bg-gray-100 text-gray-800 mr-auto';
    }
  };

  const getMessageIcon = (type: string) => {
    switch (type) {
      case 'user':
        return '👤';
      case 'ai':
        return '🤖';
      case 'tool':
        return '🔧';
      case 'system':
        return '💡';
      default:
        return '';
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b px-6 py-4">
        <h1 className="text-2xl font-bold text-gray-800">
          무신사 쇼핑 AI 에이전트
        </h1>
        <p className="text-sm text-gray-600">
          원하는 제품을 찾아드리겠습니다. 무엇을 찾고 계신가요?
        </p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {chatState.messages.length === 0 && (
          <div className="text-center text-gray-500 mt-20">
            <div className="text-6xl mb-4">🛍️</div>
            <p className="text-xl mb-2">안녕하세요!</p>
            <p className="text-sm">
              무신사에서 원하는 제품을 찾아드리겠습니다.<br />
              예: "20만원 이하 겨울 코트 추천해줘" 또는 "나이키 운동화 찾아줘"
            </p>
          </div>
        )}

        {
          chatState.messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-2xl px-4 py-3 rounded-lg ${getMessageStyle(message.type, message.metadata)}`}
            >
              <div className="flex items-start space-x-2">
                <span className="text-lg">{getMessageIcon(message.type)}</span>
                <div className="flex-1">
                  {message.type === 'ai' ? (
                    <div className="max-w-none">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        rehypePlugins={[rehypeHighlight]}
                      >
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <div className="whitespace-pre-wrap">{message.content}</div>
                  )}
                  {message.metadata && message.type === 'tool' && (
                    <details className="mt-2 text-xs opacity-75">
                      <summary className="cursor-pointer">상세 정보</summary>
                      <pre className="mt-1 bg-black/10 p-2 rounded">
                        {JSON.stringify(message.metadata, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}


        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-white border-t px-6 py-4">
        <div className="flex space-x-4">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="원하는 제품을 설명해주세요..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900 bg-white placeholder-gray-500"
            disabled={chatState.isLoading}
          />
          <button
            onClick={sendMessage}
            disabled={chatState.isLoading || !input.trim()}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            전송
          </button>
        </div>
      </div>
    </div>
  );
}
'use client';

import { useEffect, useState } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';

interface PaymentResult {
  aid: string;
  tid: string;
  cid: string;
  partner_order_id: string;
  partner_user_id: string;
  payment_method_type: string;
  amount: {
    total: number;
    tax_free: number;
    vat: number;
    point: number;
    discount: number;
  };
  item_name: string;
  quantity: number;
  created_at: string;
  approved_at: string;
}

export default function PaymentSuccess() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [paymentResult, setPaymentResult] = useState<PaymentResult | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const approvePayment = async () => {
      const pgToken = searchParams.get('pg_token');
      const tid = searchParams.get('tid');

      if (!pgToken || !tid) {
        setError('결제 정보가 올바르지 않습니다.');
        setIsLoading(false);
        return;
      }

      try {
        console.log('Approving payment with tid:', tid, 'pg_token:', pgToken);
        
        const response = await fetch('http://localhost:8000/payment/approve', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            tid: tid,
            pg_token: pgToken
          })
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail?.error_message || '결제 승인에 실패했습니다.');
        }

        const result = await response.json();
        console.log('Payment approved:', result);
        setPaymentResult(result);
      } catch (error) {
        console.error('Payment approval error:', error);
        setError((error as Error).message);
      } finally {
        setIsLoading(false);
      }
    };

    approvePayment();
  }, [searchParams]);

  const handleGoHome = () => {
    router.push('/');
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-gray-900 to-slate-800 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500/30 border-t-blue-500 rounded-full animate-spin mx-auto mb-4"></div>
          <h2 className="text-2xl font-bold text-white mb-2">결제 처리 중...</h2>
          <p className="text-gray-400">잠시만 기다려주세요.</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-gray-900 to-slate-800 flex items-center justify-center">
        <div className="max-w-md w-full mx-auto bg-red-900/20 backdrop-blur-xl border border-red-600/30 rounded-3xl p-8 text-center">
          <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold text-red-400 mb-4">결제 실패</h1>
          <p className="text-gray-300 mb-6">{error}</p>
          <button
            onClick={handleGoHome}
            className="w-full px-6 py-3 bg-gradient-to-r from-gray-600 to-gray-700 text-white font-semibold rounded-xl hover:from-gray-700 hover:to-gray-800 transition-all duration-300"
          >
            홈으로 돌아가기
          </button>
        </div>
      </div>
    );
  }

  if (!paymentResult) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-gray-900 to-slate-800 flex items-center justify-center">
        <div className="text-center text-gray-400">
          <p>결제 정보를 불러올 수 없습니다.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-gray-900 to-slate-800">
      {/* Animated background */}
      <div className="fixed inset-0 overflow-hidden">
        <div className="absolute -inset-10 opacity-50">
          <div className="absolute top-0 -left-4 w-72 h-72 bg-green-500 rounded-full mix-blend-multiply filter blur-xl animate-blob opacity-20"></div>
          <div className="absolute top-0 -right-4 w-72 h-72 bg-blue-500 rounded-full mix-blend-multiply filter blur-xl animate-blob animation-delay-2000 opacity-20"></div>
          <div className="absolute -bottom-8 left-20 w-72 h-72 bg-purple-500 rounded-full mix-blend-multiply filter blur-xl animate-blob animation-delay-4000 opacity-20"></div>
        </div>
      </div>

      <div className="relative flex items-center justify-center min-h-screen p-6">
        <div className="max-w-2xl w-full mx-auto">
          {/* Success Header */}
          <div className="text-center mb-8">
            <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-6 animate-bounce">
              <svg className="w-10 h-10 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-green-400 to-blue-400 bg-clip-text text-transparent mb-4">
              결제 완료!
            </h1>
            <p className="text-xl text-gray-300">
              카카오페이 결제가 성공적으로 처리되었습니다.
            </p>
          </div>

          {/* Payment Details */}
          <div className="bg-gradient-to-br from-gray-900/95 to-slate-800/95 backdrop-blur-xl border border-gray-700/40 rounded-3xl p-8 shadow-2xl mb-8">
            <h2 className="text-2xl font-bold text-white mb-6 flex items-center">
              <span className="text-2xl mr-3">📋</span>
              결제 상세 정보
            </h2>
            
            <div className="space-y-4">
              <div className="flex justify-between items-center py-3 border-b border-gray-700/30">
                <span className="text-gray-400 font-medium">상품명</span>
                <span className="text-white font-semibold">{paymentResult.item_name}</span>
              </div>
              
              <div className="flex justify-between items-center py-3 border-b border-gray-700/30">
                <span className="text-gray-400 font-medium">수량</span>
                <span className="text-white font-semibold">{paymentResult.quantity}개</span>
              </div>
              
              <div className="flex justify-between items-center py-3 border-b border-gray-700/30">
                <span className="text-gray-400 font-medium">결제 금액</span>
                <span className="text-2xl font-bold text-green-400">
                  {paymentResult.amount.total.toLocaleString()}원
                </span>
              </div>
              
              <div className="flex justify-between items-center py-3 border-b border-gray-700/30">
                <span className="text-gray-400 font-medium">결제 방법</span>
                <span className="text-white font-semibold">
                  {paymentResult.payment_method_type === 'MONEY' ? '카카오페이 머니' : 
                   paymentResult.payment_method_type === 'CARD' ? '카드 결제' : 
                   paymentResult.payment_method_type}
                </span>
              </div>
              
              <div className="flex justify-between items-center py-3 border-b border-gray-700/30">
                <span className="text-gray-400 font-medium">주문번호</span>
                <span className="text-white font-mono text-sm">{paymentResult.partner_order_id}</span>
              </div>
              
              <div className="flex justify-between items-center py-3 border-b border-gray-700/30">
                <span className="text-gray-400 font-medium">거래번호</span>
                <span className="text-white font-mono text-sm">{paymentResult.aid}</span>
              </div>
              
              <div className="flex justify-between items-center py-3">
                <span className="text-gray-400 font-medium">결제 시간</span>
                <span className="text-white font-semibold">
                  {new Date(paymentResult.approved_at).toLocaleString('ko-KR')}
                </span>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-4">
            <button
              onClick={handleGoHome}
              className="flex-1 px-8 py-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-2xl hover:from-blue-600 hover:to-purple-700 transition-all duration-300 shadow-lg backdrop-blur-xl border border-blue-500/20 hover:shadow-blue-500/25 hover:shadow-xl"
            >
              <span className="flex items-center justify-center space-x-2">
                <span>🏠</span>
                <span>홈으로 돌아가기</span>
              </span>
            </button>
            
            <button
              onClick={() => window.print()}
              className="flex-1 px-8 py-4 bg-gradient-to-r from-gray-600 to-gray-700 text-white font-semibold rounded-2xl hover:from-gray-700 hover:to-gray-800 transition-all duration-300 shadow-lg backdrop-blur-xl border border-gray-500/20"
            >
              <span className="flex items-center justify-center space-x-2">
                <span>🖨️</span>
                <span>영수증 출력</span>
              </span>
            </button>
          </div>
        </div>
      </div>

      <style jsx>{`
        @keyframes blob {
          0% { transform: translate(0px, 0px) scale(1); }
          33% { transform: translate(30px, -50px) scale(1.1); }
          66% { transform: translate(-20px, 20px) scale(0.9); }
          100% { transform: translate(0px, 0px) scale(1); }
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
      `}</style>
    </div>
  );
}
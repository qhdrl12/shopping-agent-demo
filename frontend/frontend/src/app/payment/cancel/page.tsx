'use client';

import { useRouter } from 'next/navigation';

export default function PaymentCancel() {
  const router = useRouter();

  const handleGoHome = () => {
    router.push('/');
  };

  const handleRetry = () => {
    router.back();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-gray-900 to-slate-800">
      {/* Animated background */}
      <div className="fixed inset-0 overflow-hidden">
        <div className="absolute -inset-10 opacity-50">
          <div className="absolute top-0 -left-4 w-72 h-72 bg-yellow-500 rounded-full mix-blend-multiply filter blur-xl animate-blob opacity-20"></div>
          <div className="absolute top-0 -right-4 w-72 h-72 bg-orange-500 rounded-full mix-blend-multiply filter blur-xl animate-blob animation-delay-2000 opacity-20"></div>
          <div className="absolute -bottom-8 left-20 w-72 h-72 bg-red-500 rounded-full mix-blend-multiply filter blur-xl animate-blob animation-delay-4000 opacity-20"></div>
        </div>
      </div>

      <div className="relative flex items-center justify-center min-h-screen p-6">
        <div className="max-w-md w-full mx-auto">
          {/* Cancel Header */}
          <div className="text-center mb-8">
            <div className="w-20 h-20 bg-yellow-500/20 rounded-full flex items-center justify-center mx-auto mb-6 animate-pulse">
              <svg className="w-10 h-10 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-yellow-400 to-orange-400 bg-clip-text text-transparent mb-4">
              결제 취소
            </h1>
            <p className="text-xl text-gray-300 mb-6">
              사용자에 의해 결제가 취소되었습니다.
            </p>
          </div>

          {/* Cancel Message */}
          <div className="bg-gradient-to-br from-yellow-900/20 to-orange-900/20 backdrop-blur-xl border border-yellow-600/30 rounded-3xl p-8 shadow-2xl mb-8">
            <div className="text-center">
              <h2 className="text-xl font-bold text-yellow-400 mb-4">결제를 취소하셨습니다</h2>
              <div className="space-y-3 text-gray-300">
                <p>결제 과정에서 취소 버튼을 누르셨거나</p>
                <p>브라우저를 닫으셔서 결제가 중단되었습니다.</p>
                <p className="text-sm text-gray-400 mt-4">
                  언제든지 다시 결제를 진행하실 수 있습니다.
                </p>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="space-y-4">
            <button
              onClick={handleRetry}
              className="w-full px-8 py-4 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-2xl hover:from-blue-600 hover:to-purple-700 transition-all duration-300 shadow-lg backdrop-blur-xl border border-blue-500/20 hover:shadow-blue-500/25 hover:shadow-xl"
            >
              <span className="flex items-center justify-center space-x-2">
                <span>🔄</span>
                <span>다시 결제하기</span>
              </span>
            </button>
            
            <button
              onClick={handleGoHome}
              className="w-full px-8 py-4 bg-gradient-to-r from-gray-600 to-gray-700 text-white font-semibold rounded-2xl hover:from-gray-700 hover:to-gray-800 transition-all duration-300 shadow-lg backdrop-blur-xl border border-gray-500/20"
            >
              <span className="flex items-center justify-center space-x-2">
                <span>🏠</span>
                <span>홈으로 돌아가기</span>
              </span>
            </button>
          </div>

          {/* Info Section */}
          <div className="mt-8 bg-gray-800/30 backdrop-blur-sm border border-gray-700/30 rounded-xl p-4">
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0">
                <svg className="w-5 h-5 text-blue-400 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <div className="text-sm text-gray-300">
                <p className="font-medium text-blue-400 mb-1">안내사항</p>
                <p>결제 취소로 인해 어떠한 금액도 청구되지 않았습니다. 안심하고 다시 이용해 주세요.</p>
              </div>
            </div>
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
'use client';

import { useRouter } from 'next/navigation';

export default function PaymentFail() {
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
          <div className="absolute top-0 -left-4 w-72 h-72 bg-red-500 rounded-full mix-blend-multiply filter blur-xl animate-blob opacity-20"></div>
          <div className="absolute top-0 -right-4 w-72 h-72 bg-orange-500 rounded-full mix-blend-multiply filter blur-xl animate-blob animation-delay-2000 opacity-20"></div>
          <div className="absolute -bottom-8 left-20 w-72 h-72 bg-pink-500 rounded-full mix-blend-multiply filter blur-xl animate-blob animation-delay-4000 opacity-20"></div>
        </div>
      </div>

      <div className="relative flex items-center justify-center min-h-screen p-6">
        <div className="max-w-md w-full mx-auto">
          {/* Fail Header */}
          <div className="text-center mb-8">
            <div className="w-20 h-20 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-6 animate-pulse">
              <svg className="w-10 h-10 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h1 className="text-4xl font-bold bg-gradient-to-r from-red-400 to-orange-400 bg-clip-text text-transparent mb-4">
              결제 실패
            </h1>
            <p className="text-xl text-gray-300 mb-6">
              결제 처리 중 문제가 발생했습니다.
            </p>
          </div>

          {/* Fail Message */}
          <div className="bg-gradient-to-br from-red-900/20 to-orange-900/20 backdrop-blur-xl border border-red-600/30 rounded-3xl p-8 shadow-2xl mb-8">
            <div className="text-center">
              <h2 className="text-xl font-bold text-red-400 mb-4">결제가 취소되었습니다</h2>
              <div className="space-y-3 text-gray-300">
                <p>• 결제 중 사용자가 취소했거나</p>
                <p>• 카드 정보가 올바르지 않거나</p>
                <p>• 한도 초과 등의 이유로 결제가 실패했습니다</p>
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
                <span>다시 시도하기</span>
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

          {/* Help Section */}
          <div className="mt-8 text-center">
            <p className="text-sm text-gray-400 mb-2">도움이 필요하신가요?</p>
            <div className="flex justify-center space-x-4 text-xs">
              <span className="text-blue-400 hover:text-blue-300 cursor-pointer">고객센터</span>
              <span className="text-gray-500">|</span>
              <span className="text-blue-400 hover:text-blue-300 cursor-pointer">FAQ</span>
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
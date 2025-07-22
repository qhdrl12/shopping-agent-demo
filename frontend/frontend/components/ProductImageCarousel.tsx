import React, { useState, useEffect } from 'react';

interface ProductImageCarouselProps {
  images: string[];
  alt: string;
}

export const ProductImageCarousel: React.FC<ProductImageCarouselProps> = ({ images, alt }) => {
  const [currentIndex, setCurrentIndex] = useState(0);

  // 단일 이미지인 경우 일반 이미지로 표시
  if (!images || images.length === 0) {
    return null;
  }

  if (images.length === 1) {
    return (
      <div className="relative w-full max-w-md mx-auto my-4">
        <img
          src={images[0]}
          alt={alt}
          className="w-full h-64 object-cover rounded-xl shadow-lg"
        />
      </div>
    );
  }

  const goToPrevious = () => {
    setCurrentIndex((prevIndex) => 
      prevIndex === 0 ? images.length - 1 : prevIndex - 1
    );
  };

  const goToNext = () => {
    setCurrentIndex((prevIndex) => 
      prevIndex === images.length - 1 ? 0 : prevIndex + 1
    );
  };

  return (
    <div className="relative w-full max-w-md mx-auto my-4">
      {/* 메인 캐러셀 컨테이너 */}
      <div className="relative overflow-hidden rounded-xl shadow-lg bg-gray-800">
        <div 
          className="flex transition-transform duration-300 ease-in-out"
          style={{ transform: `translateX(-${currentIndex * 100}%)` }}
        >
          {images.map((image, index) => (
            <div key={index} className="w-full flex-shrink-0 relative">
              <img
                src={image}
                alt={`${alt} ${index + 1}`}
                className="w-full h-64 object-cover"
              />
              
              {/* 이전/다음 이미지 미리보기 오버레이 */}
              {index === currentIndex && (
                <>
                  {/* 이전 이미지 미리보기 (왼쪽) */}
                  {currentIndex > 0 && (
                    <div className="absolute left-0 top-0 w-12 h-full bg-gradient-to-r from-black/30 to-transparent flex items-center">
                      <div className="w-8 h-16 ml-1 rounded overflow-hidden opacity-60">
                        <img
                          src={images[currentIndex - 1]}
                          alt="Previous"
                          className="w-full h-full object-cover"
                        />
                      </div>
                    </div>
                  )}
                  
                  {/* 다음 이미지 미리보기 (오른쪽) */}
                  {currentIndex < images.length - 1 && (
                    <div className="absolute right-0 top-0 w-12 h-full bg-gradient-to-l from-black/30 to-transparent flex items-center justify-end">
                      <div className="w-8 h-16 mr-1 rounded overflow-hidden opacity-60">
                        <img
                          src={images[currentIndex + 1]}
                          alt="Next"
                          className="w-full h-full object-cover"
                        />
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          ))}
        </div>
        
        {/* 이전/다음 버튼 */}
        <button
          onClick={goToPrevious}
          className="absolute left-2 top-1/2 -translate-y-1/2 bg-black/50 hover:bg-black/70 text-white rounded-full p-2 transition-all duration-200 backdrop-blur-sm flex items-center justify-center"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        
        <button
          onClick={goToNext}
          className="absolute right-2 top-1/2 -translate-y-1/2 bg-black/50 hover:bg-black/70 text-white rounded-full p-2 transition-all duration-200 backdrop-blur-sm flex items-center justify-center"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>
      </div>
      
      {/* 인디케이터 dots */}
      <div className="flex justify-center mt-3 space-x-2">
        {images.map((_, index) => (
          <button
            key={index}
            onClick={() => setCurrentIndex(index)}
            className={`w-2 h-2 rounded-full transition-all duration-200 ${
              index === currentIndex
                ? 'bg-blue-500 w-6'
                : 'bg-gray-400 hover:bg-gray-300'
            }`}
          />
        ))}
      </div>
      
      {/* 이미지 카운터 */}
      <div className="text-center mt-2 text-sm text-gray-400">
        {currentIndex + 1} / {images.length}
      </div>
    </div>
  );
};

export default ProductImageCarousel;
import React from 'react';
import ProductImageCarousel from './ProductImageCarousel';

interface ProductInfo {
  name: string;
  brand: string;
  price: number;
  originalPrice?: number;
  discountInfo?: string;
  rewardPoints?: number;
  shippingInfo?: string;
  sizeInfo?: string;
  stockStatus?: string;
  colors?: string[];
  images: string[];
  url: string;
  ranking: '1' | '2' | '3';
  recommendation: string;
  advantages: string[];
}

interface ProductCardProps {
  product: ProductInfo;
}

const ProductCard: React.FC<ProductCardProps> = ({ product }) => {
  const rankingConfig = {
    '1': { icon: '👑', color: 'from-yellow-400 to-yellow-600', label: 'BEST' },
    '2': { icon: '🥈', color: 'from-gray-300 to-gray-500', label: '추천' },
    '3': { icon: '🥉', color: 'from-amber-600 to-amber-800', label: '대안' }
  };

  const config = rankingConfig[product.ranking];
  const discount = product.originalPrice && product.price 
    ? Math.round(((product.originalPrice - product.price) / product.originalPrice) * 100)
    : null;

  return (
    <div className="relative group mb-8">
      {/* Glassmorphism Container */}
      <div className="relative bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-xl border border-white/20 rounded-3xl p-6 shadow-2xl hover:shadow-3xl transition-all duration-500 hover:scale-[1.02] hover:border-white/30">
        
        {/* Ranking Badge */}
        <div className="absolute -top-3 -right-3 z-10">
          <div className={`bg-gradient-to-r ${config.color} px-4 py-2 rounded-full shadow-lg border border-white/20 backdrop-blur-sm`}>
            <div className="flex items-center space-x-2">
              <span className="text-sm">{config.icon}</span>
              <span className="text-white font-bold text-xs tracking-wider">{config.label}</span>
            </div>
          </div>
        </div>

        {/* Product Header */}
        <div className="mb-4">
          <div className="flex items-start justify-between mb-2">
            <div>
              <h3 className="text-xl font-bold text-white mb-1 group-hover:text-yellow-300 transition-colors duration-300">
                {product.name}
              </h3>
              <p className="text-gray-300 text-sm font-medium">{product.brand}</p>
            </div>
          </div>
          <p className="text-gray-400 text-sm italic leading-relaxed">
            {product.recommendation}
          </p>
        </div>

        {/* Product Image Carousel */}
        <div className="mb-6">
          <ProductImageCarousel images={product.images} alt={product.name} />
        </div>

        {/* Price Section */}
        <div className="bg-gradient-to-r from-gray-800/40 to-gray-700/40 rounded-2xl p-4 mb-4 border border-gray-600/30">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-3">
              <span className="text-2xl font-bold text-white">
                {product.price.toLocaleString()}원
              </span>
              {product.originalPrice && (
                <span className="text-gray-400 line-through text-sm">
                  {product.originalPrice.toLocaleString()}원
                </span>
              )}
              {discount && (
                <span className="bg-red-500/20 text-red-300 px-2 py-1 rounded-full text-xs font-bold border border-red-500/30">
                  -{discount}%
                </span>
              )}
            </div>
          </div>
          
          <div className="grid grid-cols-2 gap-3 text-xs">
            {product.rewardPoints && (
              <div className="flex items-center space-x-2">
                <span className="text-yellow-400">💰</span>
                <span className="text-gray-300">적립 <span className="text-yellow-300 font-semibold">{product.rewardPoints}P</span></span>
              </div>
            )}
            {product.shippingInfo && (
              <div className="flex items-center space-x-2">
                <span className="text-blue-400">🚚</span>
                <span className="text-gray-300">{product.shippingInfo}</span>
              </div>
            )}
          </div>
        </div>

        {/* Product Details */}
        <div className="grid grid-cols-2 gap-3 mb-4 text-xs">
          {product.sizeInfo && (
            <div className="bg-gray-800/30 rounded-xl p-3 border border-gray-600/20">
              <div className="flex items-center space-x-2 mb-1">
                <span className="text-purple-400">📏</span>
                <span className="text-gray-400 font-medium">사이즈</span>
              </div>
              <span className="text-gray-200">{product.sizeInfo}</span>
            </div>
          )}
          
          {product.stockStatus && (
            <div className="bg-gray-800/30 rounded-xl p-3 border border-gray-600/20">
              <div className="flex items-center space-x-2 mb-1">
                <span className="text-green-400">📦</span>
                <span className="text-gray-400 font-medium">재고</span>
              </div>
              <span className="text-gray-200">{product.stockStatus}</span>
            </div>
          )}
        </div>

        {/* Colors */}
        {product.colors && product.colors.length > 0 && (
          <div className="mb-4">
            <div className="flex items-center space-x-2 mb-2">
              <span className="text-pink-400">🎨</span>
              <span className="text-gray-400 text-xs font-medium">컬러</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {product.colors.slice(0, 4).map((color, index) => (
                <span key={index} className="bg-gray-700/50 text-gray-300 px-2 py-1 rounded-lg text-xs border border-gray-600/30">
                  {color}
                </span>
              ))}
              {product.colors.length > 4 && (
                <span className="text-gray-400 text-xs">+{product.colors.length - 4}개</span>
              )}
            </div>
          </div>
        )}

        {/* Advantages */}
        {product.advantages && product.advantages.length > 0 && (
          <div className="mb-6">
            <div className="flex items-center space-x-2 mb-3">
              <span className="text-yellow-400">✨</span>
              <span className="text-gray-300 text-sm font-medium">추천 포인트</span>
            </div>
            <div className="space-y-2">
              {product.advantages.slice(0, 3).map((advantage, index) => (
                <div key={index} className="flex items-start space-x-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-yellow-400 mt-2 flex-shrink-0"></div>
                  <span className="text-gray-300 text-sm leading-relaxed">{advantage}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Button */}
        <button
          onClick={() => window.open(product.url, '_blank')}
          className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white font-bold py-4 rounded-2xl transition-all duration-300 transform hover:scale-[1.02] hover:shadow-2xl border border-blue-500/30 backdrop-blur-sm"
        >
          <div className="flex items-center justify-center space-x-2">
            <span>구매하러 가기</span>
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
            </svg>
          </div>
        </button>

        {/* Glow Effect */}
        <div className="absolute inset-0 rounded-3xl bg-gradient-to-r from-blue-600/10 to-purple-600/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"></div>
      </div>
      
      {/* Shadow Effect */}
      <div className="absolute inset-0 rounded-3xl bg-gradient-to-r from-blue-600/20 to-purple-600/20 blur-xl scale-95 opacity-0 group-hover:opacity-50 transition-all duration-500 -z-10"></div>
    </div>
  );
};

export default ProductCard;
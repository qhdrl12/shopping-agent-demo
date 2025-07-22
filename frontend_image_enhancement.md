# 프론트엔드 이미지 개선 가이드

## 🎯 목표
- 고정 사이즈 이미지 표시
- 여러 이미지가 있을 때 슬라이더/캐러셀 기능
- 깔끔한 UI/UX

## 🔧 구현 방법

### 1. 필요한 라이브러리 설치

```bash
cd frontend/frontend
npm install swiper react-image-gallery
# 또는
npm install embla-carousel-react
```

### 2. 커스텀 이미지 컴포넌트 생성

#### `components/ProductImageCarousel.tsx`
```typescript
import React, { useState } from 'react';
import { Swiper, SwiperSlide } from 'swiper/react';
import { Navigation, Pagination, Thumbs } from 'swiper/modules';
import 'swiper/css';
import 'swiper/css/navigation';
import 'swiper/css/pagination';
import 'swiper/css/thumbs';

interface ProductImageCarouselProps {
  images: string[];
  alt: string;
}

export const ProductImageCarousel: React.FC<ProductImageCarouselProps> = ({ images, alt }) => {
  const [thumbsSwiper, setThumbsSwiper] = useState(null);

  if (images.length === 1) {
    return (
      <div className="w-full max-w-md mx-auto">
        <img
          src={images[0]}
          alt={alt}
          className="w-full h-64 object-cover rounded-lg"
        />
      </div>
    );
  }

  return (
    <div className="w-full max-w-md mx-auto">
      {/* 메인 이미지 슬라이더 */}
      <Swiper
        spaceBetween={10}
        navigation={true}
        pagination={{ clickable: true }}
        thumbs={{ swiper: thumbsSwiper }}
        modules={[Navigation, Pagination, Thumbs]}
        className="mb-4"
      >
        {images.map((image, index) => (
          <SwiperSlide key={index}>
            <img
              src={image}
              alt={`${alt} ${index + 1}`}
              className="w-full h-64 object-cover rounded-lg"
            />
          </SwiperSlide>
        ))}
      </Swiper>

      {/* 썸네일 슬라이더 */}
      {images.length > 1 && (
        <Swiper
          onSwiper={setThumbsSwiper}
          spaceBetween={10}
          slidesPerView={4}
          freeMode={true}
          watchSlidesProgress={true}
          modules={[Navigation, Thumbs]}
          className="thumbs-swiper"
        >
          {images.map((image, index) => (
            <SwiperSlide key={index}>
              <img
                src={image}
                alt={`${alt} thumbnail ${index + 1}`}
                className="w-full h-16 object-cover rounded cursor-pointer opacity-60 hover:opacity-100 transition-opacity"
              />
            </SwiperSlide>
          ))}
        </Swiper>
      )}
    </div>
  );
};
```

### 3. ReactMarkdown 커스텀 컴포넌트 수정

#### `components/Chat.tsx` 수정
```typescript
import { ProductImageCarousel } from './ProductImageCarousel';

// 연속된 이미지를 감지하고 그룹화하는 함수
const groupConsecutiveImages = (content: string) => {
  const imageRegex = /!\[([^\]]*)\]\(([^)]+)\)/g;
  // 연속된 이미지를 찾아 그룹화하는 로직
  // 이 부분은 복잡하므로 더 간단한 방법을 사용할 수 있습니다.
};

// ReactMarkdown 컴포넌트에서 이미지 처리
const components = {
  img: ({ node, src, alt, ...props }) => {
    // 여기서 연속된 이미지를 처리하거나
    // 각 이미지를 고정 사이즈로 표시
    return (
      <img
        src={src}
        alt={alt}
        className="w-full max-w-md h-64 object-cover rounded-lg mx-auto my-4"
        {...props}
      />
    );
  }
};

// 메시지 렌더링 부분
{message.type === 'ai' ? (
  <div className="prose prose-invert prose-sm max-w-none">
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeHighlight]}
      components={components}
    >
      {message.content}
    </ReactMarkdown>
  </div>
) : (
  // ...
)}
```

### 4. 더 간단한 구현 방법 (권장)

#### CSS 기반 이미지 고정 사이즈
```css
/* globals.css 또는 컴포넌트 CSS */
.prose img {
  width: 100%;
  max-width: 400px;
  height: 240px;
  object-fit: cover;
  border-radius: 0.5rem;
  margin: 1rem auto;
}
```

#### 이미지 그룹 감지 및 슬라이더 (고급)
```typescript
// 백엔드에서 여러 이미지를 연속으로 보내는 경우를 감지
const processMarkdownWithImageGroups = (content: string) => {
  // ![image1](url1)\n![image2](url2)\n![image3](url3) 패턴을 찾아
  // <ProductImageCarousel images={[url1, url2, url3]} /> 로 변환
  const imageGroupRegex = /(?:!\[[^\]]*\]\([^)]+\)\s*){2,}/g;
  
  return content.replace(imageGroupRegex, (match) => {
    const urls = match.match(/!\[[^\]]*\]\(([^)]+)\)/g)
      ?.map(img => img.match(/\(([^)]+)\)/)?.[1])
      .filter(Boolean) || [];
    
    if (urls.length > 1) {
      return `<ProductImageCarousel images={${JSON.stringify(urls)}} />`;
    }
    return match;
  });
};
```

## 🎨 스타일링 개선안

### Tailwind CSS 클래스
```typescript
// 이미지 컨테이너
const imageContainerClass = "w-full max-w-sm mx-auto my-6";

// 단일 이미지
const singleImageClass = "w-full h-60 object-cover rounded-xl shadow-lg";

// 슬라이더 내 이미지
const carouselImageClass = "w-full h-60 object-cover rounded-xl";

// 썸네일 이미지  
const thumbnailClass = "w-full h-16 object-cover rounded-lg cursor-pointer opacity-70 hover:opacity-100 transition-all duration-300";
```

## 🚀 단계별 구현 계획

### Phase 1: 기본 고정 사이즈 (즉시 적용 가능)
```css
/* 가장 간단한 방법 - globals.css에 추가 */
.prose img {
  width: 100% !important;
  max-width: 400px !important;
  height: 240px !important;
  object-fit: cover !important;
  border-radius: 12px !important;
  margin: 1.5rem auto !important;
  display: block !important;
}
```

### Phase 2: 슬라이더 기능 추가
- Swiper.js 또는 Embla Carousel 설치
- 커스텀 이미지 컴포넌트 생성
- ReactMarkdown components prop에 등록

### Phase 3: 고급 기능
- 이미지 lazy loading
- 라이트박스/모달 기능
- 이미지 줌 기능
- 로딩 상태 표시

## 🎯 추천 방식

**가장 빠른 구현**: Phase 1의 CSS 방식
**최적의 UX**: Phase 2의 슬라이더 방식

백엔드에서 이미 여러 이미지를 연속으로 마크다운에 포함시키도록 설정했으므로, 프론트엔드에서 이를 감지하여 슬라이더로 변환하는 로직을 추가하면 됩니다.
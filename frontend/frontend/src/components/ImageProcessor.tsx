import React from 'react';
import ProductImageCarousel from '../../components/ProductImageCarousel';

interface ImageGroup {
  type: 'image-group';
  images: string[];
  alt: string;
}

interface TextContent {
  type: 'text';
  content: string;
}

type ProcessedContent = ImageGroup | TextContent;

// 메시지 내용을 분석하여 연속된 이미지들을 그룹화
export const processMessageContent = (content: string): ProcessedContent[] => {
  const lines = content.split('\n');
  const processed: ProcessedContent[] = [];
  let currentImageGroup: string[] = [];
  let currentTextLines: string[] = [];
  
  const flushTextLines = () => {
    if (currentTextLines.length > 0) {
      processed.push({
        type: 'text',
        content: currentTextLines.join('\n')
      });
      currentTextLines = [];
    }
  };
  
  const flushImageGroup = () => {
    if (currentImageGroup.length > 0) {
      processed.push({
        type: 'image-group',
        images: currentImageGroup,
        alt: 'Product images'
      });
      currentImageGroup = [];
    }
  };
  
  for (const line of lines) {
    const imageMatch = line.match(/^!\[([^\]]*)\]\(([^)]+)\)$/);
    
    if (imageMatch) {
      // 이미지 라인 발견
      flushTextLines();
      currentImageGroup.push(imageMatch[2]); // URL 추출
    } else {
      // 텍스트 라인
      flushImageGroup();
      currentTextLines.push(line);
    }
  }
  
  // 마지막 그룹들 처리
  flushTextLines();
  flushImageGroup();
  
  return processed;
};

// 처리된 콘텐츠를 렌더링하는 컴포넌트
export const ProcessedContentRenderer: React.FC<{ content: string }> = ({ content }) => {
  const processedContent = processMessageContent(content);
  
  return (
    <div>
      {processedContent.map((item, index) => {
        if (item.type === 'image-group') {
          return (
            <ProductImageCarousel
              key={`image-group-${index}`}
              images={item.images}
              alt={item.alt}
            />
          );
        } else {
          return (
            <div 
              key={`text-${index}`}
              dangerouslySetInnerHTML={{ __html: item.content }}
            />
          );
        }
      })}
    </div>
  );
};
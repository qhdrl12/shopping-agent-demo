"""
Question generation nodes for follow-up suggestions
"""

import json
from typing import List
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage

from ..utils.model import load_chat_model
from ..prompts.system_prompts import SUGGESTED_QUESTIONS_PROMPT


class QuestionNodes:
    """Nodes for generating suggested follow-up questions"""
    
    def __init__(self, model_name: str = "openai/gpt-4.1"):
        """
        질문 생성 노드 초기화
        
        Args:
            model_name: 사용할 LLM 모델명 (기본: gpt-4.1)
        """
        self.llm = load_chat_model(model_name)
    
    def generate_suggested_questions(self, state) -> dict:
        """
        사용자의 쿼리와 추천된 상품을 바탕으로 관련도 높은 후속 질문 생성
        
        Args:
            state: 워크플로우 상태 (메시지, 상품 데이터, 최종 응답 포함)
            
        Returns:
            dict: 생성된 질문 리스트와 업데이트된 상태
        """
        
        print("Generating suggested follow-up questions...")
        
        try:
            # Extract user's original query
            user_query = ""
            if state.get("messages"):
                # Get the most recent human message
                for message in reversed(state["messages"]):
                    if hasattr(message, 'type') and message.type == 'human':
                        user_query = message.content
                        break
            
            # Prepare context for question generation
            context_data = {
                "user_query": user_query,
                "has_products": bool(state.get("product_data")),
                "product_count": len(state.get("product_data", [])),
                "final_response": state.get("final_response", ""),
                "products_summary": self._extract_products_summary(state.get("product_data", []))
            }
            
            # Create prompt for question generation
            question_prompt = ChatPromptTemplate.from_messages([
                ("system", SUGGESTED_QUESTIONS_PROMPT),
                ("human", """
사용자 원본 질문: {user_query}

추천된 상품 정보:
{products_summary}

최종 응답 길이: {response_length}자

위 정보를 바탕으로 사용자가 궁금해할 만한 자연스러운 후속 질문 3-4개를 생성해주세요.
사용자의 쇼핑 여정을 이어갈 수 있도록 상품 상세정보, 스타일링, 대안 상품, 실용적 질문 등 다양한 관점에서 제안해주세요.
                """)
            ])
            
            formatted_prompt = question_prompt.format_messages(
                user_query=context_data["user_query"],
                products_summary=context_data["products_summary"],
                response_length=len(context_data["final_response"])
            )
            
            # Generate questions
            result = self.llm.invoke(formatted_prompt)
            
            # Parse the JSON response
            try:
                # Clean the response content to handle code blocks
                content = result.content.strip()
                
                # Remove markdown code block markers if present
                if content.startswith('```json'):
                    content = content[7:]  # Remove ```json
                if content.startswith('```'):
                    content = content[3:]   # Remove ```
                if content.endswith('```'):
                    content = content[:-3]  # Remove trailing ```
                
                # Clean up any extra whitespace
                content = content.strip()
                
                questions = json.loads(content)
                if not isinstance(questions, list):
                    raise ValueError("Response is not a list")
                
                # Validate questions
                valid_questions = [q for q in questions if isinstance(q, str) and len(q.strip()) > 0]
                
                if len(valid_questions) < 2:
                    # Fallback to default questions if generation fails
                    valid_questions = self._generate_fallback_questions(context_data)
                
                print(f"Generated {len(valid_questions)} suggested questions")
                
                return {
                    "suggested_questions": valid_questions[:4],  # Limit to 4 questions
                    "current_step": "questions_generated"
                }
                
            except (json.JSONDecodeError, ValueError) as parse_error:
                print(f"Failed to parse generated questions, trying manual extraction")
                
                # Try to extract questions manually from the response
                manual_questions = self._extract_questions_manually(result.content)
                if manual_questions and len(manual_questions) >= 2:
                    return {
                        "suggested_questions": manual_questions[:4],
                        "current_step": "questions_generated"
                    }
                
                # Fallback to default questions
                fallback_questions = self._generate_fallback_questions(context_data)
                return {
                    "suggested_questions": fallback_questions,
                    "current_step": "questions_generated"
                }
                
        except Exception as e:
            print(f"Question generation failed: {e}, using fallback questions")
            
            # Fallback to safe default questions
            fallback_questions = [
                "다른 색상이나 사이즈도 있어?",
                "비슷한 스타일의 다른 제품도 찾아줘",
                "이 제품들 중에서 가성비 최고는 뭐야?",
                "코디 방법도 알려줄 수 있어?"
            ]
            
            return {
                "suggested_questions": fallback_questions,
                "current_step": "questions_generated"
            }
    
    def _extract_products_summary(self, products: List[dict]) -> str:
        """
        상품 데이터에서 질문 생성에 필요한 요약 정보 추출
        
        Args:
            products: 상품 데이터 리스트
            
        Returns:
            str: 상품 요약 정보
        """
        if not products:
            return "추천된 상품이 없습니다."
        
        summary_parts = []
        for i, product in enumerate(products[:3], 1):  # Top 3 products only
            product_info = f"{i}. {product.get('name', '상품명 없음')}"
            
            if product.get('brand'):
                product_info += f" ({product['brand']})"
            
            if product.get('price'):
                product_info += f" - {product['price']}"
            
            summary_parts.append(product_info)
        
        return "\n".join(summary_parts)
    
    def _generate_fallback_questions(self, context_data: dict) -> List[str]:
        """
        기본 후속 질문 생성 (AI 생성 실패 시 사용)
        
        Args:
            context_data: 컨텍스트 정보
            
        Returns:
            List[str]: 기본 질문 리스트
        """
        user_query = context_data.get("user_query", "").lower()
        has_products = context_data.get("has_products", False)
        
        if not has_products:
            return self._get_no_product_questions()
        
        return self._get_product_questions(user_query)
    
    def _get_no_product_questions(self) -> List[str]:
        """상품이 없을 때의 기본 질문"""
        return [
            "다른 키워드로 검색해볼까?",
            "비슷한 스타일의 제품 찾아줘",
            "가격대를 바꿔서 다시 찾아볼까?",
            "다른 브랜드는 어때?"
        ]
    
    def _get_product_questions(self, user_query: str) -> List[str]:
        """상품이 있을 때의 맞춤형 질문"""
        questions = []
        
        # 색상 관련 질문
        questions.append(
            "이 제품 다른 색상도 보여줘" if any(word in user_query for word in ["색상", "컬러"]) 
            else "다른 색상이나 사이즈 옵션 있어?"
        )
        
        # 스타일링 관련 질문
        questions.append(
            "완성된 전체 코디 보여줘" if any(word in user_query for word in ["코디", "매치", "스타일링"]) 
            else "이 제품과 어울리는 다른 아이템 추천해줘"
        )
        
        # 가격대 관련 질문
        if any(word in user_query for word in ["저렴", "가성비"]):
            questions.append("더 고급 브랜드 제품도 볼까?")
        elif any(word in user_query for word in ["고급", "명품"]):
            questions.append("더 합리적인 가격대 제품은 어때?")
        else:
            questions.append("가격대별 다른 옵션도 보여줘")
        
        # 비교 질문
        questions.append("이 제품들의 장단점 비교해줘")
        
        return questions[:4]
    
    def _extract_questions_manually(self, content: str) -> List[str]:
        """
        수동으로 응답에서 질문 추출 (JSON 파싱 실패 시 사용)
        
        Args:
            content: AI 응답 원본 텍스트
            
        Returns:
            List[str]: 추출된 질문 리스트
        """
        questions = []
        
        try:
            # 여러 패턴으로 질문 추출 시도
            import re
            
            # 패턴 1: JSON 배열에서 문자열 추출
            json_pattern = r'"([^"]+\?)"'
            matches = re.findall(json_pattern, content)
            if matches:
                questions.extend(matches)
            
            # 패턴 2: 줄 단위로 물음표로 끝나는 문장 찾기
            if not questions:
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    # 따옴표 제거
                    line = line.strip('"').strip("'").strip(',')
                    if line.endswith('?') and len(line) > 10:  # 최소 길이 확인
                        questions.append(line)
            
            # 패턴 3: 리스트 마커가 있는 질문들
            if not questions:
                list_pattern = r'[\d\-\*]\s*["\']?([^"\']+\?)["\']?'
                matches = re.findall(list_pattern, content)
                if matches:
                    questions.extend(matches)
                    
            # 중복 제거 및 정리
            seen = set()
            clean_questions = []
            for q in questions:
                q = q.strip()
                if q and q not in seen and len(q) > 5:
                    seen.add(q)
                    clean_questions.append(q)
            
            return clean_questions[:4]  # 최대 4개
            
        except Exception as e:
            print(f"Manual extraction failed: {e}")
            return []
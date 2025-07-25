"""
Kakao Pay Service

카카오페이 결제 API를 처리하는 서비스 클래스
- 결제 준비 (Payment Ready)
- 결제 승인 (Payment Approve)
- 결제 취소 (Payment Cancel)
"""

import os
import uuid
import httpx
from typing import Dict, Optional
from datetime import datetime
from dotenv import load_dotenv

from ..models.schemas import (
    PaymentReadyRequest,
    PaymentReadyResponse,  
    PaymentApproveRequest,
    PaymentApproveResponse,
    PaymentErrorResponse
)

# Load environment variables
load_dotenv()


class KakaoPayService:
    """카카오페이 결제 처리 서비스"""
    
    def __init__(self):
        self.cid = os.getenv("KAKAO_PAY_CID")
        self.secret_key = os.getenv("KAKAO_PAY_SECRET_KEY")
        
        if not self.cid or not self.secret_key:
            raise ValueError("KAKAO_PAY_CID and KAKAO_PAY_SECRET_KEY must be set in environment variables")
        
        self.base_url = "https://open-api.kakaopay.com"
        
        self.headers = {
            "Authorization": f"SECRET_KEY {self.secret_key}",
            "Content-Type": "application/json"
        }
        
        # 개발용 간단한 세션 저장소 (결제 승인에 필요한 최소 데이터만)
        # 카카오페이 승인 시 partner_order_id, partner_user_id가 필수
        self.payment_sessions: Dict[str, Dict[str, str]] = {}
    
    async def prepare_payment(self, payment_request: PaymentReadyRequest) -> PaymentReadyResponse:
        """
        카카오페이 결제 준비 API 호출
        
        Args:
            payment_request: 결제 준비 요청 데이터
            
        Returns:
            PaymentReadyResponse: 결제 준비 응답 데이터
            
        Raises:
            PaymentErrorResponse: 결제 준비 실패 시
        """
        try:
            # 고유 주문번호 및 사용자ID 생성
            # Format: ORDER_[8자리UUID]_[Unix타임스탬프] 
            partner_order_id = f"ORDER_{uuid.uuid4().hex[:8]}_{int(datetime.now().timestamp())}"
            partner_user_id = f"USER_{uuid.uuid4().hex[:8]}"
            
            # VAT 자동 계산 (부가세 10%)
            # 한국 부가세법: 부가세 = 공급가액 × 10% = 총금액 ÷ 11
            vat_amount = payment_request.vat_amount
            if vat_amount is None:
                vat_amount = int(payment_request.total_amount / 11)
            
            # 카카오페이 결제 준비 요청 데이터
            prepare_data = {
                "cid": self.cid,
                "partner_order_id": partner_order_id,
                "partner_user_id": partner_user_id,
                "item_name": payment_request.product_name,
                "quantity": payment_request.quantity,
                "total_amount": payment_request.total_amount,
                "vat_amount": vat_amount,
                "tax_free_amount": payment_request.tax_free_amount,
                # 결제 완료 후 리다이렉트 URL들
                # TODO: 환경변수로 분리하여 개발/운영 환경별 관리 필요
                "approval_url": f"http://localhost:3000/payment/success",  
                "fail_url": f"http://localhost:3000/payment/fail",        
                "cancel_url": f"http://localhost:3000/payment/cancel"
            }
            
            # 개발환경에서만 로깅 (운영환경에서는 로거 사용 권장)
            print(f"[DEBUG] Preparing payment with data: {prepare_data}")
            
            # 카카오페이 결제준비 API 호출
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/online/v1/payment/ready",
                    headers=self.headers,
                    json=prepare_data,
                    timeout=30.0  # 타임아웃 30초
                )
                
                print(f"[DEBUG] Kakao Pay API response status: {response.status_code}")
                print(f"[DEBUG] Kakao Pay API response: {response.text}")
                
                # HTTP 상태코드 확인 및 에러 처리
                if response.status_code != 200:
                    try:
                        error_data = response.json() if response.content else {}
                    except ValueError:
                        error_data = {"raw_response": response.text}
                    
                    raise PaymentErrorResponse(
                        error_code=str(response.status_code),
                        error_message=error_data.get("error_message", "Payment preparation failed"),
                        extras=error_data
                    )
                
                response_data = response.json()
                
                # 결제 승인에 필요한 최소 데이터만 저장 (개발용)
                tid = response_data["tid"]
                self.payment_sessions[tid] = {
                    "partner_order_id": partner_order_id,
                    "partner_user_id": partner_user_id
                }
                
                return PaymentReadyResponse(
                    tid=tid,
                    next_redirect_app_url=response_data.get("next_redirect_app_url"),
                    next_redirect_mobile_url=response_data.get("next_redirect_mobile_url"),
                    next_redirect_pc_url=response_data.get("next_redirect_pc_url"),
                    android_app_scheme=response_data.get("android_app_scheme"),
                    ios_app_scheme=response_data.get("ios_app_scheme"),
                    created_at=datetime.now()
                )
                
        except PaymentErrorResponse:
            raise
        except Exception as e:
            print(f"Payment preparation error: {e}")
            raise PaymentErrorResponse(
                error_code="PREPARATION_ERROR",
                error_message=f"Failed to prepare payment: {str(e)}"
            )
    
    async def approve_payment(self, approve_request: PaymentApproveRequest) -> PaymentApproveResponse:
        """
        카카오페이 결제 승인 API 호출
        
        Args:
            approve_request: 결제 승인 요청 데이터
            
        Returns:
            PaymentApproveResponse: 결제 승인 응답 데이터
            
        Raises:
            PaymentErrorResponse: 결제 승인 실패 시
        """
        try:
            # 저장된 결제 세션 정보 조회
            payment_session = self.payment_sessions.get(approve_request.tid)
            if not payment_session:
                raise PaymentErrorResponse(
                    error_code="SESSION_NOT_FOUND",
                    error_message="Payment session not found"
                )
            
            # 카카오페이 결제 승인 요청 데이터
            approve_data = {
                "cid": self.cid,
                "tid": approve_request.tid,
                "partner_order_id": payment_session["partner_order_id"],
                "partner_user_id": payment_session["partner_user_id"],
                "pg_token": approve_request.pg_token
            }
            
            print(f"[DEBUG] Approving payment with data: {approve_data}")
            
            # 카카오페이 결제승인 API 호출
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/online/v1/payment/approve",
                    headers=self.headers,
                    json=approve_data,
                    timeout=30.0  # 타임아웃 30초
                )
                
                print(f"[DEBUG] Kakao Pay approve response status: {response.status_code}")
                print(f"[DEBUG] Kakao Pay approve response: {response.text}")
                
                # HTTP 상태코드 확인 및 에러 처리
                if response.status_code != 200:
                    try:
                        error_data = response.json() if response.content else {}
                    except ValueError:
                        error_data = {"raw_response": response.text}
                    
                    raise PaymentErrorResponse(
                        error_code=str(response.status_code),
                        error_message=error_data.get("error_message", "Payment approval failed"),
                        extras=error_data
                    )
                
                response_data = response.json()
                
                # 개발용: 승인 완료 후 세션 자동 정리
                del self.payment_sessions[approve_request.tid]
                
                return PaymentApproveResponse(
                    aid=response_data["aid"],
                    tid=response_data["tid"],
                    cid=response_data["cid"],
                    sid=response_data.get("sid"),
                    partner_order_id=response_data["partner_order_id"],
                    partner_user_id=response_data["partner_user_id"],
                    payment_method_type=response_data["payment_method_type"],
                    amount=response_data["amount"],
                    item_name=response_data["item_name"],
                    item_code=response_data.get("item_code"),
                    quantity=response_data["quantity"],
                    created_at=datetime.fromisoformat(response_data["created_at"].replace('Z', '+00:00')),
                    approved_at=datetime.fromisoformat(response_data["approved_at"].replace('Z', '+00:00'))
                )
                
        except PaymentErrorResponse:
            raise
        except Exception as e:
            print(f"Payment approval error: {e}")
            raise PaymentErrorResponse(
                error_code="APPROVAL_ERROR",
                error_message=f"Failed to approve payment: {str(e)}"
            )
    
    def get_payment_session(self, tid: str) -> Optional[Dict[str, str]]:
        """개발용: 결제 승인에 필요한 기본 정보만 반환"""
        return self.payment_sessions.get(tid)
    
    def clear_payment_session(self, tid: str) -> bool:
        """개발용: 결제 세션 수동 삭제"""
        if tid in self.payment_sessions:
            del self.payment_sessions[tid]
            return True
        return False


# 전역 서비스 인스턴스 
# 싱글톤 패턴으로 애플리케이션 전체에서 동일한 인스턴스 사용
try:
    kakao_pay_service = KakaoPayService()
except ValueError as e:
    print(f"[ERROR] Failed to initialize KakaoPayService: {e}")
    print("[INFO] Please check KAKAO_PAY_CID and KAKAO_PAY_SECRET_KEY environment variables")
    kakao_pay_service = None
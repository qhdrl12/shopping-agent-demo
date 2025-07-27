"""
Services package for shopping agent backend

This package contains business logic services for the shopping agent:
- kakao_pay_service: Kakao Pay payment processing service

All services are designed to be stateless and thread-safe where possible.
For production deployment, replace in-memory storage with Redis or database.
"""

from .kakao_pay_service import kakao_pay_service, KakaoPayService

__all__ = [
    "kakao_pay_service",
    "KakaoPayService",
]
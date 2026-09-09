# Runbook: 인증 실패 급증 (auth-failure)

## 1. 증상 인식
- 로그인 실패율이 평시(예: 2~3%) 대비 급격히 상승 (예: 20% 이상)
- `auth-service` 로그에 `invalid_token`, `signature_verification_failed`, `429 Too Many Requests` 다발
- 외부 IdP(예: SSO, OAuth provider) 연동 사용 시 콜백 에러 증가

## 2. 1차 진단 (5분 이내)
1. `get_monitoring_status`로 `auth-service` 상태와 활성 alert를 확인한다.
2. 실패 사유 분포를 확인한다 (잘못된 비밀번호 / 토큰 만료 / IdP 응답 오류).
3. 외부 IdP의 status page를 확인한다 (Google / Okta / Azure AD 등).
4. 직전 1시간 내 인증 관련 deploy / 키 로테이션 이력을 점검한다.
5. 의심스러운 IP / User-Agent 패턴이 있는지 — credential stuffing 공격 가능성 검토.

## 3. 2차 조치
- IdP 장애가 원인: status page 안내 후 fallback 로그인 경로 안내.
- 키 로테이션 이슈: JWKS 캐시 강제 갱신 또는 직전 키 임시 허용.
- Brute-force / stuffing 공격 의심: WAF rule 또는 rate limit 강화, 보안팀 호출.
- 내부 버그 의심: rollback 우선.

## 4. 커뮤니케이션
- 보안 인시던트 가능성 있을 경우 **즉시** #security-incident 에 함께 보고.
- 사용자 공지가 필요한 경우 CS팀과 문구 정렬 후 status page 업데이트.

## 5. 에스컬레이션
- 보안팀: security-oncall@example.com
- 인증 시스템 owner: auth-team@example.com

## 6. Post-mortem
- 공격으로 확인된 경우 IOC(Indicator of Compromise)를 보안 인텔리전스에 공유한다.

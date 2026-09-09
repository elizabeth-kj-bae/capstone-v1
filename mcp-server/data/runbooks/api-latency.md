# Runbook: API 지연 (api-latency)

## 1. 증상 인식
- p95 응답 시간이 평소(예: 200ms) 대비 3배 이상으로 상승
- 클라이언트 측 timeout 에러 증가, 5xx 비율 상승
- 모니터링에서 status=degraded, latency alert 발생

## 2. 1차 진단 (5분 이내)
1. `get_monitoring_status`로 대상 서비스의 CPU / Memory / 활성 alert를 확인한다.
2. APM (예: Datadog / Grafana Tempo) 에서 느린 endpoint와 trace를 식별한다.
3. 의존 서비스(DB, 외부 API, 캐시)의 latency 그래프를 함께 비교한다.
   - DB latency가 같이 튀는가? → DB 측 부하 가능성
   - 캐시 hit ratio가 떨어졌는가? → 캐시 invalidation 이슈
4. 최근 30분 이내 deploy / config change 이력을 확인한다.

## 3. 2차 조치
- 특정 endpoint에 국한된 경우: feature flag로 해당 기능을 비활성화.
- 전체 latency 상승: 인스턴스 수평 확장 (auto-scaling 임계치 임시 하향) 검토.
- Connection pool 고갈: 풀 사이즈 임시 증설 후 누수 origin 추적.
- 직전 배포 직후 발생: rollback 우선 수행.

## 4. 커뮤니케이션
- p95 > SLA 임계 5분 이상 지속 시 #incident-ops 보고.
- 사용자 영향이 큰 경우 status page 업데이트.

## 5. 에스컬레이션
- 서비스 owner 팀 oncall
- Infra 팀: infra-oncall@example.com

## 6. Post-mortem
- 지표 기반 트리거 (alert threshold) 적정성을 함께 리뷰한다.

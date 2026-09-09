# Runbook: 데이터베이스 다운 대응 (db-down)

## 1. 증상 인식
- 애플리케이션 로그에 `connection refused`, `timeout`, `could not connect to server` 다발
- 모니터링에서 DB 인스턴스 status=down 또는 health check 연속 실패
- 사용자 영향: 로그인/결제/조회 등 DB 의존 기능 전체 장애

## 2. 1차 진단 (5분 이내)
1. 모니터링 대시보드에서 대상 DB 인스턴스의 CPU / Memory / Disk I/O 그래프를 최근 30분 구간으로 확인한다.
2. `get_monitoring_status` 결과의 `alerts` 필드에서 active alert를 점검한다.
3. 인스턴스가 살아 있다면 SSH 또는 cloud console로 접근하여 `systemctl status postgresql` (또는 해당 엔진) 으로 프로세스 상태를 확인한다.
4. 네트워크 격리 가능성: VPC / Security Group / ACL 변경 이력을 최근 1시간 기준으로 확인한다.

## 3. 2차 조치
- DB 프로세스가 OOM-Kill 된 경우: 메모리 사용량 급증 원인 쿼리 식별 후 재기동.
- Disk full 인 경우: 임시로 로그 회전 / vacuum / 오래된 파티션 detach 후 용량 확보.
- Replication lag 또는 primary 장애 의심 시: standby promote 절차 수행 (DBA 승인 필요).

## 4. 커뮤니케이션
- 발생 5분 이내 #incident-ops 채널에 1차 보고 (영향 범위, 추정 원인).
- 15분 이상 미해결 시 P1으로 격상하고 oncall 매니저 호출.

## 5. 에스컬레이션
- DBA 팀: dba-oncall@example.com
- Infra 팀: infra-oncall@example.com

## 6. Post-mortem
- 복구 후 24시간 이내 timeline 정리 및 RCA 문서 작성.
- 동일 장애 재발 방지 액션 아이템을 Jira에 ticket으로 등록한다.

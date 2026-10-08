# 사고속보 커버리지 리포트

> 이 파일은 `scripts/build_coverage_report.py`가 생성합니다. 직접 수정하지 마세요.
> 설계 근거: [사고속보 연계 기획서](../사고속보-연계-기획서.md)

⚠️ 아래는 **해당 작업 유형에 적용되는 조항**을 찾았는지에 대한 집계입니다.
개별 사고의 법령 위반 여부를 뜻하지 않습니다. 사고속보는 조사 전 신고 단계 정보입니다.

## 요약

- 수집 사고: **332건** (게시일 2025-08-29 ~ 2026-10-07)
- 매핑 데이터: **35종**
- 커버리지: **267/332 = 80%**

## 업종별 커버리지

| 업종 | 매핑 | 전체 | 커버리지 |
|---|---:|---:|---|
| 서비스·판매 | 4 | 4 | 100% ████████████████ |
| 건물·시설 | 22 | 23 | 96% ███████████████ |
| 창고·물류 | 11 | 13 | 85% ██████████████ |
| 환경·폐기물 | 10 | 12 | 83% █████████████ |
| 건설현장 | 115 | 139 | 83% █████████████ |
| 농림축산 | 17 | 21 | 81% █████████████ |
| 제조업 | 80 | 109 | 73% ████████████ |
| 기타 | 8 | 11 | 73% ████████████ |

## 사고 유형별 분포

| 사고 유형 | 건수 | 미매핑 |
|---|---:|---:|
| 떨어짐 | 140 | 17 |
| 깔림 | 55 | 14 |
| 끼임 | 42 | 14 |
| 맞음 | 36 | 9 |
| 부딪힘 | 27 | 9 |
| 폭발 | 8 | 0 |
| 매몰 | 8 | 1 |
| 붕괴 | 5 | 0 |
| 화상 | 4 | 0 |
| 감전 | 4 | 0 |
| 쓰러짐 | 4 | 1 |
| 익사 | 3 | 0 |
| 질식 | 2 | 0 |
| 넘어짐 | 1 | 0 |
| 화재 | 1 | 0 |
| 기타 | 1 | 0 |

## 데이터 공백 큐

미매핑 **65건** 중 최근 25건입니다. 각 항목이 곧 매핑 기여 대상입니다.

| 발생 | 지역 | 업종 | 사고 |
|---|---|---|---|
| 2026-10-04 | 충북 충주시 | 제조업 | [원통형 설비 내부 청소 작업 중 작동되는 설비에 부딪힘](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20261007185530J9VYM3) |
| 2026-09-29 | 서울 서초구 | 건설현장 | [콘크리트 잔재물 청소를 위해 대기 중 무너진 천장 콘크리트에 맞음](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20261002170917NI63FM) |
| 2026-09-21 | 강원 원주시 | 건설현장 | [무너지는 벽체에 깔림](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260927200838OMJ93L) |
| 2026-09-19 | 울산 중구 | 건설현장 | [경사로에서 밀려 내려오는 차량에 부딪힘](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=2026092310295192S5DY) |
| 2026-09-18 | 경남 거제시 | 제조업 | [조선소에서 자전거를 타고 이동 중 차량에 부딪힘](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260923102646PRCM7E) |
| 2026-09-11 | 전남광주 북구 | 건설현장 | [방향 조정 중인 고철에 맞음](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=2026091718541231L30N) |
| 2026-09-03 | 경북 포항시 | 제조업 | [조관기계 정비작업 중 끼임](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=202609061917227H6XMY) |
| 2026-08-28 | 경기 포천시 | 기타 | [차량 수리 중 적재함이 하강하여 끼임](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260903091756C0FK6Y) |
| 2026-08-27 | 충남 천안시 | 제조업 | [거푸집 부재 아래에서 조립 작업 중 거푸집 부재가 쓰러져 깔림](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=202608281730134U1UMX) |
| 2026-08-26 | 경기 광주시 | 제조업 | [골재 야적장에서 골재 투입구로 이동 중인 로더에 부딪힘](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260828161946GG5ILL) |
| 2026-08-14 | 경북 의성군 | 제조업 | [가동 중인 성형기 점검작업 중 끼임](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=202608201751171QP9JG) |
| 2026-07-24 | 경기 포천시 | 제조업 | [둥근톱 날에 의해 튕긴 목재에 맞음](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260802181622HCC126) |
| 2026-07-22 | 경기 평택시 | 제조업 | [가공설비 정비 작업 중 끼임](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260723144449ILV32V) |
| 2026-07-15 | 충북 청주시 | 제조업 | [가동 중인 적재기 내부 점검 중 프레임에 끼임](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260723144017U817ZZ) |
| 2026-07-13 | 충북 음성군 | 건설현장 | [떨어지는 시멘트 블록에 맞음](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=202607151826010C5TAF) |
| 2026-07-09 | 경북 고령군 | 농림축산 | [구조물이 파손되어 비료 저장소로 떨어짐](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260711142645QP3I7B) |
| 2026-06-17 | 경기 안산시 | 건설현장 | [자재 운반 작업 중 밟고 있던 판넬이 파손되며 떨어짐](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260705185224LN4509) |
| 2026-07-01 | 경북 구미시 | 건설현장 | [석고보드 보수 작업 중 건물 사이로 떨어짐](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=202607031825131611P0) |
| 2026-06-26 | 울산 울주군 | 건설현장 | [떨어지는 흙덩이에 깔림](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260702132516X1O6VP) |
| 2026-06-27 | 충남 아산시 | 건설현장 | [천막이 찢어져 떨어짐](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260702132306MPR0Q9) |
| 2026-06-20 | 전남 신안군 | 건설현장 | [갱폼 해체 작업 중 떨어짐](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260628145906P6K8MB) |
| 2026-06-11 | 전북 군산시 | 제조업 | [화물트럭 유도 작업 중 부딪힘](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260614174458BYPCHN) |
| 2026-05-08 | 경남 창원시 | 제조업 | [가공설비 점검 중 안전문에 끼임](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=202606111107014HG1QR) |
| 2026-06-02 | 부산 사상구 | 환경·폐기물 | [차량 적재함 개폐문이 닫히며 끼임](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260607081423T8ZZVJ) |
| 2026-05-14 | 인천 중구 | 건설현장 | [배관 통로 점검 중 천장마감재를 밟고 떨어짐](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260604110344TLYI60) |

---

출처: 안전보건공단 산업안전포털 [사고속보](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2)

⚠️ 본 결과는 참고용이며 법적 판단을 대체하지 않습니다.

# 사고속보 커버리지 리포트

> 이 파일은 `scripts/build_coverage_report.py`가 생성합니다. 직접 수정하지 마세요.
> 설계 근거: [사고속보 연계 기획서](../사고속보-연계-기획서.md)

⚠️ 아래는 **해당 작업 유형에 적용되는 조항**을 찾았는지에 대한 집계입니다.
개별 사고의 법령 위반 여부를 뜻하지 않습니다. 사고속보는 조사 전 신고 단계 정보입니다.

## 요약

- 수집 사고: **332건** (게시일 2025-08-29 ~ 2026-10-07)
- 매핑 데이터: **37종**
- 커버리지: **278/332 = 84%**

## 업종별 커버리지

| 업종 | 매핑 | 전체 | 커버리지 |
|---|---:|---:|---|
| 서비스·판매 | 4 | 4 | 100% ████████████████ |
| 건물·시설 | 22 | 23 | 96% ███████████████ |
| 창고·물류 | 11 | 13 | 85% ██████████████ |
| 제조업 | 91 | 109 | 83% █████████████ |
| 환경·폐기물 | 10 | 12 | 83% █████████████ |
| 건설현장 | 115 | 139 | 83% █████████████ |
| 농림축산 | 17 | 21 | 81% █████████████ |
| 기타 | 8 | 11 | 73% ████████████ |

## 사고 유형별 분포

| 사고 유형 | 건수 | 미매핑 |
|---|---:|---:|
| 떨어짐 | 140 | 17 |
| 깔림 | 55 | 15 |
| 끼임 | 42 | 5 |
| 맞음 | 36 | 9 |
| 부딪힘 | 27 | 6 |
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

미매핑 **54건** 중 최근 25건입니다. 각 항목이 곧 매핑 기여 대상입니다.

| 발생 | 지역 | 업종 | 사고 |
|---|---|---|---|
| 2026-10-04 | 충북 충주시 | 제조업 | [원통형 설비 내부 청소 작업 중 작동되는 설비에 부딪힘](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20261007185530J9VYM3) |
| 2026-09-29 | 서울 서초구 | 건설현장 | [콘크리트 잔재물 청소를 위해 대기 중 무너진 천장 콘크리트에 맞음](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20261002170917NI63FM) |
| 2026-09-21 | 강원 원주시 | 건설현장 | [무너지는 벽체에 깔림](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260927200838OMJ93L) |
| 2026-09-19 | 울산 중구 | 건설현장 | [경사로에서 밀려 내려오는 차량에 부딪힘](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=2026092310295192S5DY) |
| 2026-09-18 | 경남 거제시 | 제조업 | [조선소에서 자전거를 타고 이동 중 차량에 부딪힘](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260923102646PRCM7E) |
| 2026-09-11 | 전남광주 북구 | 건설현장 | [방향 조정 중인 고철에 맞음](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=2026091718541231L30N) |
| 2026-08-28 | 경기 포천시 | 기타 | [차량 수리 중 적재함이 하강하여 끼임](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260903091756C0FK6Y) |
| 2026-08-27 | 충남 천안시 | 제조업 | [거푸집 부재 아래에서 조립 작업 중 거푸집 부재가 쓰러져 깔림](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=202608281730134U1UMX) |
| 2026-07-24 | 경기 포천시 | 제조업 | [둥근톱 날에 의해 튕긴 목재에 맞음](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260802181622HCC126) |
| 2026-07-13 | 충북 음성군 | 건설현장 | [떨어지는 시멘트 블록에 맞음](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=202607151826010C5TAF) |
| 2026-07-09 | 경북 고령군 | 농림축산 | [구조물이 파손되어 비료 저장소로 떨어짐](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260711142645QP3I7B) |
| 2026-06-17 | 경기 안산시 | 건설현장 | [자재 운반 작업 중 밟고 있던 판넬이 파손되며 떨어짐](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260705185224LN4509) |
| 2026-07-01 | 경북 구미시 | 건설현장 | [석고보드 보수 작업 중 건물 사이로 떨어짐](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=202607031825131611P0) |
| 2026-06-26 | 울산 울주군 | 건설현장 | [떨어지는 흙덩이에 깔림](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260702132516X1O6VP) |
| 2026-06-27 | 충남 아산시 | 건설현장 | [천막이 찢어져 떨어짐](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260702132306MPR0Q9) |
| 2026-06-20 | 전남 신안군 | 건설현장 | [갱폼 해체 작업 중 떨어짐](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260628145906P6K8MB) |
| 2026-06-11 | 전북 군산시 | 제조업 | [화물트럭 유도 작업 중 부딪힘](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260614174458BYPCHN) |
| 2026-06-02 | 부산 사상구 | 환경·폐기물 | [차량 적재함 개폐문이 닫히며 끼임](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260607081423T8ZZVJ) |
| 2026-05-14 | 인천 중구 | 건설현장 | [배관 통로 점검 중 천장마감재를 밟고 떨어짐](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260604110344TLYI60) |
| 2026-05-19 | 서울 동작구 | 건물·시설 | [환기구 덮개를 들어내던 중 환기구 아래로 떨어짐](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=202605271005247DRKH1) |
| 2026-05-20 | 부산 사하구 | 창고·물류 | [차고지로 복귀하는 버스에 부딪힘](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=2026052710042251RFLW) |
| 2026-05-18 | 전남 여수시 | 제조업 | [이동 중 유휴설비로부터 분리되어 떨어지는 덕트 배관에 맞음](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260520161933D9VWWW) |
| 2026-05-11 | 경남 합천군 | 농림축산 | [후진 중인 화물차량에 부딪힘](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=202605141028413Z1JGX) |
| 2026-04-29 | 울산 울주군 | 건설현장 | [콘크리트 믹서 트럭 위에서 떨어짐](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260502084831CMY99Q) |
| 2026-04-27 | 경남 창원시 | 건설현장 | [넘어지는 판넬에 깔림](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2?bbsId=B2025021314108&pstNo=20260502084635A6DZSZ) |

---

출처: 안전보건공단 산업안전포털 [사고속보](https://portal.kosha.or.kr/business-apply-search/etc-biz/acc-invest-act/cont2)

⚠️ 본 결과는 참고용이며 법적 판단을 대체하지 않습니다.

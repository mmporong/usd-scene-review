# 한국어 사용 안내

두 로컬 USD revision을 참조 파일까지 별도 snapshot으로 고정하고, 같은 시간·variant·load 조건에서 변경을 검토합니다. 원본 수정·자동 수정·병합은 하지 않습니다. 자료가 부족하면 unknown으로 표시합니다.

현재 개발 기준은 Kit 107.3.3 / Python 3.11 / OpenUSD 24.05입니다. 실제 Kit GUI는 GPU 드라이버 불일치와 DISPLAY 부재로 검증하지 못했습니다. Python 검사 성공은 GUI 성공을 뜻하지 않습니다.

snapshot·compare 명령과 기존 Isaac Sim Python을 사용하는 방법은 README에 있습니다. 종료 코드 0도 충돌 없음의 보증은 아닙니다. 최소 UI는 비교 목록과 별도 정적 A/B viewport를 제공하며, 애니메이션 viewport는 거부합니다. 자체 fixture만 공개하며 기존 공장 프로젝트는 수정하지 않습니다.

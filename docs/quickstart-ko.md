# 배포 후보 빠른 시작 — 한국어

Windows와 이미 설치된 Isaac Sim 4.5 SDK(Kit 106.5, Python 3.10, OpenUSD 22.11),
사용 가능한 NVIDIA RTX GPU가 필요합니다. SDK는 포함하지 않으며 설치·업그레이드하지
않습니다. 전체 Isaac 앱 지원은 검증되지 않았습니다. [지원 범위](distribution-support.md)를
확인하세요. 프로젝트 라이선스는 사용자 선택을 기다리는 중입니다.

## 1. 새 폴더에 압축 해제하고 진단하기

압축 파일의 `Get-FileHash <archive.zip> -Algorithm SHA256` 값과 별도 체크섬을 대조한 뒤
새 폴더에 압축을 풉니다. 결과물은 이 폴더 밖에 저장합니다. 압축 해제 폴더에서:

```powershell
$sdk = '<이미 설치된 Isaac Sim 4.5 SDK 폴더>'
$python = Join-Path $sdk 'kit/python/python.exe'
& $python -B .\review_kit.py verify
& $python -B .\review_kit.py --sdk $sdk doctor
```

진단은 런타임 ABI·기존 라이브러리·재질 템플릿과 GPU 상태를 읽기만 합니다.
진단 통과만으로 실제 렌더링을 인증하지 않습니다. 오류가 나면 식별자와 안내를 확인하고
중단하세요. 프로그램이 드라이버나 시스템 설정을 고치지는 않습니다.

## 2. 공개 합성 예제와 비교 결과 만들기

`$parent`는 이미 존재하고 쓰기 가능한 폴더로 지정합니다. 아래 작업 폴더는 모두 새 이름을
써야 합니다. 기존 파일을 덮어쓰지 않습니다. 합성 랙은 프로젝트가 독립적으로 만든 예제로,
공장 원본 데이터가 아닙니다.

```powershell
$parent = '<이미 존재하는 출력용 폴더>'
$sample = Join-Path $parent 'review-sample'
& $python -B .\review_kit.py --sdk $sdk sample --workspace $sample
& $python -B .\review_kit.py --sdk $sdk compare --before "$sample/snapshot-A/manifest.json" --after "$sample/snapshot-B/manifest.json" --workspace "$parent/review-comparison"
```

`review-comparison/review.html`은 인터넷 없이 열 수 있습니다. JSON도 함께 저장됩니다.
이전 A는 오른쪽 `(0,0.2,0)m`, 현재 B는 왼쪽 `(0,0,0)m`, 이동량은 `(0,-0.2,0)m`입니다.
변경을 결함으로 판정하지 않습니다. 충돌은 unknown이고 기본 정책 임계값은 없습니다.

## 3. 최소 Kit에서 열고 결과 저장하기

```powershell
& $python -B .\review_kit.py --sdk $sdk launch --data $sample --workspace "$parent/review-session"
```

새 최소 호스트에서 예제를 비교하고 `review-session/reports`에 JSON/HTML을 저장한 다음,
현재 B와 연두색 이전 위치 표시, 우측 요약을 엽니다. View A/B, 검색, 초점·홀로그램 토글을
사용할 수 있습니다. 새 비교 결과는 호스트의 출력 폴더에 새 이름을 입력하고 **Save results**로
저장합니다. 입력 스냅샷 내부로는 저장할 수 없고, 입력이 바뀌면 다시 비교해야 합니다.

Close review 후 최소 호스트를 정상적으로 닫으세요. 런처는 호스트 정상 종료와 뷰어의
원본 보존 확인이 있어야 성공으로 처리합니다. Ctrl+C나 시간 초과로 강제 정리한 실행은
정상 종료 통과가 아닙니다. 로그는 작업 폴더에 남으며 공개 업로드하지 마세요.

다른 새 세션 폴더를 지정하고 `--smoke --timeout 300`을 붙이면 실제 GPU/GUI에서
A/B 렌더링·카메라·홀로그램·저장·종료를 자동 검사합니다. `session-result.json`과
`process-result.json`을 함께 확인합니다. CPU CI나 PNG 생성만으로 GUI 성공을 주장하지 않습니다.

선택적으로 `launch.ps1 -Sdk $sdk -Action launch -Data $sample -Workspace <새폴더>`를
쓸 수 있습니다. 스크립트 정책이 막으면 위 SDK Python 명령을 그대로 사용하세요.
보안 설정을 바꾸거나 관리자 권한으로 설치할 필요는 없습니다.

## 오류 안내

| 식별자 | 다음 조치 |
| --- | --- |
| PACKAGE_HASH / PACKAGE_FILES | 검증한 압축 파일을 새 폴더에 다시 풀고 출력은 밖에 저장하세요. |
| SDK_REQUIRED / SDK_VERSION / ABI_UNQUALIFIED | 시스템 Python 대신 검증 대상 기존 SDK를 지정하세요. |
| GPU_DIAGNOSTIC | GPU 접근 상태를 별도로 확인하세요. 자동 드라이버 복구는 하지 않습니다. |
| WORKSPACE_LOCATION / file exists | 압축 해제 폴더 밖의 새 이름과 쓰기 가능한 부모 폴더를 지정하세요. |
| KIT_EXIT / timeout | 비공개 결과·로그를 확인하세요. 강제 정리는 정상 종료가 아닙니다. |

소스에서 패키지를 만들려면 `python tools/package_candidate.py <새압축파일.zip>`을 실행합니다.
같은 도구 환경에서 두 번 빌드해 체크섬을 비교할 수 있습니다. CPU 테스트에는 OpenUSD와
선택적 test 의존성이 필요합니다. CPU CI, 설치 SDK의 실제 GUI 검사, 전체 Isaac 앱 지원은
각각 별개의 검증 범위입니다.

Kit Python 캐시는 세션의 `runtime` 작업 복사본에 생성됩니다. 검증한 원본 압축 해제 폴더는 변경하지 않으며 SDK를 설치하지 않습니다.

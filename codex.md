# Codex 작업 기록

이 파일은 PDS 학습 위키를 만들면서 나온 아이디어, 결정, 시행착오를 계속 기록하는 곳이다.

## 현재 방향

- 기존 강의 HTML은 그대로 두고, 루트의 `index.html`에서 시간표형 홈 화면을 제공한다.
- 홈 목록 데이터는 `scripts/generate-site-data.mjs`가 HTML 파일을 읽어 `site-data.js`로 생성한다.
- 새 자료를 추가할 때는 `npm run build`를 실행해 홈 목록을 갱신한다.
- 무료 호스팅은 GitHub Pages + GitHub Actions를 1순위로 둔다. `main` 브랜치에 push하면 `.github/workflows/deploy.yml`이 자동 배포한다.

## 파일명 규칙

- 배포 안정성을 위해 강의 HTML 파일명은 ASCII로 고정한다.
- 형식은 `MMDD_교시_english-slug.html`이다.
- 예: `0511_2_public-health-policy.html`
- slug에는 영문 소문자, 숫자, 하이픈만 쓴다.
- 화면에 표시되는 한국어 제목은 파일명이 아니라 각 HTML 내부의 `<h1>` 또는 `<title>`에서 가져온다.

## 시행착오

- 처음에는 기존 한국어 파일명을 그대로 링크하는 방식으로 구성했다.
- 사용자가 배포 시 파일명 인코딩 문제가 생길 수 있다고 지적했다.
- 이에 따라 기존 23개 HTML을 영어 slug 파일명으로 rename했고, 빌드 스크립트에서 비 ASCII 또는 규칙 밖 파일명을 오류로 막도록 수정했다.
- 첫 빌드에서 `weekdayLabels` 상수를 사용한 뒤 선언하는 순서 오류가 발생했다. 상수를 상단으로 이동해 Node.js ESM 초기화 오류를 해결했다.
- `site-data.js`를 빌드와 동시에 병렬로 읽었더니 파일 생성 전에 읽기 명령이 먼저 실행되어 실패했다. 생성 산출물 확인은 빌드 후 순차 실행해야 한다.
- PowerShell `Get-Content`에서는 UTF-8 한글이 깨져 보일 수 있었다. 실제 파일 유효성은 `node --check site-data.js`와 브라우저 렌더링으로 확인했다.
- 브라우저 검증에서 같은 강의 링크가 시간표와 전체 목록에 각각 있어 `href`만으로는 locator가 2개 잡혔다. 검증 시에는 `.schedule-view` 또는 `.lecture-list`로 범위를 좁혀 확인했다.

## 다음 아이디어

- 실제 수업 시작/종료 시간이 확정되면 `site.config.json`의 `periods.time`을 채워 시간표 셀에 표시한다.
- GitHub 저장소가 연결되면 Codex가 `npm run build` 후 commit/push까지 수행해 재배포를 자동화할 수 있다.

## 2026-05-11 디자인 수정

- 사용자가 기존 시간표 디자인이 부족하다고 피드백했다.
- 시간표를 단순 HTML 표처럼 보이지 않게 주차 헤더, 고정 교시 축, 날짜 헤더, 태그별 색상 강의 블록으로 재구성했다.
- 빈 시간표 칸은 패턴 배경과 짧은 선으로 낮춰 보이게 하고, 실제 강의 카드에는 좌측 색상 바와 hover 상태를 추가했다.
- 전체 자료 카드도 시간표와 같은 태그 색상 체계를 공유하게 바꿨다.
- 사용자가 태그를 과목별이 아니라 담당 교수님별로 바꾸라고 요청했다.
- `site.config.json`에 `pageProfessors` 명시 매핑을 추가했다. 교수명은 박훈기, 한승훈, 김대호, 손정식, 신영전, 김민주, 이어진, 송은섭, 김원규로 정리했다.
- 생성 스크립트는 파일별 명시 매핑을 우선 사용하고, 새 파일에서 매핑이 빠졌을 때만 상단 메타 텍스트의 `professorRules`로 보조 추론한다.

## 2026-05-11 시간표 이미지 반영

- 사용자가 배치표 이미지를 제공했고, 괄호 속 이름이 담당 교수님이라고 정정했다.
- 현재 보유한 HTML 23개는 배치표의 괄호 속 이름 기준으로 `pageProfessors`를 유지한다.
- 2교시짜리 강의는 파일명 시작 교시를 유지하고 `site.config.json`의 `pageSpans`에서 칸 수를 지정하기로 했다.
- 우선 `0429_5`, `0430_1`, `0430_3`, `0430_5`, `0501_3`, `0506_1`, `0507_5` 강의를 2칸으로 표시한다.
- 홈 화면 렌더러는 span으로 덮인 다음 교시 칸을 만들지 않고, 시작 교시 셀이 CSS grid row span으로 두 칸을 차지하게 바꿨다.
- 사용자가 시간표를 까먹지 않게 저장해두라고 요청했다.
- 원본 이미지의 배치표 내용을 `timetable.md`에 전사했다. 앞으로 자료가 추가되면 이 파일을 기준으로 파일명, 담당 교수님, span을 맞춘다.

## 2026-05-11 배포 시행착오

- GitHub 저장소 `choiseungri/pds-study-wiki`를 공개 저장소로 만들고 `main` 브랜치에 첫 push를 했다.
- 첫 GitHub Actions 배포는 새 저장소에서 Pages가 아직 활성화되지 않아 `actions/configure-pages`가 Pages site를 찾지 못하며 실패했다.
- `.github/workflows/deploy.yml`의 `Configure Pages` 단계에 `enablement: true`를 추가해 첫 배포 시 Pages를 활성화하도록 수정했다.
- 두 번째 실행은 Actions 토큰이 Pages site 생성 권한을 얻지 못해 실패했다.
- GitHub 저장소 Settings > Pages에서 Source를 `GitHub Actions`로 직접 선택해 Pages를 활성화했다.

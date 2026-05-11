# PDS 학습 위키

기존 HTML 강의자료를 시간표형 홈 화면으로 엮는 정적 사이트입니다. 별도 서버가 필요 없고 GitHub Pages, Cloudflare Pages, Netlify 같은 무료 정적 호스팅에 올릴 수 있습니다.

배포 URL: https://choiseungri.github.io/pds-study-wiki/

## 자료 추가

1. 새 HTML 파일을 이 폴더에 넣습니다.
2. 파일명은 `MMDD_교시_english-slug.html` 형식을 사용합니다.
   - 예: `0511_2_public-health-policy.html`
   - 파일명은 영문 소문자, 숫자, 하이픈만 사용합니다.
   - 홈 화면의 제목은 파일명이 아니라 HTML 내부의 `<h1>` 또는 `<title>`에서 가져옵니다.
3. 아래 명령으로 홈 목록을 갱신합니다.

```powershell
npm run build
```

`site.config.json`에서 사이트 제목, 학년도, 교시 시간, 파일별 담당 교수 매핑을 수정할 수 있습니다.
2교시짜리 강의는 `pageSpans`에 파일명과 `2`를 추가하면 시간표에서 두 칸 높이로 표시됩니다.
원본 배치표 전사본은 `timetable.md`에 저장해 두었습니다.
작업 중 생긴 아이디어, 결정, 시행착오는 `codex.md`에 계속 기록합니다.

## 로컬 미리보기

```powershell
npm run build
npm run serve
```

브라우저에서 `http://localhost:4173`을 열면 됩니다.

## 무료 호스팅 추천

가장 단순한 선택지는 GitHub Pages입니다.

1. 이 폴더를 GitHub 저장소로 올립니다.
2. GitHub 저장소의 `Settings > Pages`에서 `Build and deployment`를 `GitHub Actions`로 설정합니다.
3. `main` 브랜치에 push하면 `.github/workflows/deploy.yml`이 자동으로 `site-data.js`를 다시 만들고 배포합니다.

이후 Codex가 파일을 수정하고 `npm run build`, `git add`, `git commit`, `git push`까지 실행할 수 있는 상태라면 재배포는 push만으로 자동 처리됩니다.

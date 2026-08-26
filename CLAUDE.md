# Git 규칙

## 커밋 identity (필수)

이 리포의 모든 commit/push는 **acceptha 계정**으로 수행한다:

- `user.name = acceptha`, `user.email = acceptha@gmail.com`
- identity는 글로벌 `.gitconfig`의 `includeIf "gitdir/i:D:/git/acceptha/"` → `.gitconfig2`로 자동 적용됨

커밋 전 `git config user.email`이 `acceptha@gmail.com`인지 확인하고, 아니면 커밋하지 말고 includeIf 설정을 먼저 복구할 것. `suim9770@gmail.com`(hattuping)으로 커밋 금지.

# Python 환경

PATH의 기본 `python`은 3.9라 이 프로젝트(요구 ≥3.11)에서 쓸 수 없다. 항상 프로젝트 venv를 쓸 것:

- 실행: `.\.venv\Scripts\python.exe -m pytest -q` (venv는 3.13)
- 지원 범위: 하한 3.11 유지(라이브러리이므로 올리지 않음), CI는 3.11~3.14 테스트

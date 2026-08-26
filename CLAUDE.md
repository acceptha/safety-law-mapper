# Git 규칙

## 커밋 identity (필수)

이 리포의 모든 commit/push는 **acceptha 계정**으로 수행한다:

- `user.name = acceptha`, `user.email = acceptha@gmail.com`
- identity는 글로벌 `.gitconfig`의 `includeIf "gitdir/i:D:/git/acceptha/"` → `.gitconfig2`로 자동 적용됨

커밋 전 `git config user.email`이 `acceptha@gmail.com`인지 확인하고, 아니면 커밋하지 말고 includeIf 설정을 먼저 복구할 것. `suim9770@gmail.com`(hattuping)으로 커밋 금지.

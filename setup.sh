#!/usr/bin/env bash
# 각 단계 완성본을 _ref/<태그>/ 폴더로 펼칩니다 (git worktree).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p _ref
echo "단계별 완성본을 _ref/ 에 준비합니다..."
for tag in $(git tag | grep -E '^[ab][0-9]+-' | sort); do
  if [ -d "_ref/$tag" ]; then
    echo "  이미 있음  _ref/$tag"
  else
    git worktree add "_ref/$tag" "$tag" >/dev/null 2>&1 && echo "  생성      _ref/$tag"
  fi
done
echo ""
echo "완료. 각 단계 완성본은 _ref/<태그>/ 에 있습니다."
echo "비교 예) code --diff 내작업/backend/main.py _ref/a11-fastapi/backend/main.py"

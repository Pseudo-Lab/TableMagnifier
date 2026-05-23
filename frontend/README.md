# Frontend Workbench

이 디렉터리는 `table-env-bench`의 React + Vite + TypeScript workbench입니다. 기본 사용자는 사람 평가자와 family 개발자이며, 데이터는 FastAPI session server에서 받습니다.

## 실행

Repo root에서 API server를 먼저 실행합니다.

```bash
uv run python -m table_env_bench.scripts.run_server --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

브라우저에서 `http://127.0.0.1:5173/`를 엽니다. URL에 유효한 `family`, `level`, `seed`, `template_id`가 있으면 개발용 family deep link가 우선하고, 없으면 `/api/benchmark-suites`의 첫 generated record로 시작합니다.

## 검증

```bash
npm run build
npm run lint
npm run visual:workbench
```

Agent observation gallery를 캡처할 때는 repo root에서 gallery를 먼저 만든 뒤 실행합니다.

```bash
uv run python -m table_env_bench.scripts.export_agent_observation_gallery --out artifacts/agent_observations_active --suite canonical_dev
cd frontend
npm run visual:capture:agent-observations
```

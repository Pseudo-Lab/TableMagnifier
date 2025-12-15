---
stepsCompleted: [1, 2, 3]
inputDocuments: []
documentCounts:
  briefs: 0
  research: 0
  brainstorming: 0
  projectDocs: 0
workflowType: 'prd'
lastStep: 3
project_name: 'TableMagnifier UI'
user_name: 'Jaehyeokchoi'
date: '2025-12-15'
projectType: 'brownfield'
existingComponents:
  - 'generate_synthetic_table/ - LangGraph 기반 테이블 생성 파이프라인'
  - 'annotate_tools/ - React + FastAPI 어노테이션 도구'
  - 'polling_gemini/ - Gemini API 폴링 시스템'
projectClassification:
  technicalType: 'Web Application (React + FastAPI + WebSocket)'
  domain: 'AI/ML Data Processing Tool'
  complexity: 'Medium-High'
  context: 'Brownfield'
---

# Product Requirements Document - TableMagnifier UI

**Author:** Jaehyeokchoi
**Date:** 2025-12-15
**Project Type:** Brownfield (기존 시스템 확장)

---

## 1. Executive Summary

### Vision

TableMagnifier UI는 한국어 테이블 이미지에서 합성 데이터와 QA 쌍을 생성하는 LangGraph 파이프라인을 
웹 기반 인터페이스로 실행하고 시각화하는 도구입니다. 

연구원과 데이터 라벨러가 CLI 없이도 직관적으로 파이프라인을 실행하고, 
각 단계의 결과를 실시간으로 확인하며, 필요시 수정하여 저장할 수 있습니다.

### Problem Statement

현재 `generate_synthetic_table` 파이프라인은 CLI로만 실행 가능하여:
- 비개발자 사용이 어려움
- 중간 결과 확인이 불편함
- 배치 처리 시 진행 상황 파악이 어려움
- 결과 수정을 위해 별도 도구(`annotate_tools`) 사용 필요

### Solution

웹 UI에서 다음 워크플로우를 지원:
1. **PNG 이미지 선택** → 파일 업로드 또는 폴더 선택
2. **실시간 파이프라인 실행** → 각 노드 진행 상태를 시각적 다이어그램으로 표시
3. **중간/최종 결과 시각화** → Side-by-side 비교 뷰 (원본 → 파싱 → 합성)
4. **배치 처리** → 여러 이미지 동시 처리 및 진행률 대시보드
5. **결과 수정/저장** → 인라인 편집, 검증 지표, 다중 포맷 내보내기

### What Makes This Special

- **End-to-End 워크플로우**: 이미지 선택부터 QA 생성까지 한 화면에서 완료
- **실시간 피드백**: LangGraph 노드별 진행 상태를 파이프라인 다이어그램으로 시각화
- **배치 처리 대시보드**: 대량 데이터 처리 시 생산성 극대화
- **품질 검증 내장**: 자동 검증 지표 및 결과 비교 기능
- **기존 시스템 통합**: `annotate_tools` 편집 기능 + 파이프라인 실행 기능 통합

### Technical Approach

- **Real-time Updates**: WebSocket 기반 실시간 상태 업데이트
- **Async Processing**: 비동기 태스크 큐로 배치 처리 지원
- **State Management**: 파이프라인 상태 영속화 전략

### Project Classification

| 항목 | 값 |
|------|-----|
| **Technical Type** | Web Application (React + FastAPI + WebSocket) |
| **Domain** | AI/ML Data Processing Tool |
| **Complexity** | Medium-High |
| **Project Context** | Brownfield - 기존 시스템 확장 |

### Target Users

- **Primary**: TableMagnifier 연구팀 (가짜연구소 11기 NLx Crew)
- **Secondary**: 데이터 라벨러, 한국어 TableQA 연구자

---

## 2. Success Criteria

### User Success

| 성공 지표 | 측정 기준 |
|----------|----------|
| **단건 처리 완료** | PNG 업로드 → QA JSON 저장까지 한 화면에서 완료 |
| **배치 처리 완료** | 여러 이미지 선택 → 전체 처리 완료 → 결과 일괄 저장 |
| **결과 확인 용이** | 원본 이미지와 생성 결과를 한눈에 비교 가능 |
| **CLI 불필요** | 비개발자도 웹 UI만으로 전체 워크플로우 수행 가능 |

**핵심 성공 순간:**
- "클릭 몇 번으로 QA 데이터가 생성됐다!"
- "100개 이미지를 한번에 돌려놓고 다른 일 할 수 있다!"

### Business Success

| 성공 지표 | 측정 기준 |
|----------|----------|
| **팀 생산성 향상** | CLI 대비 처리 시간 50% 이상 단축 |
| **비개발자 참여** | 연구팀 전원이 UI로 데이터 생성 가능 |
| **데이터 생산량** | 대량 테이블 데이터 생성 파이프라인 구축 완료 |

### Technical Success

| 성공 지표 | 측정 기준 |
|----------|----------|
| **단건 처리 성능** | Timeout 없이 안정적 처리 (LLM 응답 시간에 맞춤) |
| **배치 처리 성능** | 시스템 리소스가 허용하는 최대치까지 병렬 처리 |
| **중단 복구** | 배치 처리 중단 시 이어서 처리 가능 (체크포인트) |
| **에러 핸들링** | 에러 발생 시 사용자가 재시도 여부 선택 가능 |
| **결과 저장** | QA 쌍 JSON 파일로 저장 완료 |

### Measurable Outcomes

| 항목 | MVP 기준 | 목표 |
|------|---------|------|
| 단건 처리 | ✅ 작동 | Timeout 없음 |
| 배치 처리 | ✅ 10개 이상 동시 | 시스템 한계까지 |
| 중단 복구 | ✅ 체크포인트 저장 | 언제든 재개 가능 |
| 에러 재시도 | ✅ 사용자 선택 | 개별/전체 재시도 |

---

## 3. Product Scope

### MVP (Minimum Viable Product)

**Must Have:**
- [ ] PNG 이미지 업로드 (단건/다건)
- [ ] LangGraph 파이프라인 실행
- [ ] 실시간 진행 상태 표시
- [ ] 결과 시각화 (원본 ↔ 합성 테이블)
- [ ] QA 쌍 JSON 저장
- [ ] 배치 처리 (여러 이미지)
- [ ] 중단 시 이어서 처리 (체크포인트)
- [ ] 에러 시 사용자 재시도 선택

**Nice to Have:**
- [ ] 결과 편집 기능
- [ ] 다중 포맷 내보내기 (CSV, HTML)
- [ ] 히스토리/비교 기능
- [ ] 자동 검증 지표

### Out of Scope (V1)

- 모델 학습/파인튜닝
- 다국어 지원 (한국어 전용)
- 사용자 인증/권한 관리
- 클라우드 배포 (로컬 실행 우선)

---

## 4. User Personas

<!-- Step 5에서 작성 예정 -->

---

## 5. User Stories & Requirements

<!-- Step 6에서 작성 예정 -->

---

## 6. Functional Requirements

<!-- Step 7에서 작성 예정 -->

---

## 7. Non-Functional Requirements

<!-- Step 8에서 작성 예정 -->

---

## 8. Technical Constraints

<!-- Step 9에서 작성 예정 -->

---

## 9. Out of Scope

<!-- Step 10에서 작성 예정 -->

---

## 10. Risks & Mitigations

<!-- Step 11에서 작성 예정 -->

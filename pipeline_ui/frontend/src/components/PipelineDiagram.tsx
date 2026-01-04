import React from 'react';
import { CheckCircle, Loader2, Circle, AlertCircle, RotateCcw } from 'lucide-react';

// 파이프라인 노드 정의
export interface PipelineNodeData {
  id: string;
  name: string;
  shortName: string;
  description: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
  result?: string; // 중간 결과 (HTML 또는 텍스트)
  retryCount?: number;
}

// 노드 연결 정의
export interface PipelineEdge {
  from: string;
  to: string;
  label?: string;
  isLoop?: boolean;
}

// 파이프라인 노드 설정
export const PIPELINE_NODES: Omit<PipelineNodeData, 'status' | 'result'>[] = [
  {
    id: 'start',
    name: 'Start',
    shortName: '시작',
    description: '이미지 입력',
  },
  {
    id: 'generate_synthetic',
    name: 'Generate Synthetic',
    shortName: '합성 생성',
    description: '이미지에서 합성 테이블 생성',
  },
  {
    id: 'self_reflection',
    name: 'Self Reflection',
    shortName: '검증',
    description: '생성 결과 품질 검증',
  },
  {
    id: 'revise_synthetic',
    name: 'Revise Synthetic',
    shortName: '수정',
    description: '검증 결과에 따라 테이블 수정',
  },
  {
    id: 'parse_synthetic',
    name: 'Parse Synthetic',
    shortName: '파싱',
    description: 'HTML을 JSON으로 변환',
  },
  {
    id: 'generate_qa',
    name: 'Generate QA',
    shortName: 'QA 생성',
    description: 'QA 쌍 생성',
  },
  {
    id: 'end',
    name: 'End',
    shortName: '완료',
    description: '처리 완료',
  },
];

// 파이프라인 엣지 정의
export const PIPELINE_EDGES: PipelineEdge[] = [
  { from: 'start', to: 'generate_synthetic' },
  { from: 'generate_synthetic', to: 'self_reflection' },
  { from: 'self_reflection', to: 'parse_synthetic', label: 'pass' },
  { from: 'self_reflection', to: 'generate_synthetic', label: 'retry', isLoop: true },
  { from: 'parse_synthetic', to: 'generate_qa' },
  { from: 'generate_qa', to: 'end' },
];

// 노드 상태 아이콘
const NodeStatusIcon: React.FC<{ status: PipelineNodeData['status'] }> = ({ status }) => {
  switch (status) {
    case 'completed':
      return <CheckCircle className="w-5 h-5 text-green-400" />;
    case 'running':
      return <Loader2 className="w-5 h-5 text-blue-400 animate-spin" />;
    case 'failed':
      return <AlertCircle className="w-5 h-5 text-red-400" />;
    case 'skipped':
      return <Circle className="w-5 h-5 text-gray-500" />;
    default:
      return <Circle className="w-5 h-5 text-gray-600" />;
  }
};

// 노드 상태 색상
const getNodeColors = (status: PipelineNodeData['status']) => {
  switch (status) {
    case 'completed':
      return 'border-green-500 bg-green-500/10';
    case 'running':
      return 'border-blue-500 bg-blue-500/20 shadow-lg shadow-blue-500/20';
    case 'failed':
      return 'border-red-500 bg-red-500/10';
    case 'skipped':
      return 'border-gray-600 bg-gray-800/50';
    default:
      return 'border-gray-700 bg-gray-800';
  }
};

// 개별 노드 컴포넌트
interface PipelineNodeProps {
  node: PipelineNodeData;
  onClick?: (nodeId: string) => void;
  isSelected?: boolean;
}

const PipelineNode: React.FC<PipelineNodeProps> = ({ node, onClick, isSelected }) => {
  const handleClick = () => {
    if (onClick) {
      onClick(node.id);
    }
  };

  return (
    <div
      onClick={handleClick}
      className={`
        relative flex flex-col items-center p-3 rounded-xl border-2 cursor-pointer
        transition-all duration-300 min-w-[100px]
        ${getNodeColors(node.status)}
        ${isSelected ? 'ring-2 ring-white ring-offset-2 ring-offset-gray-900' : ''}
        hover:scale-105
      `}
    >
      {/* 재시도 카운트 배지 */}
      {node.retryCount && node.retryCount > 0 && (
        <div className="absolute -top-2 -right-2 flex items-center gap-1 px-1.5 py-0.5 bg-orange-600 rounded-full text-xs">
          <RotateCcw className="w-3 h-3" />
          {node.retryCount}
        </div>
      )}
      
      {/* 상태 아이콘 */}
      <NodeStatusIcon status={node.status} />
      
      {/* 노드 이름 */}
      <span className="mt-2 text-sm font-medium text-white text-center">
        {node.shortName}
      </span>
      
      {/* 실행 중 펄스 효과 */}
      {node.status === 'running' && (
        <div className="absolute inset-0 rounded-xl border-2 border-blue-400 animate-ping opacity-30" />
      )}
    </div>
  );
};

// 연결선 컴포넌트 (수평)
interface EdgeLineProps {
  isActive: boolean;
  isLoop?: boolean;
  label?: string;
}

const EdgeLine: React.FC<EdgeLineProps> = ({ isActive, isLoop, label }) => {
  if (isLoop) {
    return null; // 루프는 별도로 처리
  }

  return (
    <div className="flex items-center mx-1">
      {/* 연결선 */}
      <div className="relative w-12 h-0.5">
        <div className={`absolute inset-0 ${isActive ? 'bg-blue-500' : 'bg-gray-600'}`} />
        
        {/* 데이터 흐름 애니메이션 */}
        {isActive && (
          <div className="absolute top-1/2 -translate-y-1/2 w-2 h-2 bg-blue-400 rounded-full animate-flow-right" />
        )}
        
        {/* 화살표 */}
        <div 
          className={`absolute right-0 top-1/2 -translate-y-1/2 border-t-4 border-b-4 border-l-6 
            border-t-transparent border-b-transparent ${isActive ? 'border-l-blue-500' : 'border-l-gray-600'}`}
          style={{ borderLeftWidth: '6px' }}
        />
      </div>
      
      {/* 라벨 */}
      {label && (
        <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-xs text-gray-500">
          {label}
        </span>
      )}
    </div>
  );
};

// 재시도 루프 표시
const RetryLoop: React.FC<{ isActive: boolean }> = ({ isActive }) => {
  return (
    <div className="absolute -top-8 left-1/4 right-1/2 flex items-center justify-center">
      <svg width="200" height="40" className="overflow-visible">
        <path
          d="M 30 35 C 30 10, 170 10, 170 35"
          fill="none"
          stroke={isActive ? '#f97316' : '#4b5563'}
          strokeWidth="2"
          strokeDasharray={isActive ? "5,5" : "none"}
          markerEnd="url(#arrowhead)"
        />
        <defs>
          <marker
            id="arrowhead"
            markerWidth="10"
            markerHeight="7"
            refX="9"
            refY="3.5"
            orient="auto"
          >
            <polygon
              points="0 0, 10 3.5, 0 7"
              fill={isActive ? '#f97316' : '#4b5563'}
            />
          </marker>
        </defs>
        <text x="100" y="8" textAnchor="middle" fill="#9ca3af" fontSize="10">
          retry
        </text>
      </svg>
    </div>
  );
};

// 노드 상태 타입 (간단한 버전 - App.tsx에서 사용)
export type PipelineNodeStates = {
  [key: string]: 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
};

// 노드 결과 타입 (Record로 정의하여 타입 안전성 확보)
export type PipelineNodeResults = Record<string, string | object | undefined>;

// 메인 파이프라인 다이어그램 컴포넌트
interface PipelineDiagramProps {
  nodes?: PipelineNodeData[];
  nodeStates?: PipelineNodeStates;  // 간단한 상태 맵
  nodeResults?: PipelineNodeResults;  // 노드별 결과
  currentNode?: string;
  currentNodeId?: string;
  onNodeClick?: (nodeId: string) => void;
  selectedNodeId?: string;
  animated?: boolean;
}

export function PipelineDiagram({
  nodes: propNodes,
  nodeStates,
  nodeResults,
  currentNode,
  currentNodeId,
  onNodeClick,
  selectedNodeId,
  animated: _animated = false,  // 향후 애니메이션 효과에 사용
}: PipelineDiagramProps): React.ReactElement {
  // nodeStates가 제공되면 nodes 배열 생성
  const nodes: PipelineNodeData[] = propNodes || PIPELINE_NODES.map(nodeConfig => {
    const nodeResult = nodeResults?.[nodeConfig.id];
    let resultStr: string | undefined;
    if (nodeResult !== undefined) {
      resultStr = typeof nodeResult === 'string' ? nodeResult : JSON.stringify(nodeResult);
    }
    return {
      ...nodeConfig,
      status: nodeStates?.[nodeConfig.id] || 'pending',
      result: resultStr,
    };
  });
  
  // 향후 하이라이트에 사용 - 현재 활성 노드 ID
  void (currentNode || currentNodeId);

  // 노드 ID로 데이터 찾기
  const getNodeData = (id: string) => nodes.find(n => n.id === id);
  
  // 현재 노드 이전까지는 완료 상태로 표시
  const isEdgeActive = (fromId: string, toId: string) => {
    const fromNode = getNodeData(fromId);
    const toNode = getNodeData(toId);
    return fromNode?.status === 'completed' && (toNode?.status === 'running' || toNode?.status === 'completed');
  };

  // 재시도 루프 활성화 여부
  const isRetryLoopActive = () => {
    const reflectionNode = getNodeData('self_reflection');
    return reflectionNode?.status === 'running' && (reflectionNode?.retryCount || 0) > 0;
  };

  return (
    <div className="relative p-6 bg-gray-800/50 rounded-xl border border-gray-700">
      <h3 className="text-sm font-medium text-gray-400 mb-6">파이프라인 진행 상태</h3>
      
      {/* 메인 파이프라인 (수평) */}
      <div className="relative flex items-center justify-center gap-2 overflow-x-auto pb-4">
        {/* 재시도 루프 SVG */}
        <RetryLoop isActive={isRetryLoopActive()} />
        
        {/* 노드들 */}
        {PIPELINE_NODES.map((nodeConfig, index) => {
          const nodeData = getNodeData(nodeConfig.id) || {
            ...nodeConfig,
            status: 'pending' as const,
          };
          
          const isLast = index === PIPELINE_NODES.length - 1;
          const nextNodeConfig = PIPELINE_NODES[index + 1];
          
          return (
            <React.Fragment key={nodeConfig.id}>
              <PipelineNode
                node={nodeData}
                onClick={onNodeClick}
                isSelected={selectedNodeId === nodeConfig.id}
              />
              
              {!isLast && nextNodeConfig && (
                <EdgeLine
                  isActive={isEdgeActive(nodeConfig.id, nextNodeConfig.id)}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>
      
      {/* 범례 */}
      <div className="flex items-center justify-center gap-6 mt-4 text-xs text-gray-500">
        <div className="flex items-center gap-1">
          <Circle className="w-3 h-3 text-gray-600" />
          <span>대기</span>
        </div>
        <div className="flex items-center gap-1">
          <Loader2 className="w-3 h-3 text-blue-400" />
          <span>실행 중</span>
        </div>
        <div className="flex items-center gap-1">
          <CheckCircle className="w-3 h-3 text-green-400" />
          <span>완료</span>
        </div>
        <div className="flex items-center gap-1">
          <AlertCircle className="w-3 h-3 text-red-400" />
          <span>실패</span>
        </div>
      </div>
    </div>
  );
};

// 노드 상세 결과 패널
interface NodeDetailPanelProps {
  node: PipelineNodeData | null;
  onClose: () => void;
}

export const NodeDetailPanel: React.FC<NodeDetailPanelProps> = ({ node, onClose }) => {
  if (!node) return null;

  return (
    <div className="bg-gray-800 rounded-xl border border-gray-700 p-4 mt-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-medium text-white">{node.name}</h3>
          <p className="text-sm text-gray-400">{node.description}</p>
        </div>
        <button
          onClick={onClose}
          className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg"
        >
          ✕
        </button>
      </div>
      
      {/* 노드 상태 */}
      <div className="flex items-center gap-2 mb-4">
        <span className="text-sm text-gray-400">상태:</span>
        <NodeStatusIcon status={node.status} />
        <span className="text-sm text-white capitalize">{node.status}</span>
        {node.retryCount !== undefined && node.retryCount > 0 && (
          <span className="text-sm text-orange-400">(재시도 {node.retryCount}회)</span>
        )}
      </div>
      
      {/* 중간 결과 */}
      {node.result && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-gray-400 mb-2">결과:</h4>
          {node.id === 'generate_synthetic' || node.id === 'parse_synthetic' ? (
            <div className="bg-white rounded-lg p-4 max-h-64 overflow-auto">
              <div dangerouslySetInnerHTML={{ __html: node.result }} />
            </div>
          ) : node.id === 'generate_qa' ? (
            <div className="bg-gray-900 rounded-lg p-4 max-h-64 overflow-auto">
              <pre className="text-sm text-gray-300 whitespace-pre-wrap">{node.result}</pre>
            </div>
          ) : (
            <p className="text-sm text-gray-300">{node.result}</p>
          )}
        </div>
      )}
      
      {node.status === 'pending' && (
        <p className="text-sm text-gray-500 italic">아직 실행되지 않았습니다.</p>
      )}
    </div>
  );
};

export default PipelineDiagram;

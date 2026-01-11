import React, { useState, useCallback, useEffect, useRef } from 'react';
import { 
  Upload, 
  Play, 
  Pause, 
  RotateCcw, 
  X, 
  CheckCircle, 
  AlertCircle, 
  Clock,
  Loader2,
  FileImage,
  Table,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  Download
} from 'lucide-react';
import { 
  JobItem, 
  BatchJob, 
  PipelineResult, 
  WebSocketMessage,
  PipelineConfig
} from './types';
import { 
  uploadImages, 
  runPipeline, 
  getJobStatus, 
  pauseJob, 
  resumeJob, 
  retryFailed, 
  cancelJob,
  createWebSocket 
} from './api';
import PipelineDiagram, { PipelineNodeStates } from './components/PipelineDiagram';

// ============ Components ============

interface FileDropzoneProps {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
}

const FileDropzone: React.FC<FileDropzoneProps> = ({ onFilesSelected, disabled }) => {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    if (disabled) return;
    
    const files = Array.from(e.dataTransfer.files).filter(
      f => f.type.startsWith('image/') || f.name.endsWith('.png') || f.name.endsWith('.jpg')
    );
    if (files.length > 0) {
      onFilesSelected(files);
    }
  }, [onFilesSelected, disabled]);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragging(true);
  };

  const handleDragLeave = () => setIsDragging(false);

  const handleClick = () => {
    if (!disabled) inputRef.current?.click();
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      onFilesSelected(files);
    }
  };

  return (
    <div
      onClick={handleClick}
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      className={`
        border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all
        ${isDragging ? 'border-blue-500 bg-blue-500/10' : 'border-gray-600 hover:border-gray-500'}
        ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept="image/*"
        onChange={handleInputChange}
        className="hidden"
      />
      <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
      <p className="text-lg text-gray-300 mb-2">
        이미지 파일을 드래그하거나 클릭하여 선택
      </p>
      <p className="text-sm text-gray-500">
        PNG, JPG 파일 지원 (여러 파일 선택 가능)
      </p>
    </div>
  );
};

interface StatusBadgeProps {
  status: string;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const config: Record<string, { color: string; icon: React.ReactNode }> = {
    pending: { color: 'bg-gray-600', icon: <Clock className="w-3 h-3" /> },
    running: { color: 'bg-blue-600', icon: <Loader2 className="w-3 h-3 animate-spin" /> },
    completed: { color: 'bg-green-600', icon: <CheckCircle className="w-3 h-3" /> },
    failed: { color: 'bg-red-600', icon: <AlertCircle className="w-3 h-3" /> },
    paused: { color: 'bg-yellow-600', icon: <Pause className="w-3 h-3" /> },
    cancelled: { color: 'bg-gray-600', icon: <X className="w-3 h-3" /> },
  };

  const { color, icon } = config[status] || config.pending;

  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium text-white ${color}`}>
      {icon}
      {status}
    </span>
  );
};

interface ProgressBarProps {
  progress: number;
  status: string;
}

const ProgressBar: React.FC<ProgressBarProps> = ({ progress, status }) => {
  const color = status === 'failed' ? 'bg-red-500' : status === 'completed' ? 'bg-green-500' : 'bg-blue-500';
  
  return (
    <div className="w-full bg-gray-700 rounded-full h-2">
      <div
        className={`h-2 rounded-full transition-all duration-300 ${color}`}
        style={{ width: `${progress}%` }}
      />
    </div>
  );
};

interface JobItemCardProps {
  item: JobItem;
  onRetry?: (itemId: string) => void;
}

const JobItemCard: React.FC<JobItemCardProps> = ({ item, onRetry }) => {
  const [expanded, setExpanded] = useState(false);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  // JobItem의 node_states를 PipelineDiagram에서 사용하는 형식으로 변환
  const convertNodeStates = (): PipelineNodeStates => {
    if (!item.node_states) {
      // 기본 상태: 실행 중이면 첫 번째 노드 활성화
      const defaultState: PipelineNodeStates = {
        generate_synthetic: item.status === 'running' ? 'running' : item.status === 'completed' ? 'completed' : 'pending',
        self_reflection: 'pending',
        revise_synthetic: 'pending',
        parse_synthetic: item.status === 'completed' ? 'completed' : 'pending',
        generate_qa: item.status === 'completed' ? 'completed' : 'pending',
      };
      return defaultState;
    }

    // 백엔드에서 받은 node_states를 변환
    const result: PipelineNodeStates = {
      generate_synthetic: 'pending',
      self_reflection: 'pending',
      revise_synthetic: 'pending',
      parse_synthetic: 'pending',
      generate_qa: 'pending',
    };

    for (const [nodeId, state] of Object.entries(item.node_states)) {
      if (nodeId in result) {
        result[nodeId] = state.status as 'pending' | 'running' | 'completed' | 'failed' | 'skipped';
      }
    }

    return result;
  };

  const handleNodeClick = (nodeId: string) => {
    if (item.node_results && item.node_results[nodeId]) {
      setSelectedNode(selectedNode === nodeId ? null : nodeId);
    }
  };

  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      <div 
        className="p-4 flex items-center gap-4 cursor-pointer hover:bg-gray-750"
        onClick={() => setExpanded(!expanded)}
      >
        <FileImage className="w-8 h-8 text-gray-400 flex-shrink-0" />
        
        <div className="flex-grow min-w-0">
          <p className="text-sm font-medium text-white truncate">{item.image_name}</p>
          <ProgressBar progress={item.progress} status={item.status} />
        </div>
        
        <StatusBadge status={item.status} />
        
        {item.status === 'failed' && onRetry && (
          <button
            onClick={(e) => { e.stopPropagation(); onRetry(item.id); }}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg"
            title="재시도"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        )}
        
        {expanded ? <ChevronUp className="w-4 h-4 text-gray-400" /> : <ChevronDown className="w-4 h-4 text-gray-400" />}
      </div>
      
      {expanded && (
        <div className="border-t border-gray-700">
          {/* 파이프라인 다이어그램 */}
          <div className="p-4 bg-gray-800">
            <PipelineDiagram
              nodeStates={convertNodeStates()}
              currentNode={item.current_node}
              onNodeClick={handleNodeClick}
              animated={item.status === 'running'}
            />
          </div>

          {/* 선택된 노드 결과 표시 */}
          {selectedNode && item.node_results && item.node_results[selectedNode] && (
            <div className="border-t border-gray-700 p-4">
              <div className="flex items-center justify-between mb-2">
                <h4 className="text-sm font-medium text-blue-400">{selectedNode} 결과</h4>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-gray-400 hover:text-white"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="bg-gray-900 rounded-lg p-3 max-h-48 overflow-auto">
                <pre className="text-xs text-gray-300 whitespace-pre-wrap">
                  {(() => {
                    const result = item.node_results[selectedNode];
                    return typeof result === 'string' 
                      ? result 
                      : JSON.stringify(result, null, 2);
                  })()}
                </pre>
              </div>
            </div>
          )}

          {/* 최종 결과 탭 */}
          {item.result && (
            <div className="border-t border-gray-700 p-4">
              <ResultView result={item.result} />
            </div>
          )}
          
          {item.error && (
            <div className="border-t border-gray-700 p-4">
              <div className="bg-red-900/30 border border-red-700 rounded-lg p-3">
                <p className="text-red-400 text-sm">{item.error}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

interface ResultViewProps {
  result: PipelineResult;
}

const ResultView: React.FC<ResultViewProps> = ({ result }) => {
  const [activeTab, setActiveTab] = useState<'html' | 'synthetic' | 'qa'>('html');

  return (
    <div>
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setActiveTab('html')}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${
            activeTab === 'html' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          <Table className="w-4 h-4" />
          Parsed HTML
        </button>
        <button
          onClick={() => setActiveTab('synthetic')}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${
            activeTab === 'synthetic' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          <Table className="w-4 h-4" />
          Synthetic
        </button>
        <button
          onClick={() => setActiveTab('qa')}
          className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm ${
            activeTab === 'qa' ? 'bg-blue-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
          }`}
        >
          <MessageSquare className="w-4 h-4" />
          QA ({result.qa_results?.length || 0})
        </button>
      </div>

      {activeTab === 'html' && (
        <div className="bg-white rounded-lg p-4 overflow-auto max-h-64">
          <div dangerouslySetInnerHTML={{ __html: result.html_table || '<p>No HTML</p>' }} />
        </div>
      )}

      {activeTab === 'synthetic' && (
        <div className="bg-white rounded-lg p-4 overflow-auto max-h-64">
          <div dangerouslySetInnerHTML={{ __html: result.synthetic_table || '<p>No synthetic table</p>' }} />
        </div>
      )}

      {activeTab === 'qa' && (
        <div className="space-y-2 max-h-64 overflow-auto">
          {result.qa_results?.map((qa, idx) => (
            <div key={idx} className="bg-gray-900 rounded-lg p-3">
              <p className="text-blue-400 text-sm font-medium mb-1">Q: {qa.question}</p>
              <p className="text-green-400 text-sm">A: {qa.answer}</p>
            </div>
          )) || <p className="text-gray-500">No QA pairs</p>}
        </div>
      )}
    </div>
  );
};

// ============ Main App ============

const App: React.FC = () => {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [currentJob, setCurrentJob] = useState<BatchJob | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // WebSocket 연결
  useEffect(() => {
    if (!currentJob) return;

    const ws = createWebSocket(currentJob.id);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const message: WebSocketMessage = JSON.parse(event.data);
      handleWebSocketMessage(message);
    };

    ws.onclose = () => {
      // 재연결 로직 추가 가능
    };

    // Ping 보내기
    const pingInterval = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
      }
    }, 30000);

    return () => {
      clearInterval(pingInterval);
      ws.close();
    };
  }, [currentJob?.id]);

  const handleWebSocketMessage = (message: WebSocketMessage) => {
    if (!currentJob) return;

    setCurrentJob(prev => {
      if (!prev) return prev;
      
      const updatedItems = prev.items.map(item => {
        if (item.id !== message.item_id) return item;

        switch (message.type) {
          case 'item_start':
            return { 
              ...item, 
              status: 'running' as const, 
              progress: 10,
              node_states: message.nodes,
              node_results: message.node_results
            };
          case 'item_complete':
            return { 
              ...item, 
              status: 'completed' as const, 
              progress: 100, 
              result: message.result,
              node_states: message.nodes,
              node_results: message.node_results
            };
          case 'item_error':
            return { 
              ...item, 
              status: 'failed' as const, 
              progress: 100, 
              error: message.error,
              node_states: message.nodes,
              node_results: message.node_results
            };
          case 'progress':
            return { 
              ...item, 
              progress: message.progress || item.progress, 
              current_node: message.current_node,
              node_states: message.nodes || item.node_states,
              node_results: message.node_results || item.node_results
            };
          default:
            return item;
        }
      });

      const completed = updatedItems.filter(i => i.status === 'completed').length;
      const failed = updatedItems.filter(i => i.status === 'failed').length;
      const newStatus = completed + failed === prev.total 
        ? (failed === 0 ? 'completed' : 'failed')
        : prev.status;

      return { ...prev, items: updatedItems, completed, failed, status: newStatus };
    });
  };

  const handleFilesSelected = (files: File[]) => {
    setSelectedFiles(prev => [...prev, ...files]);
  };

  const handleRemoveFile = (index: number) => {
    setSelectedFiles(prev => prev.filter((_, i) => i !== index));
  };

  const handleStartPipeline = async () => {
    if (selectedFiles.length === 0) return;

    setIsUploading(true);
    setError(null);

    try {
      // 1. 파일 업로드
      const paths = await uploadImages(selectedFiles);

      // 2. 파이프라인 실행
      const config: PipelineConfig = {
        provider: 'gemini_pool',
        model: 'gemini-2.0-flash',
        temperature: 0.2,
      };
      
      const { job_id } = await runPipeline(paths, config);

      // 3. 상태 조회
      const job = await getJobStatus(job_id);
      setCurrentJob(job);
      setSelectedFiles([]);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start pipeline');
    } finally {
      setIsUploading(false);
    }
  };

  const handlePause = async () => {
    if (!currentJob) return;
    try {
      await pauseJob(currentJob.id);
      setCurrentJob(prev => prev ? { ...prev, status: 'paused' } : prev);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to pause');
    }
  };

  const handleResume = async () => {
    if (!currentJob) return;
    try {
      await resumeJob(currentJob.id);
      setCurrentJob(prev => prev ? { ...prev, status: 'running' } : prev);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resume');
    }
  };

  const handleRetryItem = async (itemId: string) => {
    if (!currentJob) return;
    try {
      await retryFailed(currentJob.id, [itemId]);
      // 상태 새로고침
      const job = await getJobStatus(currentJob.id);
      setCurrentJob(job);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retry');
    }
  };

  const handleRetryAll = async () => {
    if (!currentJob) return;
    try {
      await retryFailed(currentJob.id);
      const job = await getJobStatus(currentJob.id);
      setCurrentJob(job);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retry');
    }
  };

  const handleCancel = async () => {
    if (!currentJob) return;
    try {
      await cancelJob(currentJob.id);
      setCurrentJob(prev => prev ? { ...prev, status: 'cancelled' } : prev);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel');
    }
  };

  const handleNewJob = () => {
    setCurrentJob(null);
    setSelectedFiles([]);
    setError(null);
  };

  const handleDownloadResults = () => {
    if (!currentJob) return;
    
    const results = currentJob.items
      .filter(item => item.result)
      .map(item => ({
        image_name: item.image_name,
        ...item.result,
      }));
    
    const blob = new Blob([JSON.stringify(results, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `results_${currentJob.id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // 진행률 계산
  const overallProgress = currentJob 
    ? Math.round(((currentJob.completed + currentJob.failed) / currentJob.total) * 100)
    : 0;

  return (
    <div className="min-h-screen bg-gray-900 text-gray-100">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-teal-400 bg-clip-text text-transparent">
            TableMagnifier Pipeline UI
          </h1>
          {currentJob && (
            <button
              onClick={handleNewJob}
              className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm"
            >
              <Upload className="w-4 h-4" />
              새 작업
            </button>
          )}
        </div>
      </header>

      <main className="max-w-6xl mx-auto p-6">
        {error && (
          <div className="mb-6 bg-red-900/30 border border-red-700 rounded-lg p-4 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <p className="text-red-400">{error}</p>
            <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-300">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {!currentJob ? (
          // 업로드 뷰
          <div className="space-y-6">
            <FileDropzone onFilesSelected={handleFilesSelected} disabled={isUploading} />

            {selectedFiles.length > 0 && (
              <div className="bg-gray-800 rounded-xl border border-gray-700 p-4">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-medium">선택된 파일 ({selectedFiles.length})</h2>
                  <button
                    onClick={() => setSelectedFiles([])}
                    className="text-sm text-gray-400 hover:text-white"
                  >
                    전체 삭제
                  </button>
                </div>
                
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
                  {selectedFiles.map((file, idx) => (
                    <div key={idx} className="relative group bg-gray-700 rounded-lg p-2">
                      <img
                        src={URL.createObjectURL(file)}
                        alt={file.name}
                        className="w-full h-24 object-cover rounded"
                      />
                      <p className="text-xs text-gray-400 mt-1 truncate">{file.name}</p>
                      <button
                        onClick={() => handleRemoveFile(idx)}
                        className="absolute -top-2 -right-2 p-1 bg-red-600 rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                      >
                        <X className="w-3 h-3" />
                      </button>
                    </div>
                  ))}
                </div>

                <button
                  onClick={handleStartPipeline}
                  disabled={isUploading}
                  className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg font-medium transition-colors"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      업로드 중...
                    </>
                  ) : (
                    <>
                      <Play className="w-5 h-5" />
                      파이프라인 실행 ({selectedFiles.length}개 이미지)
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        ) : (
          // 작업 진행 뷰
          <div className="space-y-6">
            {/* 진행 상태 헤더 */}
            <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-lg font-medium">작업 #{currentJob.id}</h2>
                  <p className="text-sm text-gray-400">
                    {currentJob.completed} / {currentJob.total} 완료
                    {currentJob.failed > 0 && ` (${currentJob.failed} 실패)`}
                  </p>
                </div>
                <StatusBadge status={currentJob.status} />
              </div>

              <ProgressBar progress={overallProgress} status={currentJob.status} />

              <div className="flex gap-3 mt-4">
                {currentJob.status === 'running' && (
                  <button
                    onClick={handlePause}
                    className="flex items-center gap-2 px-4 py-2 bg-yellow-600 hover:bg-yellow-700 rounded-lg text-sm"
                  >
                    <Pause className="w-4 h-4" />
                    일시정지
                  </button>
                )}
                
                {currentJob.status === 'paused' && (
                  <button
                    onClick={handleResume}
                    className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg text-sm"
                  >
                    <Play className="w-4 h-4" />
                    재개
                  </button>
                )}

                {currentJob.failed > 0 && (currentJob.status === 'completed' || currentJob.status === 'failed') && (
                  <button
                    onClick={handleRetryAll}
                    className="flex items-center gap-2 px-4 py-2 bg-orange-600 hover:bg-orange-700 rounded-lg text-sm"
                  >
                    <RotateCcw className="w-4 h-4" />
                    실패 항목 재시도 ({currentJob.failed})
                  </button>
                )}

                {currentJob.status === 'running' && (
                  <button
                    onClick={handleCancel}
                    className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 rounded-lg text-sm"
                  >
                    <X className="w-4 h-4" />
                    취소
                  </button>
                )}

                {currentJob.completed > 0 && (
                  <button
                    onClick={handleDownloadResults}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 rounded-lg text-sm ml-auto"
                  >
                    <Download className="w-4 h-4" />
                    결과 다운로드
                  </button>
                )}
              </div>
            </div>

            {/* 개별 항목 목록 */}
            <div className="space-y-3">
              {currentJob.items.map(item => (
                <JobItemCard 
                  key={item.id} 
                  item={item} 
                  onRetry={handleRetryItem}
                />
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
};

export default App;

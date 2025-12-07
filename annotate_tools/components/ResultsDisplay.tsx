
import React, { useState } from 'react';
import type { AnalysisResult } from '../types';

interface ResultsDisplayProps {
  result: AnalysisResult;
}

const ResultsDisplay: React.FC<ResultsDisplayProps> = ({ result }) => {
  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h2 className="text-2xl font-bold text-blue-300 mb-4">OCR Result</h2>
        <div className="bg-gray-950 p-4 rounded-lg border border-gray-700 max-h-96 overflow-y-auto">
          <pre className="text-gray-300 whitespace-pre-wrap font-mono text-sm">{result.ocrResult}</pre>
        </div>
      </div>
      <div>
        <h2 className="text-2xl font-bold text-blue-300 mb-4">Generated Q&A</h2>
        <div className="space-y-4">
          {result.qaSet.map((item, index) => (
            <QAItem key={index} question={item.question} answer={item.answer} />
          ))}
        </div>
      </div>
    </div>
  );
};

const QAItem: React.FC<{ question: string; answer: string }> = ({ question, answer }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="border border-gray-700 bg-gray-800/50 rounded-lg overflow-hidden">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex justify-between items-center p-4 text-left"
      >
        <h3 className="font-semibold text-gray-100">{question}</h3>
        <svg
          className={`w-5 h-5 text-gray-400 transform transition-transform ${isOpen ? 'rotate-180' : ''}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>
      {isOpen && (
        <div className="p-4 border-t border-gray-700 bg-gray-900/50">
          <p className="text-gray-300">{answer}</p>
        </div>
      )}
    </div>
  );
};

export default ResultsDisplay;

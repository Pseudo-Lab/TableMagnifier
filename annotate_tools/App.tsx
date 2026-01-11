import React, { useState, useEffect } from 'react';
import { TableGenerationResult } from './types';

// Changed API Port to 8001 (Pipeline UI Backend)
const API_BASE_URL = 'http://localhost:8001/api';

const App: React.FC = () => {
  const [data, setData] = useState<TableGenerationResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [jsonInput, setJsonInput] = useState<string>('');
  const [qaInput, setQaInput] = useState<string>('');
  const [saveStatus, setSaveStatus] = useState<string | null>(null);
  const [dbStatus, setDbStatus] = useState<string | null>(null);
  const [showDbModal, setShowDbModal] = useState<boolean>(false);
  const [dbPassword, setDbPassword] = useState<string>('');
  const [collectionName, setCollectionName] = useState<string>('Public');
  const [itemId, setItemId] = useState<string | null>(null);

  useEffect(() => {
    // Get ID from URL
    const params = new URLSearchParams(window.location.search);
    const id = params.get('id');
    setItemId(id);
    if (!id) {
      setError("No Item ID provided in URL (e.g. ?id=xyz)");
    } else {
      fetchData(id);
    }
  }, []);

  const fetchData = async (id: string) => {
    setIsLoading(true);
    setError(null);
    try {
      // Changed endpoint to /api/annotate/data/{id}
      const response = await fetch(`${API_BASE_URL}/annotate/data/${id}`);
      if (!response.ok) {
        throw new Error(`Failed to fetch data: ${response.statusText}`);
      }
      const result: TableGenerationResult = await response.json();
      setData(result);
      setJsonInput(JSON.stringify(result.synthetic_json, null, 2));
      setQaInput(JSON.stringify(result.qa_results, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An unknown error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    setSaveStatus('Saving...');
    try {
      const parsedJson = JSON.parse(jsonInput);
      const parsedQa = JSON.parse(qaInput);

      if (!itemId) throw new Error("No Item ID");

      // Changed endpoint to /api/annotate/save/{id}
      const response = await fetch(`${API_BASE_URL}/annotate/save/${itemId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          synthetic_json: parsedJson,
          qa_results: parsedQa
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to save data');
      }

      setSaveStatus('Saved successfully!');
      setTimeout(() => setSaveStatus(null), 3000);

      // Refresh data to ensure sync
      // fetchData(); 
    } catch (err) {
      setSaveStatus('Error saving data');
      setError(err instanceof Error ? err.message : 'Invalid JSON or server error');
    }
  };

  const handleSaveToDb = async () => {
    setDbStatus('Saving to DB...');
    try {
      if (!itemId) throw new Error("No Item ID");

      // Changed endpoint to /api/annotate/save_to_db/{id}
      const response = await fetch(`${API_BASE_URL}/annotate/save_to_db/${itemId}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          collection_name: collectionName,
          password: dbPassword || undefined // Only send if set
        }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to save to DB');
      }

      setDbStatus('Saved to DB successfully!');
      setTimeout(() => setDbStatus(null), 3000);
      setShowDbModal(false);
    } catch (err) {
      setDbStatus('Error saving to DB');
      alert(err instanceof Error ? err.message : 'Unknown DB Error');
    }
  };

  const getImageUrl = (path: string) => {
    // Assuming path is relative or absolute, we need to convert it to a static URL served by backend
    // Backend serves static files from BASE_DIR at /static
    // If path is absolute /home/ssh/..., we need to strip BASE_DIR
    // But for simplicity, let's assume the backend handles it or we just show the path for now if it's tricky.
    // Actually, let's try to construct a relative path if possible.
    // If path starts with /, it's absolute.

    // Quick hack: just use the filename if it's in the same dir
    const filename = path.split('/').pop();
    // Use :8001 for images (Pipeline Backend)
    return `http://localhost:8001/output/${filename}`;
  };

  if (isLoading && !data) {
    return <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">Loading...</div>;
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-900 text-white flex flex-col items-center justify-center p-4">
        <div className="text-red-500 text-xl mb-4">Error: {error}</div>
        <button onClick={() => itemId && fetchData(itemId)} className="bg-blue-600 px-4 py-2 rounded">Retry</button>
      </div>
    );
  }

  if (!data) {
    return <div className="min-h-screen bg-gray-900 text-white flex items-center justify-center">No data found. Check the ID in URL.</div>;
  }

  return (
    <div className="min-h-screen bg-gray-900 text-gray-200 font-sans p-4 sm:p-6 md:p-8">
      <div className="max-w-7xl mx-auto">
        <header className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-teal-300">
            Table Generation Review
          </h1>
          <div className="flex items-center space-x-4">
            {saveStatus && <span className={saveStatus.includes('Error') ? 'text-red-400' : 'text-green-400'}>{saveStatus}</span>}
            {dbStatus && <span className={dbStatus.includes('Error') ? 'text-red-400' : 'text-green-400'}>{dbStatus}</span>}
            <button
              onClick={() => setShowDbModal(true)}
              className="bg-teal-600 hover:bg-teal-700 text-white font-bold py-2 px-6 rounded-lg transition-colors"
            >
              Save to DB
            </button>
            <button
              onClick={handleSave}
              className="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded-lg transition-colors"
            >
              Save Changes
            </button>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column: Visuals */}
          <div className="space-y-8 lg:col-span-1">

            {/* Original Image */}
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
              <h2 className="text-xl font-bold text-teal-300 mb-4">Original Image</h2>
              <div className="flex justify-center bg-gray-900 p-4 rounded-lg">
                <img
                  src={getImageUrl(data.image_path)}
                  alt="Original Table"
                  className="max-h-96 object-contain"
                  onError={(e) => {
                    (e.target as HTMLImageElement).style.display = 'none';
                    (e.target as HTMLImageElement).parentElement!.innerHTML += `<p class="text-red-400">Image not found at ${data.image_path}</p>`;
                  }}
                />
              </div>
              <p className="text-xs text-gray-500 mt-2 break-all">{data.image_path}</p>
            </div>

            {/* Parsed HTML */}
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
              <h2 className="text-xl font-bold text-teal-300 mb-4">Parsed HTML (Structure)</h2>
              <div className="bg-white text-black p-4 rounded-lg overflow-auto max-h-96" dangerouslySetInnerHTML={{ __html: data.html_table }} />
            </div>

            {/* Synthetic HTML */}
            <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
              <h2 className="text-xl font-bold text-teal-300 mb-4">Synthetic HTML (Preview)</h2>
              <div className="bg-white text-black p-4 rounded-lg overflow-auto max-h-96" dangerouslySetInnerHTML={{ __html: data.synthetic_table }} />
            </div>

          </div>

          {/* Middle Column: JSON Editor */}
          <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 flex flex-col h-full lg:col-span-1">
            <h2 className="text-xl font-bold text-teal-300 mb-4">Synthetic JSON (Editable)</h2>
            <textarea
              value={jsonInput}
              onChange={(e) => setJsonInput(e.target.value)}
              className="flex-grow w-full bg-gray-900 border border-gray-600 text-gray-200 font-mono text-sm p-4 rounded-lg focus:ring-blue-500 focus:border-blue-500 min-h-[600px]"
            />
          </div>

          {/* Right Column: QA Editor */}
          <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 flex flex-col h-full lg:col-span-1">
            <h2 className="text-xl font-bold text-teal-300 mb-4">QA Pairs (Editable)</h2>
            <textarea
              value={qaInput}
              onChange={(e) => setQaInput(e.target.value)}
              className="flex-grow w-full bg-gray-900 border border-gray-600 text-gray-200 font-mono text-sm p-4 rounded-lg focus:ring-blue-500 focus:border-blue-500 min-h-[600px]"
            />
          </div>
        </div>
      </div>

      {showDbModal && (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50">
          <div className="bg-gray-800 p-8 rounded-xl border border-gray-700 max-w-md w-full">
            <h2 className="text-2xl font-bold text-white mb-6">Save to MongoDB</h2>

            <div className="mb-4">
              <label className="block text-gray-400 mb-2">Collection Name (Domain)</label>
              <select
                value={collectionName}
                onChange={(e) => setCollectionName(e.target.value)}
                className="w-full bg-gray-900 border border-gray-600 text-white p-3 rounded-lg"
              >
                <option value="Academic">Academic</option>
                <option value="Business">Business</option>
                <option value="Finance">Finance</option>
                <option value="Insurance">Insurance</option>
                <option value="Medical">Medical</option>
                <option value="Public">Public</option>
              </select>
            </div>

            <div className="mb-6">
              <label className="block text-gray-400 mb-2">DB Password (Optional if env set)</label>
              <input
                type="password"
                value={dbPassword}
                onChange={(e) => setDbPassword(e.target.value)}
                placeholder="Enter MongoDB Password"
                className="w-full bg-gray-900 border border-gray-600 text-white p-3 rounded-lg"
              />
            </div>

            <div className="flex justify-end space-x-4">
              <button
                onClick={() => setShowDbModal(false)}
                className="px-4 py-2 text-gray-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={handleSaveToDb}
                className="px-6 py-2 bg-teal-600 hover:bg-teal-700 text-white rounded-lg font-bold"
              >
                Confirm Save
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default App;

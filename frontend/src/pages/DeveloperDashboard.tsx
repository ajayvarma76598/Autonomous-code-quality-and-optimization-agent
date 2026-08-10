import React, { useState, useEffect } from 'react';
import { Send, Terminal, HardDrive, MessageSquare, Plus, Loader2, Database, Trash2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const INGESTION_STEPS = [
  "Cloning repository from source...",
  "Parsing Abstract Syntax Trees (AST)...",
  "Chunking code files into semantic blocks...",
  "Generating vector embeddings...",
  "Running SonarQube static analysis...",
  "Finalizing architectural index..."
];

const DeveloperDashboard = () => {
  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  const [query, setQuery] = useState('');
  const [repoPath, setRepoPath] = useState('');
  const [ingesting, setIngesting] = useState(false);
  const [ingestionStep, setIngestionStep] = useState(0);
  const [messages, setMessages] = useState<{ role: 'user' | 'assistant', content: string }[]>([
    { role: 'assistant', content: 'Hello! I am your AI architect. What would you like to know about your codebase today?' }
  ]);
  const [loading, setLoading] = useState(false);

  // New state
  const [sessions, setSessions] = useState<any[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [availableRepos, setAvailableRepos] = useState<any[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string>('');
  const [repoSnapshots, setRepoSnapshots] = useState<any[]>([]);
  const [selectedSnapshotId, setSelectedSnapshotId] = useState<string>('');

  const { getToken } = useAuth();

  const getHeaders = async (additional: Record<string, string> = {}) => {
    const token = await getToken();
    return {
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...additional
    };
  };

  useEffect(() => {
    fetchSessions();
    fetchRepos();
  }, []);

  const fetchSessions = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/sessions/`, {
        headers: await getHeaders()
      });
      if (res.ok) setSessions(await res.json());
    } catch (err) { console.error(err); }
  };

  const fetchRepos = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/repositories/`, {
        headers: await getHeaders()
      });
      if (res.ok) {
        const repos = await res.json();
        setAvailableRepos(repos);
        if (repos.length > 0 && !selectedRepoId) {
          setSelectedRepoId(repos[0].repository_id);
        }
      }
    } catch (err) { console.error(err); }
  };

  useEffect(() => {
    const fetchSnapshots = async () => {
      if (!selectedRepoId) {
        setRepoSnapshots([]);
        setSelectedSnapshotId('');
        return;
      }
      try {
        const res = await fetch(`${API_URL}/api/v1/repositories/${selectedRepoId}/snapshots`, {
          headers: await getHeaders()
        });
        if (res.ok) {
          const snaps = await res.json();
          setRepoSnapshots(snaps);
          if (snaps.length > 0) {
            setSelectedSnapshotId(snaps[0].snapshot_id);
          } else {
            setSelectedSnapshotId('');
          }
        }
      } catch (err) { console.error(err); }
    };
    fetchSnapshots();
  }, [selectedRepoId]);

  useEffect(() => {
    let interval: ReturnType<typeof setInterval>;
    if (ingesting) {
      setIngestionStep(0);
      interval = setInterval(() => {
        setIngestionStep(prev => (prev < INGESTION_STEPS.length - 1 ? prev + 1 : prev));
      }, 2500);
    }
    return () => clearInterval(interval);
  }, [ingesting]);

  const handleIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoPath) return;
    setIngesting(true);
    try {
      const response = await fetch(`${API_URL}/api/v1/ingestion/trigger`, {
        method: 'POST',
        headers: await getHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ repo_path: repoPath, project_key: "default-project" })
      });
      if (response.ok) {
        alert('Repository ingestion triggered successfully!');
        fetchRepos(); // Refresh repos
      } else {
        alert('Failed to trigger ingestion.');
      }
    } catch (err) {
      console.error(err);
      alert('Network error triggering ingestion.');
    } finally {
      setIngesting(false);
    }
  };

  const handleSelectSession = async (id: string) => {
    setActiveSessionId(id);
    try {
      const res = await fetch(`${API_URL}/api/v1/sessions/${id}/history`, {
        headers: await getHeaders()
      });
      if (res.ok) {
        const history = await res.json();
        const newMessages = [{ role: 'assistant', content: 'Hello! I am your AI architect. What would you like to know about your codebase today?' }];
        [...history].reverse().forEach((q: any) => {
          newMessages.push({ role: 'user', content: q.user_query });
          if (q.assistant_response) newMessages.push({ role: 'assistant', content: q.assistant_response });
        });
        setMessages(newMessages as any);
      }
    } catch (err) { console.error(err); }
  };

  const handleDeleteSession = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    try {
      await fetch(`${API_URL}/api/v1/sessions/${id}`, { 
        method: 'DELETE',
        headers: await getHeaders()
      });
      if (activeSessionId === id) {
        setActiveSessionId(null);
        setMessages([{ role: 'assistant', content: 'Hello! I am your AI architect. What would you like to know about your codebase today?' }]);
      }
      fetchSessions();
    } catch (err) { console.error(err); }
  };

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query) return;

    const currentQuery = query;
    setMessages(prev => [...prev, { role: 'user', content: currentQuery }]);
    setQuery('');
    setLoading(true);

    let sessionIdToUse = activeSessionId;
    if (!sessionIdToUse) {
      if (!selectedRepoId) {
        alert('Please select a repository first.');
        setLoading(false);
        setMessages(prev => prev.slice(0, -1));
        setQuery(currentQuery);
        return;
      }
      const repo = availableRepos.find(r => r.repository_id === selectedRepoId);
      try {
        const res = await fetch(`${API_URL}/api/v1/sessions/`, {
          method: 'POST',
          headers: await getHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({
            session_name: currentQuery.substring(0, 30) + (currentQuery.length > 30 ? '...' : ''),
            user_id: repo?.user_id,
            repository_id: selectedRepoId
          })
        });
        if (res.ok) {
          const newSession = await res.json();
          sessionIdToUse = newSession.session_id;
          setActiveSessionId(newSession.session_id);
          fetchSessions();
        } else {
          throw new Error("Failed to create session");
        }
      } catch (err) {
        console.error(err);
        setLoading(false);
        return;
      }
    }

    try {
      const response = await fetch(`${API_URL}/api/v1/query/stream`, {
        method: 'POST',
        headers: await getHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ 
          query: currentQuery, 
          session_id: sessionIdToUse,
          snapshot_id: selectedSnapshotId || undefined
        })
      });

      if (!response.body) throw new Error('ReadableStream not yet supported in this browser.');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let assistantMsg = '';

      // Add a placeholder message for the assistant
      setMessages(prev => [...prev, { role: 'assistant', content: '' }]);

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]' || data.includes('"status": "done"')) break;
            try {
              const parsed = JSON.parse(data);
              
              if (parsed.node && !parsed.is_final) {
                assistantMsg = `> Working on: ${parsed.node}...`;
                setMessages(prev => {
                  const newMsgs = [...prev];
                  newMsgs[newMsgs.length - 1].content = assistantMsg;
                  return newMsgs;
                });
              } else if (parsed.is_final && parsed.final_response) {
                const finalStr = parsed.final_response;
                assistantMsg = "";
                
                setMessages(prev => {
                  const newMsgs = [...prev];
                  newMsgs[newMsgs.length - 1].content = assistantMsg;
                  return newMsgs;
                });
                
                // Simulate stream
                const chunkSize = 3;
                for (let i = 0; i < finalStr.length; i += chunkSize) {
                  assistantMsg += finalStr.substring(i, i + chunkSize);
                  setMessages(prev => {
                    const newMsgs = [...prev];
                    newMsgs[newMsgs.length - 1].content = assistantMsg;
                    return newMsgs;
                  });
                  await new Promise(r => setTimeout(r, 10)); // tiny delay for visual stream effect
                }
                
                assistantMsg = finalStr;
                setMessages(prev => {
                  const newMsgs = [...prev];
                  newMsgs[newMsgs.length - 1].content = assistantMsg;
                  return newMsgs;
                });
                
                fetchSessions(); // Refresh session name/last activity if backend updated it
              } else if (parsed.status === 'error' || parsed.message) {
                assistantMsg += '\n\n[Error: ' + (parsed.message || "Unknown error") + ']';
              }
            } catch (e) { }
          }
        }
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, there was an error connecting to the AI.' }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)] gap-6">

      {/* Header section with Ingestion */}
      <div className="bg-white p-6 rounded-xl border border-gray-100 shadow-sm flex items-center justify-between animate-slide-up">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Developer Workspace</h1>
          <p className="text-gray-500 mt-1">Ingest repositories and run AI analysis</p>
        </div>

        <form onSubmit={handleIngest} className="flex gap-2">
          <div className="relative">
            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <HardDrive size={16} className="text-gray-400" />
            </div>
            <input
              type="text"
              placeholder="Public Git HTTP URL"
              className="pl-10 pr-4 py-2 bg-gray-50 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-skyblue-500 focus:border-transparent text-sm w-64 transition-all"
              value={repoPath}
              onChange={e => setRepoPath(e.target.value)}
            />
          </div>
          <button
            type="submit"
            disabled={ingesting || !repoPath}
            className="px-4 py-2 bg-black text-white text-sm font-medium rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-70 flex items-center gap-2"
          >
            {ingesting ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />}
            Ingest
          </button>
        </form>
      </div>

      {/* Main Workspace */}
      <div className="flex-1 grid grid-cols-4 gap-6 min-h-0 animate-slide-up" style={{ animationDelay: '100ms' }}>

        {/* Sessions Sidebar */}
        <div className="col-span-1 bg-white border border-gray-100 rounded-xl shadow-sm p-4 flex flex-col">
          <div className="flex items-center gap-2 mb-4 text-sm font-semibold text-gray-700">
            <Terminal size={16} className="text-skyblue-500" />
            Recent Sessions
          </div>
          <div className="space-y-2 flex-1 overflow-y-auto pr-2">
            {sessions.length === 0 ? (
              <div className="text-xs text-gray-400 text-center mt-4">No sessions found.</div>
            ) : (
              sessions.map(s => (
                <div 
                  key={s.session_id} 
                  onClick={() => handleSelectSession(s.session_id)}
                  className={`group flex items-center justify-between p-3 rounded-lg text-sm cursor-pointer transition-colors ${activeSessionId === s.session_id ? 'bg-skyblue-50 border border-skyblue-100 text-skyblue-800 font-medium' : 'hover:bg-gray-50 border border-transparent text-gray-600'}`}
                >
                  <div className="overflow-hidden">
                    <div className="truncate">{s.session_name || "New Chat"}</div>
                    <div className="text-xs text-gray-400 mt-1 font-normal truncate">
                      {new Date(s.created_at).toLocaleString()}
                    </div>
                  </div>
                  <button
                    onClick={(e) => handleDeleteSession(e, s.session_id)}
                    className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md opacity-0 group-hover:opacity-100 transition-all"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Chat UI */}
        <div className="col-span-3 bg-white border border-gray-100 rounded-xl shadow-sm flex flex-col overflow-hidden relative">

          {ingesting && (
            <div className="absolute inset-0 bg-white/90 backdrop-blur-[2px] z-20 flex flex-col items-center justify-center animate-fade-in">
              <div className="w-16 h-16 rounded-2xl bg-skyblue-50 flex items-center justify-center mb-6">
                <Database size={32} className="text-skyblue-500 animate-pulse" />
              </div>
              <h2 className="text-2xl font-bold tracking-tight mb-2">Ingesting Repository</h2>
              <div className="flex items-center gap-3 text-gray-600 font-medium">
                <Loader2 size={18} className="animate-spin text-skyblue-500" />
                <span>{INGESTION_STEPS[ingestionStep]}</span>
              </div>
            </div>
          )}

          <div className="border-b border-gray-100 p-4 bg-gray-50/50 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <MessageSquare size={16} className="text-skyblue-500" />
              <span className="font-semibold text-sm">AI Agent Chat</span>
            </div>

            <div className="flex items-center gap-3">
              <select 
                value={selectedRepoId} 
                onChange={e => setSelectedRepoId(e.target.value)}
                className="text-xs bg-white border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:border-skyblue-500"
                disabled={!!activeSessionId}
                title={activeSessionId ? "Repository is locked for an active session" : ""}
              >
                <option value="" disabled>Select Repository</option>
                {availableRepos.map(r => (
                  <option key={r.repository_id} value={r.repository_id}>{r.name}</option>
                ))}
              </select>

              <select 
                value={selectedSnapshotId} 
                onChange={e => setSelectedSnapshotId(e.target.value)}
                className="text-xs bg-white border border-gray-200 rounded-md px-2 py-1 focus:outline-none focus:border-skyblue-500"
              >
                <option value="">Latest Snapshot</option>
                {repoSnapshots.map(s => (
                  <option key={s.snapshot_id} value={s.snapshot_id}>
                    {s.commit_hash ? s.commit_hash.substring(0, 7) : s.snapshot_id.substring(0, 7)} - {new Date(s.indexed_at).toLocaleDateString()}
                  </option>
                ))}
              </select>

              {activeSessionId && (
                <button
                  onClick={() => {
                    setActiveSessionId(null);
                    setMessages([{ role: 'assistant', content: 'Hello! I am your AI architect. What would you like to know about your codebase today?' }]);
                  }}
                  className="text-xs font-medium text-gray-500 hover:text-black flex items-center gap-1 ml-2 pl-3 border-l border-gray-300"
                >
                  <Plus size={14} /> New Chat
                </button>
              )}
            </div>
          </div>

          <div className="flex-1 p-6 overflow-y-auto flex flex-col gap-6">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[80%] rounded-2xl p-4 text-sm leading-relaxed overflow-x-auto ${msg.role === 'user'
                    ? 'bg-black text-white rounded-br-sm'
                    : 'bg-gray-50 border border-gray-100 text-gray-800 rounded-bl-sm prose prose-sm prose-blue'
                  }`}>
                  {msg.role === 'user' ? (
                    msg.content
                  ) : (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  )}
                </div>
              </div>
            ))}
            {loading && messages[messages.length - 1]?.role === 'user' && (
              <div className="flex justify-start">
                <div className="max-w-[80%] rounded-2xl p-4 bg-gray-50 border border-gray-100 rounded-bl-sm flex items-center gap-2 text-sm text-gray-500">
                  <Loader2 size={14} className="animate-spin text-skyblue-500" />
                  Agent is thinking...
                </div>
              </div>
            )}
          </div>

          <div className="p-4 bg-white border-t border-gray-100">
            <form onSubmit={handleQuery} className="relative">
              <input
                type="text"
                placeholder="Ask about architecture, coverage, or performance..."
                className="w-full pl-4 pr-12 py-3 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-skyblue-500/50 focus:border-skyblue-500 transition-all"
                value={query}
                onChange={e => setQuery(e.target.value)}
              />
              <button
                type="submit"
                disabled={!query || loading}
                className="absolute right-2 top-2 p-1.5 bg-skyblue-500 text-white rounded-lg hover:bg-skyblue-600 transition-colors disabled:opacity-50"
              >
                <Send size={16} />
              </button>
            </form>
          </div>
        </div>

      </div>
    </div>
  );
};

export default DeveloperDashboard;

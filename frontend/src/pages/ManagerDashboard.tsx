import React, { useState, useEffect } from 'react';
import { AlertTriangle, Check, X, BarChart3, Activity, ShieldAlert, Trash2, Folder, Clock } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const ManagerDashboard = () => {
  const API_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');
  const WS_URL = API_URL.replace(/^http/, 'ws');
  const [escalations, setEscalations] = useState<any[]>([]);
  const [repositories, setRepositories] = useState<any[]>([]);
  const [snapshots, setSnapshots] = useState<{ [repoId: string]: any[] }>({});
  
  const [metrics, setMetrics] = useState<any>(null);
  const [loadingMetrics, setLoadingMetrics] = useState(true);

  const { getToken } = useAuth();

  const getHeaders = async (additional: Record<string, string> = {}) => {
    const token = await getToken();
    return {
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...additional
    };
  };

  const fetchRepos = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/repositories/`, {
        headers: await getHeaders()
      });
      if (res.ok) setRepositories(await res.json());
    } catch(err) { console.error(err); }
  };

  const fetchMetrics = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/metrics`, {
        headers: await getHeaders()
      });
      if (res.ok) {
        const data = await res.json();
        setMetrics(data);
      }
    } catch (err) {
      console.error("Failed to fetch metrics", err);
    } finally {
      setLoadingMetrics(false);
    }
  };

  const fetchPendingEscalations = async () => {
    try {
      const res = await fetch(`${API_URL}/api/v1/escalation/pending`, {
        headers: await getHeaders()
      });
      if (res.ok) {
        const data = await res.json();
        setEscalations(data);
      }
    } catch (err) {
      console.error("Failed to fetch pending escalations", err);
    }
  };

  useEffect(() => {
    fetchRepos();
    fetchMetrics();
    fetchPendingEscalations();

    // Connect to WebSocket for real-time escalations with auto-reconnect
    let ws: WebSocket;
    let reconnectTimer: ReturnType<typeof setTimeout>;

    const connectWebSocket = () => {
      ws = new WebSocket(`${WS_URL}/api/v1/escalation/ws`);
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'ESCALATION') {
          // Immediately load fresh data once triggered
          fetchPendingEscalations();
          fetchMetrics();
        }
      };

      ws.onclose = () => {
        // Auto-reconnect after 2 seconds
        reconnectTimer = setTimeout(() => {
          connectWebSocket();
        }, 2000);
      };
    };

    connectWebSocket();

    return () => {
      clearTimeout(reconnectTimer);
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      } else {
        ws.addEventListener('open', () => ws.close());
      }
    };
  }, []);

  const handleResolve = async (sessionId: string, action: 'APPROVE' | 'REJECT') => {
    // Optimistic UI update: immediately remove the escalation to load the new state
    setEscalations(prev => prev.filter(e => e.session_id !== sessionId));
    try {
      await fetch(`${API_URL}/api/v1/escalation/resolve`, {
        method: 'POST',
        headers: await getHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ session_id: sessionId, action, feedback: 'Resolved by manager.' })
      });
      // Refetch metrics as they may have been updated after the escalation was resolved
      fetchMetrics();
    } catch (err) {
      console.error("Failed to resolve escalation", err);
      // Rollback on error
      fetchPendingEscalations();
    }
  };


  const handleDeleteRepo = async (id: string) => {
    if (!window.confirm("Are you sure you want to delete this repository? This cannot be undone.")) return;
    try {
      const res = await fetch(`${API_URL}/api/v1/repositories/${id}`, { 
        method: 'DELETE',
        headers: await getHeaders()
      });
      if (res.ok) {
        setRepositories(prev => prev.filter(r => r.repository_id !== id));
        setSnapshots(prev => {
          const newSnaps = {...prev};
          delete newSnaps[id];
          return newSnaps;
        });
      }
    } catch (err) { console.error(err); }
  };

  const handleViewSnapshots = async (id: string) => {
    if (snapshots[id]) {
      // toggle off
      setSnapshots(prev => {
        const newSnaps = {...prev};
        delete newSnaps[id];
        return newSnaps;
      });
      return;
    }
    try {
      const res = await fetch(`${API_URL}/api/v1/repositories/${id}/snapshots`, {
        headers: await getHeaders()
      });
      if (res.ok) {
        const data = await res.json();
        setSnapshots(prev => ({...prev, [id]: data}));
      }
    } catch(err) { console.error(err); }
  };

  return (
    <div className="flex flex-col gap-8 animate-fade-in pb-8">
      
      <div>
        <h1 className="text-3xl font-bold tracking-tight">System Analytics</h1>
        <p className="text-gray-500 mt-1">Real-time code quality and agent oversight</p>
      </div>

      {/* Analytics Cards */}
      {loadingMetrics ? (
        <div className="flex items-center justify-center h-32">
          <p className="text-gray-500">Loading metrics...</p>
        </div>
      ) : (
        <div className="grid grid-cols-4 gap-6">
          {[
            { label: 'Task Success Rate', value: metrics?.summary?.task_success_rate !== undefined ? `${metrics.summary.task_success_rate.toFixed(1)}%` : '0%', icon: <Check className="text-skyblue-500" /> },
            { label: 'LLM Confidence', value: metrics?.summary?.llm_confidence !== undefined ? `${(metrics.summary.llm_confidence * 100).toFixed(1)}%` : '0%', icon: <ShieldAlert className="text-green-500" /> },
            { label: 'Avg Latency (ms)', value: metrics?.summary?.latency_ms !== undefined ? Math.round(metrics.summary.latency_ms) : '0', icon: <Activity className="text-amber-500" /> },
            { label: 'Total Queries', value: metrics?.summary?.total_queries !== undefined ? metrics.summary.total_queries : '0', icon: <BarChart3 className="text-purple-500" /> },
          ].map((stat, i) => (
            <div key={i} className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex flex-col hover:shadow-md transition-shadow">
              <div className="flex justify-between items-start mb-4">
                <div className="p-2 bg-gray-50 rounded-lg">{stat.icon}</div>
              </div>
              <div className="text-3xl font-bold mb-1">{stat.value}</div>
              <div className="text-sm font-medium text-gray-500">{stat.label}</div>
            </div>
          ))}
        </div>
      )}

      <div className="grid grid-cols-2 gap-6">
        {/* Chart */}
        <div className="col-span-1 bg-white p-6 rounded-2xl border border-gray-100 shadow-sm">
          <h2 className="text-lg font-bold mb-6">Query Analytics</h2>
          <div className="h-64 w-full">
            {loadingMetrics ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-gray-500">Loading chart...</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={(metrics?.timeseries || []).map((t: any) => ({
                  ...t,
                  failures: Math.round((t.queries || 0) * Math.max(0, 1 - ((t.tsr || 0) / 100)))
                }))}>
                  <defs>
                    <linearGradient id="colorQueries" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorFailures" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} />
                  <YAxis axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} />
                  <Tooltip 
                    contentStyle={{borderRadius: '8px', border: 'none', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)'}}
                  />
                  <Area type="monotone" dataKey="queries" name="Total Queries" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorQueries)" />
                  <Area type="monotone" dataKey="failures" name="Failures" stroke="#ef4444" strokeWidth={3} fillOpacity={1} fill="url(#colorFailures)" />
                </AreaChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        {/* Escalations Feed */}
        <div className="col-span-1 bg-white p-6 rounded-2xl border border-gray-100 shadow-sm flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-bold flex items-center gap-2">
              <AlertTriangle size={18} className="text-amber-500" />
              Action Required
            </h2>
            {escalations.length > 0 && (
              <span className="bg-red-100 text-red-700 text-xs font-bold px-2 py-1 rounded-full">
                {escalations.length} Pending
              </span>
            )}
          </div>
          
          <div className="flex-1 overflow-y-auto space-y-4">
            {escalations.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-gray-400 gap-3 pb-8">
                <Check size={32} className="text-gray-300" />
                <p className="text-sm">No pending escalations.</p>
              </div>
            ) : (
              escalations.map((esc, i) => (
                <div key={i} className="border border-red-100 bg-red-50/50 rounded-xl p-4 animate-slide-up">
                  <div className="text-xs font-semibold text-red-600 mb-2 uppercase tracking-wide">AI Agent Failure</div>
                  <div className="text-sm font-medium mb-1 line-clamp-2">Q: {esc.query}</div>
                  <div className="text-xs text-gray-600 mb-4 bg-white p-2 rounded border border-red-100">
                    {esc.reasoning}
                  </div>
                  <div className="flex gap-2">
                    <button 
                      onClick={() => handleResolve(esc.session_id, 'APPROVE')}
                      className="flex-1 bg-black text-white py-1.5 rounded-lg text-xs font-medium hover:bg-gray-800 transition-colors flex items-center justify-center gap-1"
                    >
                      <Check size={14} /> Approve
                    </button>
                    <button 
                      onClick={() => handleResolve(esc.session_id, 'REJECT')}
                      className="flex-1 bg-white border border-gray-200 text-black py-1.5 rounded-lg text-xs font-medium hover:bg-gray-50 transition-colors flex items-center justify-center gap-1"
                    >
                      <X size={14} /> Reject
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
      
      {/* Repository Management */}
      <div className="bg-white p-6 rounded-2xl border border-gray-100 shadow-sm mt-2 animate-slide-up" style={{ animationDelay: '100ms' }}>
        <div className="flex items-center gap-2 mb-6">
          <Folder className="text-skyblue-500" />
          <h2 className="text-lg font-bold">Repository Management</h2>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50/50 text-gray-500 font-medium border-b border-gray-100">
              <tr>
                <th className="px-4 py-3 rounded-tl-lg">Name</th>
                <th className="px-4 py-3">Git Provider</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Last Updated</th>
                <th className="px-4 py-3 text-right rounded-tr-lg">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {repositories.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-400">No repositories found.</td>
                </tr>
              ) : (
                repositories.map(repo => (
                  <React.Fragment key={repo.repository_id}>
                    <tr className="hover:bg-gray-50 transition-colors">
                      <td className="px-4 py-3 font-medium text-gray-900">{repo.name}</td>
                      <td className="px-4 py-3 text-gray-600 capitalize">{repo.git_provider || 'local'}</td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-1 text-xs font-medium rounded-md ${repo.status === 'Active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'}`}>
                          {repo.status || 'Active'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-gray-500">
                        {repo.updated_at ? new Date(repo.updated_at).toLocaleString() : 'N/A'}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="flex justify-end items-center gap-2">
                          <button 
                            onClick={() => handleViewSnapshots(repo.repository_id)}
                            className="px-3 py-1.5 text-xs font-medium bg-white border border-gray-200 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                          >
                            {snapshots[repo.repository_id] ? 'Hide Snapshots' : 'View Snapshots'}
                          </button>
                          <button 
                            onClick={() => handleDeleteRepo(repo.repository_id)}
                            className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                            title="Delete Repository"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </td>
                    </tr>
                    {snapshots[repo.repository_id] && (
                      <tr>
                        <td colSpan={5} className="px-4 py-4 bg-gray-50 border-b border-gray-100">
                          <div className="pl-6 border-l-2 border-skyblue-200">
                            <h4 className="text-xs font-bold text-gray-500 uppercase tracking-wider mb-3 flex items-center gap-2">
                              <Clock size={12} /> Version History
                            </h4>
                            {snapshots[repo.repository_id].length === 0 ? (
                              <p className="text-sm text-gray-500">No snapshots available for this repository.</p>
                            ) : (
                              <div className="space-y-2 max-h-48 overflow-y-auto">
                                {snapshots[repo.repository_id].map((snap: any) => (
                                  <div key={snap.snapshot_id} className="flex items-center justify-between bg-white p-3 rounded-lg border border-gray-200 shadow-sm text-sm">
                                    <div className="font-medium font-mono text-xs text-gray-700">
                                      Commit: {snap.commit_hash || snap.snapshot_id.substring(0,8)}
                                    </div>
                                    <div className="text-gray-500 text-xs">
                                      {new Date(snap.indexed_at).toLocaleString()}
                                    </div>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      
    </div>
  );
};

export default ManagerDashboard;

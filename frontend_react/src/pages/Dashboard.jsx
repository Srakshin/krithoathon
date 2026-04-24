import { useEffect, useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { AnimatePresence, motion } from 'framer-motion';
import {
  Activity,
  BarChart3,
  Clock,
  Database,
  ExternalLink,
  LogOut,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  TriangleAlert,
  Zap,
} from 'lucide-react';
import { format } from 'date-fns';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

function formatTimestamp(value) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return format(date, 'MMM d, h:mm a');
}

function sourceBadge(sourceLabel) {
  return sourceLabel || 'Web';
}

export default function Dashboard() {
  const { user, session, signOut } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [fetchingLatest, setFetchingLatest] = useState(false);
  const [error, setError] = useState(null);
  const [errorType, setErrorType] = useState(null);
  const [seeding, setSeeding] = useState(false);
  const [seedMsg, setSeedMsg] = useState(null);
  const [notice, setNotice] = useState(null);
  const [activeTab, setActiveTab] = useState('All');

  const fetchDigest = async () => {
    if (!session?.access_token) {
      setLoading(false);
      setErrorType('auth');
      setError('Your session is missing. Please sign out and sign in again.');
      return;
    }

    setLoading(true);
    setError(null);
    setErrorType(null);
    setSeedMsg(null);

    try {
      const response = await fetch(`${BACKEND_URL}/daily-brief`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });

      if (response.status === 401) {
        let detail = 'Your session expired or could not be verified. Please sign out and sign in again.';
        try {
          const payload = await response.json();
          if (payload?.detail) detail = payload.detail;
        } catch {
          // Keep fallback message.
        }
        setErrorType('auth');
        throw new Error(detail);
      }

      if (response.status === 503) {
        let detail = "The 'market_intelligence' table isn't ready in Supabase yet.";
        try {
          const payload = await response.json();
          if (payload?.detail) detail = payload.detail;
        } catch {
          // Keep fallback message.
        }
        setErrorType('setup_required');
        throw new Error(detail);
      }

      if (!response.ok) {
        let detail = 'Failed to load your saved digest. Make sure the backend server is running.';
        try {
          const payload = await response.json();
          if (payload?.detail) detail = payload.detail;
        } catch {
          // Keep fallback message.
        }
        setErrorType('general');
        throw new Error(detail);
      }

      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err.message);
      if (data) {
        setNotice({
          type: 'warning',
          text: err.message,
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchLatest = async () => {
    if (!session?.access_token) {
      setErrorType('auth');
      setError('Your session is missing. Please sign out and sign in again.');
      return;
    }

    setFetchingLatest(true);
    setNotice(null);
    setError(null);
    setErrorType(null);

    try {
      const response = await fetch(`${BACKEND_URL}/fetch-intelligence`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });

      if (response.status === 401) {
        let detail = 'Your session expired or could not be verified. Please sign out and sign in again.';
        try {
          const payload = await response.json();
          if (payload?.detail) detail = payload.detail;
        } catch {
          // Keep fallback message.
        }
        setErrorType('auth');
        throw new Error(detail);
      }

      if (!response.ok) {
        let detail = 'Failed to fetch scraper data.';
        try {
          const payload = await response.json();
          if (payload?.detail) detail = payload.detail;
        } catch {
          // Keep fallback message.
        }
        setErrorType('general');
        throw new Error(detail);
      }

      const result = await response.json();

      if (result.total_items > 0 || !data) {
        setData(result);
      }

      setNotice({
        type: result.storage_status === 'failed' ? 'warning' : 'success',
        text: result.message || 'Scraper fetch completed.',
      });
    } catch (err) {
      setError(err.message);
      setNotice({
        type: 'warning',
        text: err.message,
      });
    } finally {
      setFetchingLatest(false);
    }
  };

  const seedDemoData = async () => {
    if (!session?.access_token) return;

    setSeeding(true);
    setSeedMsg(null);

    try {
      const response = await fetch(`${BACKEND_URL}/seed-data`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });
      const payload = await response.json();

      if (!response.ok) {
        setSeedMsg({
          type: 'error',
          text: payload.detail || 'Failed to seed demo data.',
        });
        return;
      }

      setSeedMsg({
        type: 'success',
        text: payload.message || 'Demo data seeded successfully.',
      });
      setNotice({
        type: 'success',
        text: payload.message || 'Demo data seeded successfully.',
      });
      setTimeout(() => {
        fetchDigest();
      }, 700);
    } catch (err) {
      setSeedMsg({
        type: 'error',
        text: err.message,
      });
    } finally {
      setSeeding(false);
    }
  };

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchDigest();
    }, 0);

    return () => {
      window.clearTimeout(timer);
    };
  }, [session]);

  const categoryTabs = ['All', ...Object.keys(data?.categories || {})];
  const selectedTab = categoryTabs.includes(activeTab) ? activeTab : 'All';
  const sourceCounts = Object.entries(data?.source_counts || {});

  const getIconForCategory = (categoryName) => {
    if (categoryName.includes('Competitor')) return <Zap className="w-5 h-5 text-amber-400" />;
    if (categoryName.includes('Pain')) return <ShieldAlert className="w-5 h-5 text-rose-400" />;
    if (categoryName.includes('Tech') || categoryName.includes('Trend')) {
      return <BarChart3 className="w-5 h-5 text-blue-400" />;
    }
    return <Activity className="w-5 h-5 text-zinc-400" />;
  };

  const renderSetupRequired = () => (
    <div className="p-8 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-300 max-w-2xl mx-auto mt-10">
      <h3 className="font-semibold text-lg mb-3 flex items-center gap-2">
        <Database className="w-5 h-5 text-amber-400" />
        Database Setup Required
      </h3>
      <p className="text-sm opacity-90 mb-4 leading-relaxed">
        The
        {' '}
        <code className="bg-amber-500/20 px-1.5 py-0.5 rounded text-amber-200 font-mono text-xs">market_intelligence</code>
        {' '}
        table or its policies are not ready in Supabase yet.
      </p>
      <ol className="text-sm space-y-2 mb-6 list-decimal list-inside opacity-90">
        <li>
          Open your Supabase Dashboard and run
          {' '}
          <code className="bg-amber-500/20 px-1.5 py-0.5 rounded text-amber-200 font-mono text-xs">supabase_setup.sql</code>
          {' '}
          from the project root in the SQL Editor.
        </li>
        <li>After that, use Fetch Latest to pull real scraper data or seed demo data if you want sample content.</li>
      </ol>
      {seedMsg && (
        <div
          className={`mb-4 text-sm px-4 py-2 rounded-lg ${
            seedMsg.type === 'success' ? 'bg-green-500/20 text-green-300' : 'bg-red-500/20 text-red-300'
          }`}
        >
          {seedMsg.text}
        </div>
      )}
      <div className="flex gap-3 flex-wrap">
        <button
          onClick={seedDemoData}
          disabled={seeding}
          className="flex items-center gap-2 px-5 py-2.5 bg-amber-500/20 hover:bg-amber-500/30 border border-amber-500/30 rounded-lg text-sm font-medium transition-all disabled:opacity-50"
        >
          <Sparkles className={`w-4 h-4 ${seeding ? 'animate-pulse' : ''}`} />
          {seeding ? 'Seeding...' : 'Seed Demo Data'}
        </button>
        <button
          onClick={fetchDigest}
          className="flex items-center gap-2 px-5 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm font-medium text-zinc-300 transition-all"
        >
          <RefreshCw className="w-4 h-4" />
          Retry Saved View
        </button>
      </div>
    </div>
  );

  const renderNotice = () => {
    if (!notice) return null;

    const warning = notice.type === 'warning';
    return (
      <div
        className={`mb-6 rounded-2xl border px-5 py-4 text-sm ${
          warning
            ? 'border-amber-500/20 bg-amber-500/10 text-amber-200'
            : 'border-emerald-500/20 bg-emerald-500/10 text-emerald-200'
        }`}
      >
        <div className="flex items-start gap-3">
          {warning ? <TriangleAlert className="w-5 h-5 mt-0.5" /> : <Sparkles className="w-5 h-5 mt-0.5" />}
          <p className="leading-relaxed">{notice.text}</p>
        </div>
      </div>
    );
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className="flex flex-col items-center justify-center py-20 text-zinc-500">
          <RefreshCw className="w-8 h-8 animate-spin mb-4" />
          <p>Loading your saved intelligence digest...</p>
        </div>
      );
    }

    if (error && !data) {
      if (errorType === 'setup_required') {
        return renderSetupRequired();
      }

      return (
        <div className="p-6 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 max-w-2xl mx-auto mt-10">
          <h3 className="font-semibold mb-2 flex items-center gap-2">
            <ShieldAlert className="w-5 h-5" />
            Error Loading Digest
          </h3>
          <p className="text-sm opacity-90">{error}</p>
          <button
            onClick={fetchDigest}
            className="mt-4 flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm font-medium text-zinc-300 transition-all"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      );
    }

    if (!data || Object.keys(data.categories || {}).length === 0) {
      return (
        <div className="flex flex-col items-center justify-center py-28 text-zinc-500 max-w-lg mx-auto text-center">
          <div className="w-16 h-16 rounded-2xl bg-[#141415] border border-white/5 flex items-center justify-center mb-6">
            <Clock className="w-8 h-8 text-zinc-400" />
          </div>
          <h3 className="text-xl text-zinc-200 font-medium mb-2">No saved updates yet</h3>
          <p className="text-sm leading-relaxed">
            Click
            {' '}
            <span className="text-zinc-300 font-medium">Fetch Latest</span>
            {' '}
            to pull live data from the working scrapers, store it in Supabase, and render it here.
          </p>
        </div>
      );
    }

    return (
      <div className="max-w-5xl mx-auto mt-8">
        {renderNotice()}

        {sourceCounts.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 mb-6">
            <div className="px-3 py-1.5 rounded-full bg-white/5 border border-white/10 text-xs font-medium text-zinc-200">
              {data.total_items}
              {' '}
              items
            </div>
            {typeof data.inserted_count === 'number' && (
              <div className="px-3 py-1.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-xs font-medium text-emerald-200">
                {data.inserted_count}
                {' '}
                stored
              </div>
            )}
            {typeof data.duplicates_skipped === 'number' && data.duplicates_skipped > 0 && (
              <div className="px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-xs font-medium text-amber-200">
                {data.duplicates_skipped}
                {' '}
                duplicates skipped
              </div>
            )}
            {sourceCounts.map(([source, count]) => (
              <div
                key={source}
                className="px-3 py-1.5 rounded-full bg-[#141415] border border-white/5 text-xs font-medium text-zinc-400"
              >
                {source}
                {' '}
                {count}
              </div>
            ))}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2 mb-8">
          {categoryTabs.map((categoryName) => (
            <button
              key={categoryName}
              onClick={() => setActiveTab(categoryName)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                selectedTab === categoryName
                  ? 'bg-white text-black'
                  : 'bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-white'
              }`}
            >
              {categoryName}
            </button>
          ))}
        </div>

        <div className="grid gap-6">
          <AnimatePresence mode="popLayout">
            {Object.entries(data.categories).map(([categoryName, items]) => {
              if (selectedTab !== 'All' && selectedTab !== categoryName) return null;

              return (
                <motion.div
                  key={categoryName}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.98 }}
                  className="mb-8"
                >
                  <h2 className="text-lg font-semibold text-zinc-200 flex items-center gap-2 mb-4">
                    {getIconForCategory(categoryName)}
                    {categoryName}
                  </h2>
                  <div className="grid md:grid-cols-2 gap-4">
                    {items.map((item, index) => {
                      const timestamp = formatTimestamp(item.published_at || item.created_at);

                      return (
                        <div
                          key={`${item.url || item.title}-${index}`}
                          className="group p-5 rounded-xl bg-[#141415] border border-white/5 hover:border-white/10 transition-all flex flex-col h-full relative overflow-hidden"
                        >
                          <div className="absolute top-0 left-0 w-1 h-full bg-gradient-to-b from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

                          <div className="flex items-start justify-between gap-3 mb-4">
                            <div>
                              <div className="text-xs font-medium text-zinc-500 uppercase tracking-[0.16em]">
                                {sourceBadge(item.source_label)}
                              </div>
                              {item.sub_source && (
                                <div className="text-xs text-zinc-600 mt-1">{item.sub_source}</div>
                              )}
                            </div>
                            <div className="flex items-center gap-3 text-zinc-600">
                              {timestamp && <span className="text-xs">{timestamp}</span>}
                              {item.url && (
                                <a
                                  href={item.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="hover:text-white transition-colors"
                                  title="Open source"
                                >
                                  <ExternalLink className="w-4 h-4" />
                                </a>
                              )}
                            </div>
                          </div>

                          <h4 className="font-medium text-zinc-200 mb-3 leading-snug">{item.title}</h4>
                          <p className="text-sm text-zinc-400 leading-relaxed flex-grow">
                            {item.summary || 'This scraper item did not include a text summary.'}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#fafafa] font-sans selection:bg-white/10">
      <nav className="border-b border-white/5 bg-[#0a0a0a]/80 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center">
              <Activity className="w-5 h-5 text-black" />
            </div>
            <span className="font-semibold tracking-tight">Morning Pulse</span>
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-white/5 border border-white/10 text-xs font-medium text-zinc-300">
              <Clock className="w-3.5 h-3.5 text-blue-400" />
              Next run: 08:00 AM
            </div>
            <div className="h-4 w-px bg-white/10 mx-1" />
            <span className="text-sm text-zinc-400 hidden sm:block">{user?.email}</span>
            <button
              onClick={signOut}
              className="p-2 text-zinc-400 hover:text-white hover:bg-white/5 rounded-md transition-colors"
              title="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </nav>

      <main className="px-6 py-12">
        <div className="max-w-5xl mx-auto">
          <header className="mb-10 flex flex-col lg:flex-row lg:items-end justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold tracking-tight mb-2">Daily Intelligence</h1>
              <p className="text-zinc-400">{format(new Date(), 'EEEE, MMMM do, yyyy')}</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <button
                onClick={fetchLatest}
                disabled={fetchingLatest}
                className="flex items-center gap-2 px-4 py-2 bg-white text-black text-sm font-medium rounded-lg hover:bg-zinc-200 transition-colors disabled:opacity-50"
              >
                <Sparkles className={`w-4 h-4 ${fetchingLatest ? 'animate-pulse' : ''}`} />
                {fetchingLatest ? 'Fetching...' : 'Fetch Latest'}
              </button>
              <button
                onClick={fetchDigest}
                disabled={loading}
                className="flex items-center gap-2 px-4 py-2 bg-[#141415] border border-white/5 text-sm font-medium rounded-lg hover:bg-white/5 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                Load Saved
              </button>
            </div>
          </header>

          {renderContent()}
        </div>
      </main>
    </div>
  );
}

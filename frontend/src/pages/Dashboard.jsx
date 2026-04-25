import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { motion } from 'framer-motion';
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
  Settings,
  Search,
  TrendingUp,
  MessageSquare,
  Target
} from 'lucide-react';
import { format } from 'date-fns';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import CustomizationPanel from '../components/CustomizationPanel';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';
const DISPLAY_CATEGORIES = [
  'Competitor Updates',
  'User Pain Points',
  'Emerging Tech Trends',
  'Market Opportunities',
  'Customer Feedback Signals'
];

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
  const [loadingSaved, setLoadingSaved] = useState(false);
  const [fetchingData, setFetchingData] = useState(false);
  const [error, setError] = useState(null);
  const [errorType, setErrorType] = useState(null);
  const [seeding, setSeeding] = useState(false);
  const [seedMsg, setSeedMsg] = useState(null);
  const [notice, setNotice] = useState(null);
  const [isCustomizationOpen, setIsCustomizationOpen] = useState(false);
  const [targetEmailOverride, setTargetEmailOverride] = useState(null);
  const targetEmail = targetEmailOverride ?? user?.email ?? '';

  const fetchDigest = async () => {
    if (!session?.access_token) {
      setLoadingSaved(false);
      setErrorType('auth');
      setError('Your session is missing. Please sign out and sign in again.');
      return;
    }

    setLoadingSaved(true);
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
      setNotice({
        type: 'success',
        text: result.message || 'Loaded saved results from Supabase.',
      });
    } catch (err) {
      setError(err.message);
      setNotice({
        type: 'warning',
        text: err.message,
      });
    } finally {
      setLoadingSaved(false);
    }
  };

  const fetchData = async () => {
    if (!session?.access_token) {
      setErrorType('auth');
      setError('Your session is missing. Please sign out and sign in again.');
      return;
    }

    setFetchingData(true);
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
      setData(result);
      setNotice({
        type: 'success',
        text: result.message || 'Fetch completed successfully.',
      });
    } catch (err) {
      setError(err.message);
      setNotice({
        type: 'warning',
        text: err.message,
      });
    } finally {
      setFetchingData(false);
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
      await fetchDigest();
    } catch (err) {
      setSeedMsg({
        type: 'error',
        text: err.message,
      });
    } finally {
      setSeeding(false);
    }
  };

  const sourceCounts = Object.entries(data?.source_counts || {});

  const getIconForCategory = (categoryName) => {
    if (categoryName.includes('Competitor')) return <Zap className="w-5 h-5 text-amber-400" />;
    if (categoryName.includes('Pain')) return <ShieldAlert className="w-5 h-5 text-rose-400" />;
    if (categoryName.includes('Emerging')) return <TrendingUp className="w-5 h-5 text-blue-400" />;
    if (categoryName.includes('Market')) return <Target className="w-5 h-5 text-emerald-400" />;
    if (categoryName.includes('Feedback')) return <MessageSquare className="w-5 h-5 text-purple-400" />;
    return <BarChart3 className="w-5 h-5 text-zinc-400" />;
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
        <li>After that, use Fetch Data to run the scrapers and categorize the stored results.</li>
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
          disabled={loadingSaved}
          className="flex items-center gap-2 px-5 py-2.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm font-medium text-zinc-300 transition-all disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${loadingSaved ? 'animate-spin' : ''}`} />
          Load Saved
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

  const renderCards = (items) => (
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
              {item.summary || 'This record did not include a summary.'}
            </p>
          </div>
        );
      })}
    </div>
  );

  const renderEmptyState = () => {
    const hasLoadedResult = Boolean(data);

    return (
      <div className="max-w-3xl mx-auto mt-8">
        {renderNotice()}
        <div className="flex flex-col items-center justify-center py-28 text-zinc-500 max-w-xl mx-auto text-center">
          <div className="w-16 h-16 rounded-2xl bg-[#141415] border border-white/5 flex items-center justify-center mb-6">
            <Clock className="w-8 h-8 text-zinc-400" />
          </div>
          <h3 className="text-xl text-zinc-200 font-medium mb-2">
            {hasLoadedResult ? 'No saved updates yet' : 'Ready to fetch market intelligence'}
          </h3>
          <p className="text-sm leading-relaxed">
            {hasLoadedResult
              ? 'Click Fetch Data to run the scrapers, save the results in Supabase, categorize them with Grok, and render the three sections below.'
              : 'Nothing runs automatically here. Click Fetch Data when you want the backend to scrape, store, analyze, and return the latest results in one flow.'}
          </p>
        </div>
      </div>
    );
  };

  const renderContent = () => {
    if (loadingSaved) {
      return (
        <div className="flex flex-col items-center justify-center py-20 text-zinc-500">
          <RefreshCw className="w-8 h-8 animate-spin mb-4" />
          <p>Loading saved intelligence from Supabase...</p>
        </div>
      );
    }

    if (error && !data) {
      if (errorType === 'setup_required') {
        return renderSetupRequired();
      }

      return (
        <div className="max-w-3xl mx-auto mt-8">
          {renderNotice()}
          <div className="p-6 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 max-w-2xl mx-auto mt-10">
            <h3 className="font-semibold mb-2 flex items-center gap-2">
              <ShieldAlert className="w-5 h-5" />
              Error Loading Data
            </h3>
            <p className="text-sm opacity-90">{error}</p>
            <button
              onClick={fetchDigest}
              className="mt-4 flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-sm font-medium text-zinc-300 transition-all"
            >
              <RefreshCw className="w-4 h-4" />
              Load Saved
            </button>
          </div>
        </div>
      );
    }

    if (!data || data.total_items === 0) {
      return renderEmptyState();
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
            {typeof data.categorized_count === 'number' && (
              <div className="px-3 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/20 text-xs font-medium text-blue-200">
                {data.categorized_count}
                {' '}
                categorized
              </div>
            )}
            {typeof data.duplicates_skipped === 'number' && data.duplicates_skipped > 0 && (
              <div className="px-3 py-1.5 rounded-full bg-amber-500/10 border border-amber-500/20 text-xs font-medium text-amber-200">
                {data.duplicates_skipped}
                {' '}
                reused
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

        <div className="mb-10 p-6 rounded-2xl bg-[#141415] border border-white/5 shadow-lg">
          <h3 className="text-sm font-medium text-zinc-400 mb-6 uppercase tracking-wider">Insight Distribution</h3>
          <div className="h-48 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={DISPLAY_CATEGORIES.map(cat => ({ name: cat.replace(' Updates', '').replace(' Signals', ''), count: data.categories?.[cat]?.length || 0 }))}>
                <XAxis dataKey="name" stroke="#52525b" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="#52525b" fontSize={11} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip 
                  cursor={{ fill: 'rgba(255,255,255,0.05)' }}
                  contentStyle={{ backgroundColor: '#141415', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px' }}
                  itemStyle={{ color: '#fff' }}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {DISPLAY_CATEGORIES.map((cat, index) => {
                    const colors = ['#fbbf24', '#f43f5e', '#60a5fa', '#34d399', '#c084fc'];
                    return <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />;
                  })}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid gap-8">
          {DISPLAY_CATEGORIES.map((categoryName, index) => {
            const items = data.categories?.[categoryName] || [];

            return (
              <motion.section
                key={categoryName}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.06 }}
              >
                <div className="flex items-center justify-between gap-3 mb-4">
                  <h2 className="text-lg font-semibold text-zinc-200 flex items-center gap-2">
                    {getIconForCategory(categoryName)}
                    {categoryName}
                  </h2>
                  <div className="px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs text-zinc-400">
                    {items.length}
                    {' '}
                    item{items.length === 1 ? '' : 's'}
                  </div>
                </div>

                {items.length > 0 ? (
                  renderCards(items)
                ) : (
                  <div className="rounded-xl border border-white/5 bg-[#141415] px-5 py-4 text-sm text-zinc-500">
                    No records landed in this category for the current result set.
                  </div>
                )}
              </motion.section>
            );
          })}
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
              <Database className="w-3.5 h-3.5 text-emerald-400" />
              Manual fetch only
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
              <h1 className="text-3xl font-bold tracking-tight mb-2">On-Demand Intelligence</h1>
              <p className="text-zinc-400">{format(new Date(), 'EEEE, MMMM do, yyyy')}</p>
            </div>
            <div className="flex flex-col sm:flex-row flex-wrap gap-3 items-end">
              <div className="flex flex-col gap-1.5 w-full sm:w-auto">
                <label className="text-xs text-zinc-500 font-medium ml-1">Target Email</label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                    <Search className="h-4 w-4 text-zinc-500" />
                  </div>
                  <input
                    type="email"
                    value={targetEmail}
                    onChange={(e) => setTargetEmailOverride(e.target.value)}
                    className="w-full sm:w-64 pl-10 pr-4 py-2 bg-[#141415] border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-white/30 focus:ring-1 focus:ring-white/30 transition-all placeholder:text-zinc-600"
                    placeholder="Enter email to fetch for..."
                  />
                </div>
              </div>
              <button
                onClick={fetchData}
                disabled={fetchingData}
                className="flex items-center justify-center gap-2 px-5 py-2 h-10 bg-white text-black text-sm font-medium rounded-lg hover:bg-zinc-200 transition-colors disabled:opacity-50"
              >
                <Sparkles className={`w-4 h-4 ${fetchingData ? 'animate-pulse' : ''}`} />
                {fetchingData ? 'Fetching...' : 'Fetch Data'}
              </button>
              <button
                onClick={fetchDigest}
                disabled={loadingSaved}
                className="flex items-center justify-center gap-2 px-5 py-2 h-10 bg-[#141415] border border-white/5 text-sm font-medium rounded-lg hover:bg-white/5 transition-colors disabled:opacity-50"
              >
                <RefreshCw className={`w-4 h-4 ${loadingSaved ? 'animate-spin' : ''}`} />
                Load Saved
              </button>
              <button
                onClick={() => setIsCustomizationOpen(true)}
                className="flex items-center justify-center gap-2 p-2 h-10 w-10 bg-[#141415] border border-white/5 rounded-lg hover:bg-white/5 transition-colors text-zinc-400 hover:text-white"
                title="Customize Dashboard"
              >
                <Settings className="w-5 h-5" />
              </button>
            </div>
          </header>

          {renderContent()}
        </div>
      </main>

      <CustomizationPanel 
        isOpen={isCustomizationOpen} 
        onClose={() => setIsCustomizationOpen(false)} 
      />
    </div>
  );
}

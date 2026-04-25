import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Settings, Check, ChevronDown, Bell, Hash, Briefcase, Database, Clock, ListChecks, Mail } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000';

export default function CustomizationPanel({ isOpen, onClose }) {
  const { session } = useAuth();

  const [keywords, setKeywords] = useState('EdTech, AI Tutors, Learning Management Systems');
  const [industry, setIndustry] = useState('K-12 Education');
  const [frequency, setFrequency] = useState('Daily at 8:00 AM');
  const [additionalEmails, setAdditionalEmails] = useState('');
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  
  const [categories, setCategories] = useState({
    'Competitor Updates': true,
    'User Pain Points': true,
    'Emerging Tech Trends': true,
    'Market Opportunities': true,
    'Customer Feedback Signals': false,
  });

  const [sources, setSources] = useState({
    'Hacker News': true,
    'Reddit': true,
    'Twitter / X': false,
    'TechCrunch': true,
  });
  
  const [notifications, setNotifications] = useState({
    email: true,
    slack: false,
    inApp: true,
  });

  const toggleCategory = (cat) => {
    setCategories(prev => ({ ...prev, [cat]: !prev[cat] }));
  };

  const toggleSource = (source) => {
    setSources(prev => ({ ...prev, [source]: !prev[source] }));
  };
  
  const toggleNotification = (type) => {
    setNotifications(prev => ({ ...prev, [type]: !prev[type] }));
  };

  useEffect(() => {
    if (!isOpen || !session?.access_token) {
      return undefined;
    }

    let cancelled = false;

    const loadPreferences = async () => {
      setLoading(true);
      try {
        const response = await fetch(`${BACKEND_URL}/preferences`, {
          headers: { Authorization: `Bearer ${session.access_token}` }
        });
        const data = await response.json();

        if (cancelled) return;

        if (data.keywords) setKeywords(data.keywords);
        if (data.industry) setIndustry(data.industry);
        if (data.frequency) setFrequency(data.frequency);
        if (data.categories) setCategories(data.categories);
        if (data.sources) setSources(data.sources);
        if (data.notifications) setNotifications(data.notifications);
        if (data.additional_emails !== undefined) setAdditionalEmails(data.additional_emails || '');
      } catch (err) {
        if (!cancelled) {
          console.error('Error fetching preferences:', err);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void loadPreferences();

    return () => {
      cancelled = true;
    };
  }, [isOpen, session?.access_token]);

  const handleSave = async () => {
    if (!session?.access_token) return onClose();
    
    setSaving(true);
    try {
      await fetch(`${BACKEND_URL}/preferences`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          keywords,
          industry,
          frequency,
          categories,
          sources,
          notifications,
          additional_emails: additionalEmails
        })
      });
    } catch (err) {
      console.error('Error saving preferences:', err);
    } finally {
      setSaving(false);
      onClose();
    }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />
          <motion.div
            initial={{ x: '100%', opacity: 0.5 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: '100%', opacity: 0.5 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed inset-y-0 right-0 w-full max-w-md bg-[#0a0a0a] border-l border-white/10 z-50 shadow-2xl overflow-y-auto"
          >
            <div className="p-6 border-b border-white/10 flex items-center justify-between bg-[#141415]/80 backdrop-blur-md sticky top-0 z-10">
              <div className="flex items-center gap-3">
                <Settings className="w-5 h-5 text-zinc-300" />
                <h2 className="text-lg font-semibold text-white">Customization</h2>
              </div>
              <button 
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-white/10 text-zinc-400 hover:text-white transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-8 text-zinc-300">
              {/* Keywords Section */}
              <section className="space-y-4">
                <div className="flex items-center gap-2 text-white font-medium">
                  <Hash className="w-4 h-4 text-emerald-400" />
                  <h3>Keywords & Topics</h3>
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-500 uppercase tracking-wider">Tracked Keywords (comma separated)</label>
                  <textarea
                    value={keywords}
                    onChange={(e) => setKeywords(e.target.value)}
                    className="w-full bg-[#141415] border border-white/10 rounded-xl p-3 text-sm focus:border-white/30 focus:ring-1 focus:ring-white/30 transition-all outline-none resize-none h-20"
                    placeholder="e.g. EdTech, AI, SAAS..."
                  />
                </div>
              </section>

              {/* Industries Section */}
              <section className="space-y-4">
                <div className="flex items-center gap-2 text-white font-medium">
                  <Briefcase className="w-4 h-4 text-blue-400" />
                  <h3>Industry & Niche</h3>
                </div>
                <div className="relative">
                  <select
                    value={industry}
                    onChange={(e) => setIndustry(e.target.value)}
                    className="w-full bg-[#141415] border border-white/10 rounded-xl p-3 text-sm appearance-none focus:border-white/30 focus:ring-1 focus:ring-white/30 transition-all outline-none"
                  >
                    <option>K-12 Education</option>
                    <option>Higher Education</option>
                    <option>Corporate Training</option>
                    <option>Language Learning</option>
                    <option>EdTech Infrastructure</option>
                  </select>
                  <ChevronDown className="w-4 h-4 absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none" />
                </div>
              </section>

              {/* Data Sources */}
              <section className="space-y-4">
                <div className="flex items-center gap-2 text-white font-medium">
                  <Database className="w-4 h-4 text-amber-400" />
                  <h3>Data Sources</h3>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  {Object.entries(sources).map(([source, isEnabled]) => (
                    <button
                      key={source}
                      onClick={() => toggleSource(source)}
                      className={`flex items-center gap-3 p-3 rounded-xl border text-sm transition-all ${
                        isEnabled 
                          ? 'bg-amber-500/10 border-amber-500/30 text-amber-100' 
                          : 'bg-[#141415] border-white/5 text-zinc-500 hover:border-white/10'
                      }`}
                    >
                      <div className={`w-4 h-4 rounded-full border flex items-center justify-center ${isEnabled ? 'border-amber-400 bg-amber-400/20' : 'border-zinc-600'}`}>
                        {isEnabled && <Check className="w-2.5 h-2.5 text-amber-400" />}
                      </div>
                      {source}
                    </button>
                  ))}
                </div>
              </section>

              {/* Categories */}
              <section className="space-y-4">
                <div className="flex items-center gap-2 text-white font-medium">
                  <ListChecks className="w-4 h-4 text-rose-400" />
                  <h3>Insight Categories</h3>
                </div>
                <div className="space-y-2">
                  {Object.entries(categories).map(([cat, isEnabled]) => (
                    <button
                      key={cat}
                      onClick={() => toggleCategory(cat)}
                      className="w-full flex items-center justify-between p-3 rounded-xl bg-[#141415] border border-white/5 hover:border-white/10 transition-all group"
                    >
                      <span className={`text-sm ${isEnabled ? 'text-zinc-200' : 'text-zinc-500'}`}>{cat}</span>
                      <div className={`w-10 h-5 rounded-full relative transition-colors ${isEnabled ? 'bg-rose-500/50' : 'bg-zinc-800'}`}>
                        <div className={`absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform ${isEnabled ? 'translate-x-5' : 'translate-x-0'}`} />
                      </div>
                    </button>
                  ))}
                </div>
              </section>

              {/* Email & Frequency */}
              <section className="space-y-4">
                <div className="flex items-center gap-2 text-white font-medium">
                  <Clock className="w-4 h-4 text-purple-400" />
                  <h3>Email Delivery</h3>
                </div>
                <div className="relative">
                  <select
                    value={frequency}
                    onChange={(e) => setFrequency(e.target.value)}
                    className="w-full bg-[#141415] border border-white/10 rounded-xl p-3 text-sm appearance-none focus:border-white/30 focus:ring-1 focus:ring-white/30 transition-all outline-none"
                  >
                    <option>Daily at 8:00 AM</option>
                    <option>Daily at 5:00 PM</option>
                    <option>Weekly (Monday Morning)</option>
                    <option>Weekly (Friday Afternoon)</option>
                    <option>Real-time (Immediate)</option>
                    <option>Never (Dashboard Only)</option>
                  </select>
                  <ChevronDown className="w-4 h-4 absolute right-4 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none" />
                </div>
              </section>

              {/* Additional Emails */}
              <section className="space-y-4">
                <div className="flex items-center gap-2 text-white font-medium">
                  <Mail className="w-4 h-4 text-emerald-400" />
                  <h3>Additional Recipients</h3>
                </div>
                <div className="space-y-2">
                  <label className="text-xs text-zinc-500 uppercase tracking-wider">Extra emails (comma separated)</label>
                  <input
                    type="text"
                    value={additionalEmails}
                    onChange={(e) => setAdditionalEmails(e.target.value)}
                    className="w-full bg-[#141415] border border-white/10 rounded-xl p-3 text-sm focus:border-white/30 focus:ring-1 focus:ring-white/30 transition-all outline-none"
                    placeholder="team@example.com, boss@example.com"
                  />
                </div>
              </section>

              {/* Notifications */}
              <section className="space-y-4">
                <div className="flex items-center gap-2 text-white font-medium">
                  <Bell className="w-4 h-4 text-sky-400" />
                  <h3>Notifications</h3>
                </div>
                <div className="flex gap-3">
                  {Object.entries(notifications).map(([type, isEnabled]) => (
                    <button
                      key={type}
                      onClick={() => toggleNotification(type)}
                      className={`flex-1 py-2 rounded-lg text-sm capitalize font-medium transition-all ${
                        isEnabled ? 'bg-white text-black' : 'bg-[#141415] text-zinc-400 hover:bg-white/10 border border-white/5'
                      }`}
                    >
                      {type}
                    </button>
                  ))}
                </div>
              </section>
            </div>

            <div className="p-6 border-t border-white/10 bg-[#0a0a0a] sticky bottom-0 z-10">
              <button
                onClick={handleSave}
                disabled={saving || loading}
                className="w-full py-3 bg-white text-black rounded-xl font-medium hover:bg-zinc-200 transition-colors shadow-lg shadow-white/5 disabled:opacity-50 flex justify-center items-center gap-2"
              >
                {saving ? (
                  <>
                    <Clock className="w-4 h-4 animate-spin" /> Saving...
                  </>
                ) : 'Save Preferences'}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

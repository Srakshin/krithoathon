import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowRight, BarChart3, Activity, Zap, ShieldAlert } from 'lucide-react';

export default function Landing() {
  return (
    <div className="min-h-screen bg-[#0a0a0a] text-[#fafafa] overflow-hidden selection:bg-white/10">
      {/* Navbar */}
      <nav className="fixed top-0 w-full border-b border-white/5 bg-[#0a0a0a]/50 backdrop-blur-md z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-white flex items-center justify-center">
              <Activity className="w-5 h-5 text-black" />
            </div>
            <span className="font-semibold text-lg tracking-tight">The Morning Pulse</span>
          </div>
          <div className="flex items-center gap-4">
            <Link to="/login" className="text-sm text-zinc-400 hover:text-white transition-colors">
              Log in
            </Link>
            <Link 
              to="/login" 
              className="px-4 py-2 text-sm font-medium bg-white text-black rounded-md hover:bg-zinc-200 transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <main className="pt-32 pb-16 px-6">
        <div className="max-w-5xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-sm text-zinc-300 mb-8">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
              Live EdTech Market Intelligence
            </div>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-8 leading-tight">
              Know what your market <br className="hidden md:block" />
              is <span className="text-transparent bg-clip-text bg-gradient-to-r from-zinc-200 to-zinc-500">saying today.</span>
            </h1>
            <p className="text-lg md:text-xl text-zinc-400 max-w-2xl mx-auto mb-10 leading-relaxed">
              We crawl Reddit, Hacker News, and RSS feeds to deliver a concise, actionable daily digest of competitor updates, user pain points, and emerging tech trends right to your dashboard.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link 
                to="/login" 
                className="flex items-center gap-2 px-6 py-3 text-base font-medium bg-white text-black rounded-lg hover:bg-zinc-200 transition-all active:scale-95"
              >
                Start your 14-day trial <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </motion.div>
        </div>

        {/* Feature Cards */}
        <div className="max-w-6xl mx-auto mt-32 grid md:grid-cols-3 gap-6">
          {[
            {
              title: "Competitor Updates",
              description: "Track what competitors are launching this week before it hits the mainstream news.",
              icon: Zap,
              color: "text-amber-400",
              bg: "bg-amber-400/10"
            },
            {
              title: "User Pain Points",
              description: "Discover what educators are complaining about right now on r/Teachers and r/edtech.",
              icon: ShieldAlert,
              color: "text-rose-400",
              bg: "bg-rose-400/10"
            },
            {
              title: "Emerging Trends",
              description: "Spot the next big AI integrations or software shifts in the EdTech ecosystem.",
              icon: BarChart3,
              color: "text-blue-400",
              bg: "bg-blue-400/10"
            }
          ].map((feature, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 + i * 0.1 }}
              className="p-6 rounded-2xl bg-[#141415] border border-white/5 hover:border-white/10 transition-colors"
            >
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center mb-6 ${feature.bg}`}>
                <feature.icon className={`w-6 h-6 ${feature.color}`} />
              </div>
              <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
              <p className="text-zinc-400 leading-relaxed">
                {feature.description}
              </p>
            </motion.div>
          ))}
        </div>
      </main>
    </div>
  );
}

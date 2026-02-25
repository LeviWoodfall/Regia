import { useState } from 'react';
import { Sun, Eye, EyeOff, LogIn, UserPlus } from 'lucide-react';
import { useAuth } from '../lib/auth';
import { setupUser } from '../lib/api';

export default function LoginPage() {
  const { setupCompleted, login, refresh } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (!setupCompleted) {
      // First-time setup
      try {
        const resp = await setupUser({ username, password, display_name: displayName || username });
        localStorage.setItem('regia_token', resp.data.token);
        await refresh();
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Setup failed');
      }
    } else {
      // Login
      const ok = await login(username, password);
      if (!ok) {
        setError('Invalid username or password');
      }
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen bg-warm-50 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-sunset-400 to-sunset-600 flex items-center justify-center mx-auto mb-4 shadow-lg">
            <Sun className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-warm-900 tracking-tight">Regia</h1>
          <p className="text-sm text-sand-500 mt-1">Intelligent Document Management</p>
        </div>

        {/* Form Card */}
        <div className="bg-white rounded-2xl border border-sand-200 shadow-lg p-8">
          <h2 className="text-lg font-semibold text-warm-900 mb-1">
            {setupCompleted ? 'Welcome back' : 'Create your account'}
          </h2>
          <p className="text-sm text-sand-500 mb-6">
            {setupCompleted
              ? 'Sign in to access your documents'
              : 'Set up your login credentials to get started'
            }
          </p>

          {error && (
            <div className="mb-4 px-4 py-2.5 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {!setupCompleted && (
              <div>
                <label className="text-xs font-medium text-sand-600 mb-1.5 block">Display Name</label>
                <input
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Your name"
                  className="w-full px-4 py-2.5 bg-sand-50 border border-sand-200 rounded-xl text-sm
                             text-warm-900 placeholder-sand-400
                             focus:outline-none focus:ring-2 focus:ring-sunset-400/40 focus:border-sunset-400"
                />
              </div>
            )}

            <div>
              <label className="text-xs font-medium text-sand-600 mb-1.5 block">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Enter username"
                required
                autoFocus
                className="w-full px-4 py-2.5 bg-sand-50 border border-sand-200 rounded-xl text-sm
                           text-warm-900 placeholder-sand-400
                           focus:outline-none focus:ring-2 focus:ring-sunset-400/40 focus:border-sunset-400"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-sand-600 mb-1.5 block">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder={setupCompleted ? 'Enter password' : 'Create a password (min 8 chars)'}
                  required
                  className="w-full px-4 py-2.5 bg-sand-50 border border-sand-200 rounded-xl text-sm
                             text-warm-900 placeholder-sand-400
                             focus:outline-none focus:ring-2 focus:ring-sunset-400/40 focus:border-sunset-400"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-sand-400 hover:text-warm-600"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !username || !password}
              className="w-full flex items-center justify-center gap-2 px-4 py-3
                         bg-gradient-to-r from-sunset-500 to-sunset-600 text-white rounded-xl
                         text-sm font-semibold shadow-md hover:shadow-lg
                         hover:from-sunset-600 hover:to-sunset-700 transition-all duration-200
                         disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
              ) : setupCompleted ? (
                <><LogIn className="w-4 h-4" /> Sign In</>
              ) : (
                <><UserPlus className="w-4 h-4" /> Create Account</>
              )}
            </button>
          </form>
        </div>

        <p className="text-center text-xs text-sand-400 mt-6">
          Regia v0.1.0 &middot; All data stays on your device
        </p>
      </div>
    </div>
  );
}

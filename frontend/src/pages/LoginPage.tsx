import { useState } from 'react';
import { Sun, Eye, EyeOff, LogIn, UserPlus, ArrowLeft, Mail, KeyRound } from 'lucide-react';
import { useAuth } from '../lib/auth';
import { setupUser, forgotPassword, resetPassword } from '../lib/api';

type View = 'login' | 'create' | 'forgot' | 'reset';

export default function LoginPage() {
  const { setupCompleted, login, refresh } = useAuth();
  const [view, setView] = useState<View>(() => {
    // Check URL for reset token
    const params = new URLSearchParams(window.location.search);
    if (params.get('token')) return 'reset';
    return 'login';
  });

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  const resetForm = () => {
    setUsername(''); setPassword(''); setEmail(''); setDisplayName('');
    setNewPassword(''); setConfirmPassword('');
    setError(''); setSuccess(''); setShowPassword(false);
  };

  const switchView = (v: View) => { resetForm(); setView(v); };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setLoading(true);
    const ok = await login(username, password);
    if (!ok) setError('Invalid username or password');
    setLoading(false);
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setLoading(true);
    try {
      const resp = await setupUser({
        username, password,
        email: email || '',
        display_name: displayName || username,
      });
      localStorage.setItem('regia_token', resp.data.token);
      await refresh();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Account creation failed');
    }
    setLoading(false);
  };

  const handleForgot = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setSuccess(''); setLoading(true);
    try {
      await forgotPassword(email);
      setSuccess('If an account with that email exists, a reset link has been sent. Check your inbox.');
    } catch {
      setError('Failed to send reset email. Please try again.');
    }
    setLoading(false);
  };

  const handleReset = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(''); setLoading(true);
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match'); setLoading(false); return;
    }
    try {
      const params = new URLSearchParams(window.location.search);
      const token = params.get('token') || '';
      await resetPassword(token, newPassword);
      setSuccess('Password has been reset. You can now sign in.');
      setTimeout(() => switchView('login'), 2000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Reset failed. The link may have expired.');
    }
    setLoading(false);
  };

  const inputClass = `w-full px-4 py-2.5 bg-sand-50 border border-sand-200 rounded-xl text-sm
    text-warm-900 placeholder-sand-400
    focus:outline-none focus:ring-2 focus:ring-sunset-400/40 focus:border-sunset-400`;

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

          {/* === LOGIN VIEW === */}
          {view === 'login' && (
            <>
              <h2 className="text-lg font-semibold text-warm-900 mb-1">Welcome back</h2>
              <p className="text-sm text-sand-500 mb-6">Sign in to access your documents</p>

              {error && <div className="mb-4 px-4 py-2.5 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">{error}</div>}

              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-sand-600 mb-1.5 block">Username</label>
                  <input type="text" value={username} onChange={(e) => setUsername(e.target.value)}
                    placeholder="Enter username" required autoFocus className={inputClass} />
                </div>
                <div>
                  <label className="text-xs font-medium text-sand-600 mb-1.5 block">Password</label>
                  <div className="relative">
                    <input type={showPassword ? 'text' : 'password'} value={password}
                      onChange={(e) => setPassword(e.target.value)} placeholder="Enter password"
                      required className={inputClass} />
                    <button type="button" onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-sand-400 hover:text-warm-600">
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <button type="submit" disabled={loading || !username || !password}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3
                    bg-gradient-to-r from-sunset-500 to-sunset-600 text-white rounded-xl
                    text-sm font-semibold shadow-md hover:shadow-lg
                    hover:from-sunset-600 hover:to-sunset-700 transition-all duration-200
                    disabled:opacity-50 disabled:cursor-not-allowed">
                  {loading ? <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                    : <><LogIn className="w-4 h-4" /> Sign In</>}
                </button>
              </form>

              <div className="mt-5 flex items-center justify-between text-xs">
                <button onClick={() => switchView('forgot')} className="text-sunset-600 hover:text-sunset-700 font-medium">
                  Forgot password?
                </button>
                {!setupCompleted && (
                  <button onClick={() => switchView('create')} className="text-sunset-600 hover:text-sunset-700 font-medium">
                    Create account
                  </button>
                )}
              </div>
            </>
          )}

          {/* === CREATE ACCOUNT VIEW === */}
          {view === 'create' && (
            <>
              <button onClick={() => switchView('login')} className="flex items-center gap-1 text-xs text-sand-500 hover:text-warm-700 mb-4">
                <ArrowLeft className="w-3.5 h-3.5" /> Back to login
              </button>
              <h2 className="text-lg font-semibold text-warm-900 mb-1">Create your account</h2>
              <p className="text-sm text-sand-500 mb-6">Set up your credentials to get started</p>

              {error && <div className="mb-4 px-4 py-2.5 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">{error}</div>}

              <form onSubmit={handleCreate} className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-sand-600 mb-1.5 block">Display Name</label>
                  <input type="text" value={displayName} onChange={(e) => setDisplayName(e.target.value)}
                    placeholder="Your name" className={inputClass} />
                </div>
                <div>
                  <label className="text-xs font-medium text-sand-600 mb-1.5 block">Email <span className="text-sand-400">(for password recovery)</span></label>
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com" className={inputClass} />
                </div>
                <div>
                  <label className="text-xs font-medium text-sand-600 mb-1.5 block">Username</label>
                  <input type="text" value={username} onChange={(e) => setUsername(e.target.value)}
                    placeholder="Choose a username" required autoFocus className={inputClass} />
                </div>
                <div>
                  <label className="text-xs font-medium text-sand-600 mb-1.5 block">Password</label>
                  <div className="relative">
                    <input type={showPassword ? 'text' : 'password'} value={password}
                      onChange={(e) => setPassword(e.target.value)} placeholder="Create a password (min 8 chars)"
                      required className={inputClass} />
                    <button type="button" onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-sand-400 hover:text-warm-600">
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>
                <button type="submit" disabled={loading || !username || !password}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3
                    bg-gradient-to-r from-sunset-500 to-sunset-600 text-white rounded-xl
                    text-sm font-semibold shadow-md hover:shadow-lg
                    hover:from-sunset-600 hover:to-sunset-700 transition-all duration-200
                    disabled:opacity-50 disabled:cursor-not-allowed">
                  {loading ? <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                    : <><UserPlus className="w-4 h-4" /> Create Account</>}
                </button>
              </form>
            </>
          )}

          {/* === FORGOT PASSWORD VIEW === */}
          {view === 'forgot' && (
            <>
              <button onClick={() => switchView('login')} className="flex items-center gap-1 text-xs text-sand-500 hover:text-warm-700 mb-4">
                <ArrowLeft className="w-3.5 h-3.5" /> Back to login
              </button>
              <h2 className="text-lg font-semibold text-warm-900 mb-1">Reset your password</h2>
              <p className="text-sm text-sand-500 mb-6">Enter the email address linked to your account</p>

              {error && <div className="mb-4 px-4 py-2.5 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">{error}</div>}
              {success && <div className="mb-4 px-4 py-2.5 bg-green-50 border border-green-200 rounded-xl text-sm text-green-700">{success}</div>}

              <form onSubmit={handleForgot} className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-sand-600 mb-1.5 block">Email</label>
                  <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@example.com" required autoFocus className={inputClass} />
                </div>
                <button type="submit" disabled={loading || !email}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3
                    bg-gradient-to-r from-sunset-500 to-sunset-600 text-white rounded-xl
                    text-sm font-semibold shadow-md hover:shadow-lg
                    hover:from-sunset-600 hover:to-sunset-700 transition-all duration-200
                    disabled:opacity-50 disabled:cursor-not-allowed">
                  {loading ? <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                    : <><Mail className="w-4 h-4" /> Send Reset Link</>}
                </button>
              </form>
            </>
          )}

          {/* === RESET PASSWORD VIEW === */}
          {view === 'reset' && (
            <>
              <h2 className="text-lg font-semibold text-warm-900 mb-1">Set new password</h2>
              <p className="text-sm text-sand-500 mb-6">Choose a strong password for your account</p>

              {error && <div className="mb-4 px-4 py-2.5 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">{error}</div>}
              {success && <div className="mb-4 px-4 py-2.5 bg-green-50 border border-green-200 rounded-xl text-sm text-green-700">{success}</div>}

              <form onSubmit={handleReset} className="space-y-4">
                <div>
                  <label className="text-xs font-medium text-sand-600 mb-1.5 block">New Password</label>
                  <input type="password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="New password (min 8 chars)" required autoFocus className={inputClass} />
                </div>
                <div>
                  <label className="text-xs font-medium text-sand-600 mb-1.5 block">Confirm Password</label>
                  <input type="password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="Confirm new password" required className={inputClass} />
                </div>
                <button type="submit" disabled={loading || !newPassword || !confirmPassword}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3
                    bg-gradient-to-r from-sunset-500 to-sunset-600 text-white rounded-xl
                    text-sm font-semibold shadow-md hover:shadow-lg
                    hover:from-sunset-600 hover:to-sunset-700 transition-all duration-200
                    disabled:opacity-50 disabled:cursor-not-allowed">
                  {loading ? <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                    : <><KeyRound className="w-4 h-4" /> Reset Password</>}
                </button>
              </form>

              <div className="mt-4 text-center">
                <button onClick={() => switchView('login')} className="text-xs text-sunset-600 hover:text-sunset-700 font-medium">
                  Back to login
                </button>
              </div>
            </>
          )}
        </div>

        <p className="text-center text-xs text-sand-400 mt-6">
          Regia v0.2.0 &middot; All data stays on your device
        </p>
      </div>
    </div>
  );
}

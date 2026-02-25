import { useEffect, useState } from 'react';
import {
  Shield, Lock, Unlock, Mail, Plus, Trash2, Save, Eye, EyeOff,
  Brain, Clock, FolderOpen,
} from 'lucide-react';
import {
  getStatus, setupMasterPassword, unlock as apiUnlock, lock as apiLock,
  getAccounts, addAccount, deleteAccount, storeCredentials, getConfig, updateConfig,
} from '../lib/api';

export default function SettingsPage() {
  const [initialized, setInitialized] = useState(false);
  const [unlocked, setUnlocked] = useState(false);
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [accounts, setAccounts] = useState<any[]>([]);
  const [config, setConfig] = useState<any>(null);
  const [tab, setTab] = useState('security');
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState('');

  // New account form
  const [newAccount, setNewAccount] = useState({
    name: '', email: '', provider: 'gmail', auth_method: 'app_password',
    imap_server: '', imap_port: 993, poll_interval_minutes: 15,
    folders: ['INBOX'], download_invoice_links: true,
  });
  const [appPassword, setAppPassword] = useState('');
  const [showAddAccount, setShowAddAccount] = useState(false);

  const loadStatus = async () => {
    try {
      const resp = await getStatus();
      setInitialized(resp.data.initialized);
      setUnlocked(resp.data.unlocked);
    } catch { /* API not available */ }
    setLoading(false);
  };

  const loadAccounts = async () => {
    try {
      const resp = await getAccounts();
      setAccounts(resp.data.accounts || []);
    } catch { /* ignore */ }
  };

  const loadConfig = async () => {
    try {
      const resp = await getConfig();
      setConfig(resp.data);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    loadStatus();
    loadAccounts();
    loadConfig();
  }, []);

  const handleSetup = async () => {
    if (!password) return;
    try {
      if (initialized) {
        await apiUnlock(password);
        setMessage('Unlocked successfully');
      } else {
        await setupMasterPassword(password);
        setMessage('Master password set successfully');
      }
      setUnlocked(true);
      setPassword('');
      loadAccounts();
    } catch {
      setMessage('Invalid password');
    }
  };

  const handleLock = async () => {
    try {
      await apiLock();
      setUnlocked(false);
      setMessage('Locked');
    } catch { /* ignore */ }
  };

  const handleAddAccount = async () => {
    try {
      const resp = await addAccount(newAccount);
      const accountId = resp.data.account_id;

      if (appPassword) {
        await storeCredentials(accountId, {
          account_id: accountId,
          app_password: appPassword,
        });
      }

      setShowAddAccount(false);
      setNewAccount({
        name: '', email: '', provider: 'gmail', auth_method: 'app_password',
        imap_server: '', imap_port: 993, poll_interval_minutes: 15,
        folders: ['INBOX'], download_invoice_links: true,
      });
      setAppPassword('');
      setMessage('Account added successfully');
      loadAccounts();
    } catch {
      setMessage('Failed to add account');
    }
  };

  const handleDeleteAccount = async (id: string) => {
    try {
      await deleteAccount(id);
      setMessage('Account deleted');
      loadAccounts();
    } catch { /* ignore */ }
  };

  const handleSaveConfig = async () => {
    if (!config) return;
    try {
      await updateConfig(config);
      setMessage('Configuration saved');
    } catch {
      setMessage('Failed to save configuration');
    }
  };

  const tabs = [
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'accounts', label: 'Email Accounts', icon: Mail },
    { id: 'llm', label: 'LLM / AI', icon: Brain },
    { id: 'storage', label: 'Storage', icon: FolderOpen },
    { id: 'scheduler', label: 'Scheduler', icon: Clock },
  ];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-sunset-400 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-warm-900">Settings</h2>
        <p className="text-sm text-sand-600 mt-0.5">Configure Regia to your needs</p>
      </div>

      {message && (
        <div className="px-4 py-2.5 bg-sunset-100 border border-sunset-200 rounded-xl text-sm text-sunset-800 flex items-center justify-between">
          <span>{message}</span>
          <button onClick={() => setMessage('')} className="text-sunset-500 hover:text-sunset-700 text-xs ml-4">Dismiss</button>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="flex gap-1 bg-sand-100 p-1 rounded-xl w-fit">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-medium transition-colors ${
              tab === t.id ? 'bg-white text-warm-900 shadow-sm' : 'text-sand-600 hover:text-warm-700'
            }`}
          >
            <t.icon className="w-4 h-4" /> {t.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-2xl border border-sand-200 shadow-sm p-6">
        {/* === Security Tab === */}
        {tab === 'security' && (
          <div className="space-y-6 max-w-md">
            <div>
              <h3 className="text-lg font-semibold text-warm-900 flex items-center gap-2">
                <Shield className="w-5 h-5 text-sunset-500" /> Master Password
              </h3>
              <p className="text-sm text-sand-500 mt-1">
                {initialized
                  ? 'Your credential store is encrypted. Enter your password to unlock.'
                  : 'Set a master password to encrypt your email credentials.'
                }
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${
                unlocked ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
              }`}>
                {unlocked ? <Unlock className="w-3 h-3" /> : <Lock className="w-3 h-3" />}
                {unlocked ? 'Unlocked' : 'Locked'}
              </span>
            </div>

            {!unlocked ? (
              <div className="space-y-3">
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder={initialized ? 'Enter master password' : 'Create master password'}
                    className="w-full px-4 py-2.5 bg-sand-50 border border-sand-200 rounded-xl text-sm
                               focus:outline-none focus:ring-2 focus:ring-sunset-400/40 focus:border-sunset-400"
                    onKeyDown={(e) => e.key === 'Enter' && handleSetup()}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-sand-400 hover:text-warm-600"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
                <button
                  onClick={handleSetup}
                  className="px-5 py-2.5 bg-gradient-to-r from-sunset-500 to-sunset-600 text-white rounded-xl
                             text-sm font-medium shadow-sm hover:shadow-md transition-all"
                >
                  {initialized ? 'Unlock' : 'Set Password'}
                </button>
              </div>
            ) : (
              <button
                onClick={handleLock}
                className="px-5 py-2.5 bg-sand-100 text-warm-700 rounded-xl text-sm font-medium hover:bg-sand-200 transition-colors"
              >
                Lock Credential Store
              </button>
            )}
          </div>
        )}

        {/* === Accounts Tab === */}
        {tab === 'accounts' && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-warm-900">Email Accounts</h3>
              <button
                onClick={() => setShowAddAccount(!showAddAccount)}
                className="flex items-center gap-1.5 px-3 py-2 bg-sunset-500 text-white rounded-xl text-xs font-medium hover:bg-sunset-600 transition-colors"
              >
                <Plus className="w-3.5 h-3.5" /> Add Account
              </button>
            </div>

            {/* Add Account Form */}
            {showAddAccount && (
              <div className="bg-sand-50 rounded-xl p-4 border border-sand-200 space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-medium text-sand-600 mb-1 block">Name</label>
                    <input
                      type="text" placeholder="My Gmail"
                      value={newAccount.name} onChange={e => setNewAccount({...newAccount, name: e.target.value})}
                      className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-sand-600 mb-1 block">Email</label>
                    <input
                      type="email" placeholder="user@gmail.com"
                      value={newAccount.email} onChange={e => setNewAccount({...newAccount, email: e.target.value})}
                      className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-sand-600 mb-1 block">Provider</label>
                    <select
                      value={newAccount.provider} onChange={e => setNewAccount({...newAccount, provider: e.target.value})}
                      className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                    >
                      <option value="gmail">Gmail</option>
                      <option value="outlook">Outlook</option>
                      <option value="imap">Custom IMAP</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-sand-600 mb-1 block">Poll Interval (min)</label>
                    <input
                      type="number" min={1} max={1440}
                      value={newAccount.poll_interval_minutes}
                      onChange={e => setNewAccount({...newAccount, poll_interval_minutes: parseInt(e.target.value) || 15})}
                      className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                    />
                  </div>
                </div>
                <div>
                  <label className="text-xs font-medium text-sand-600 mb-1 block">App Password</label>
                  <input
                    type="password" placeholder="App-specific password"
                    value={appPassword} onChange={e => setAppPassword(e.target.value)}
                    className="w-full px-3 py-2 bg-white border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                  />
                  <p className="text-[11px] text-sand-400 mt-1">
                    For Gmail: enable 2FA then create an app password at myaccount.google.com
                  </p>
                </div>
                <div className="flex gap-2">
                  <button onClick={handleAddAccount}
                    className="px-4 py-2 bg-sunset-500 text-white rounded-lg text-xs font-medium hover:bg-sunset-600 transition-colors">
                    Save Account
                  </button>
                  <button onClick={() => setShowAddAccount(false)}
                    className="px-4 py-2 bg-sand-100 text-sand-600 rounded-lg text-xs font-medium hover:bg-sand-200 transition-colors">
                    Cancel
                  </button>
                </div>
              </div>
            )}

            {/* Account List */}
            {accounts.length === 0 ? (
              <div className="text-center py-8 text-sand-400">
                <Mail className="w-10 h-10 mx-auto mb-2 text-sand-300" />
                <p className="text-sm">No email accounts configured</p>
              </div>
            ) : (
              <div className="space-y-2">
                {accounts.map((acc: any) => (
                  <div key={acc.id} className="flex items-center justify-between px-4 py-3 bg-sand-50 rounded-xl border border-sand-200">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-lg bg-sunset-100 flex items-center justify-center">
                        <Mail className="w-4 h-4 text-sunset-500" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-warm-900">{acc.name || acc.email}</p>
                        <p className="text-[11px] text-sand-500">{acc.email} · {acc.provider}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                        acc.enabled ? 'bg-green-100 text-green-700' : 'bg-sand-200 text-sand-500'
                      }`}>
                        {acc.enabled ? 'Active' : 'Disabled'}
                      </span>
                      <button
                        onClick={() => handleDeleteAccount(acc.id)}
                        className="p-1.5 rounded-lg hover:bg-red-100 text-sand-400 hover:text-red-500 transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* === LLM Tab === */}
        {tab === 'llm' && config && (
          <div className="space-y-4 max-w-lg">
            <h3 className="text-lg font-semibold text-warm-900 flex items-center gap-2">
              <Brain className="w-5 h-5 text-sunset-500" /> LLM Configuration
            </h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-sand-600 mb-1 block">Model Name</label>
                <input
                  type="text"
                  value={config.llm?.model_name || ''}
                  onChange={e => setConfig({...config, llm: {...config.llm, model_name: e.target.value}})}
                  className="w-full px-3 py-2 bg-sand-50 border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                />
                <p className="text-[11px] text-sand-400 mt-1">Recommended: qwen2.5:0.5b (ultra-light), tinyllama, phi</p>
              </div>
              <div>
                <label className="text-xs font-medium text-sand-600 mb-1 block">Ollama URL</label>
                <input
                  type="text"
                  value={config.llm?.ollama_base_url || ''}
                  onChange={e => setConfig({...config, llm: {...config.llm, ollama_base_url: e.target.value}})}
                  className="w-full px-3 py-2 bg-sand-50 border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={config.llm?.fallback_to_rules ?? true}
                  onChange={e => setConfig({...config, llm: {...config.llm, fallback_to_rules: e.target.checked}})}
                  className="rounded border-sand-300 text-sunset-500 focus:ring-sunset-400"
                />
                <label className="text-sm text-warm-700">Fallback to rule-based classification if LLM unavailable</label>
              </div>
            </div>
            <button onClick={handleSaveConfig}
              className="flex items-center gap-2 px-4 py-2 bg-sunset-500 text-white rounded-xl text-sm font-medium hover:bg-sunset-600 transition-colors">
              <Save className="w-4 h-4" /> Save Configuration
            </button>
          </div>
        )}

        {/* === Storage Tab === */}
        {tab === 'storage' && config && (
          <div className="space-y-4 max-w-lg">
            <h3 className="text-lg font-semibold text-warm-900 flex items-center gap-2">
              <FolderOpen className="w-5 h-5 text-sunset-500" /> Storage Configuration
            </h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-sand-600 mb-1 block">Storage Directory</label>
                <input
                  type="text"
                  value={config.storage?.base_dir || ''}
                  onChange={e => setConfig({...config, storage: {...config.storage, base_dir: e.target.value}})}
                  className="w-full px-3 py-2 bg-sand-50 border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                />
              </div>
              <div>
                <label className="text-xs font-medium text-sand-600 mb-1 block">Folder Template</label>
                <input
                  type="text"
                  value={config.storage?.folder_template || ''}
                  onChange={e => setConfig({...config, storage: {...config.storage, folder_template: e.target.value}})}
                  className="w-full px-3 py-2 bg-sand-50 border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                />
                <p className="text-[11px] text-sand-400 mt-1">
                  Available: {'{email}'}, {'{date}'}, {'{sender}'}, {'{subject}'}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={config.storage?.verify_hash ?? true}
                  onChange={e => setConfig({...config, storage: {...config.storage, verify_hash: e.target.checked}})}
                  className="rounded border-sand-300 text-sunset-500 focus:ring-sunset-400"
                />
                <label className="text-sm text-warm-700">Verify file integrity with SHA-256 hash</label>
              </div>
            </div>
            <button onClick={handleSaveConfig}
              className="flex items-center gap-2 px-4 py-2 bg-sunset-500 text-white rounded-xl text-sm font-medium hover:bg-sunset-600 transition-colors">
              <Save className="w-4 h-4" /> Save Configuration
            </button>
          </div>
        )}

        {/* === Scheduler Tab === */}
        {tab === 'scheduler' && config && (
          <div className="space-y-4 max-w-lg">
            <h3 className="text-lg font-semibold text-warm-900 flex items-center gap-2">
              <Clock className="w-5 h-5 text-sunset-500" /> Scheduler Configuration
            </h3>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={config.scheduler?.enabled ?? true}
                  onChange={e => setConfig({...config, scheduler: {...config.scheduler, enabled: e.target.checked}})}
                  className="rounded border-sand-300 text-sunset-500 focus:ring-sunset-400"
                />
                <label className="text-sm text-warm-700">Enable automatic email polling</label>
              </div>
              <div>
                <label className="text-xs font-medium text-sand-600 mb-1 block">Default Interval (minutes)</label>
                <input
                  type="number" min={1} max={1440}
                  value={config.scheduler?.default_interval_minutes || 15}
                  onChange={e => setConfig({...config, scheduler: {...config.scheduler, default_interval_minutes: parseInt(e.target.value) || 15}})}
                  className="w-full px-3 py-2 bg-sand-50 border border-sand-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-sunset-400/40"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={config.scheduler?.retry_on_failure ?? true}
                  onChange={e => setConfig({...config, scheduler: {...config.scheduler, retry_on_failure: e.target.checked}})}
                  className="rounded border-sand-300 text-sunset-500 focus:ring-sunset-400"
                />
                <label className="text-sm text-warm-700">Retry on failure</label>
              </div>
            </div>
            <button onClick={handleSaveConfig}
              className="flex items-center gap-2 px-4 py-2 bg-sunset-500 text-white rounded-xl text-sm font-medium hover:bg-sunset-600 transition-colors">
              <Save className="w-4 h-4" /> Save Configuration
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
